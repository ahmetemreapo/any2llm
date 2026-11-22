from zipfile import ZipFile

import pytest
from docx import Document
from openpyxl import Workbook
from pptx import Presentation
from pptx.util import Inches
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from any2llm.parsers import ParsedFile, SkippedFile, parse_file


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "utf-16", "utf-32", "cp1252"])
def test_text_encodings(tmp_path, encoding):
    path = tmp_path / "notes.txt"
    path.write_bytes("Café — résumé  \r\n\r\n\r\nFin".encode(encoding))
    assert parse_file(path) == ParsedFile("TXT", "Café — résumé\n\nFin")


def test_code_preserves_significant_whitespace(tmp_path):
    path = tmp_path / "example.PY"
    source = 'def example():\n    return """first  \n\n\n\tlast"""\n'
    path.write_bytes(source.replace("\n", "\r\n").encode())
    assert parse_file(path) == ParsedFile("PY", source)


def test_pdf_text_and_margins(tmp_path):
    writer = PdfWriter()
    for n in range(1, 3):
        page = writer.add_blank_page(width=300, height=300)
        font = DictionaryObject({
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        })
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): font}),
        })
        contents = DecodedStreamObject()
        contents.set_data(
            f"BT /F1 12 Tf 10 260 Td (Header) Tj 0 -20 Td (Body {n}) Tj "
            f"0 -20 Td (Page {n} of 2) Tj ET".encode()
        )
        page[NameObject("/Contents")] = contents
    path = tmp_path / "report.pdf"
    writer.write(path)
    assert parse_file(path) == ParsedFile("PDF", "Body 1\n\nBody 2")
    writer.encrypt("password")
    writer.write(path)
    assert parse_file(path) == SkippedFile("encrypted")


def test_docx_preserves_paragraph_and_table_order(tmp_path):
    path = tmp_path / "report.docx"
    doc = Document()
    doc.add_paragraph("Before")
    table = doc.add_table(rows=2, cols=2)
    for row, values in zip(table.rows, [("Item", "Qty"), ("Apple", "3")]):
        for cell, value in zip(row.cells, values):
            cell.text = value
    doc.add_paragraph("After")
    doc.save(path)
    assert parse_file(path) == ParsedFile(
        "DOCX", "Before\n\n| Item | Qty |\n| --- | --- |\n| Apple | 3 |\n\nAfter"
    )


def test_pptx_numbers_slides_including_empty_ones(tmp_path):
    path = tmp_path / "deck.pptx"
    deck = Presentation()
    blank = deck.slide_layouts[6]
    slide = deck.slides.add_slide(blank)
    box = (0, 0, Inches(2), Inches(1))
    slide.shapes.add_group_shape().shapes.add_textbox(*box).text = "Introduction"
    deck.slides.add_slide(blank)
    slide = deck.slides.add_slide(blank)
    slide.shapes.add_textbox(*box).text = "Results"
    slide.shapes.add_table(1, 1, *box).table.cell(0, 0).text = "Revenue"
    deck.save(path)
    assert parse_file(path) == ParsedFile(
        "PPTX", "## Slide 1\n\nIntroduction\n\n## Slide 2\n\n## Slide 3\n\n"
        "Results\n\n| Revenue |\n| --- |"
    )


def test_xlsx_sheet_tables(tmp_path):
    path = tmp_path / "book.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Inventory"
    sheet.append(["Item", "Stock"])
    sheet.append(["A|B\nC", 0, False])
    sheet.append(["Total", "=SUM(B2:B2)"])
    sheet.cell(10, 8).number_format = "0.00"
    workbook.create_sheet("Empty")
    workbook.create_sheet("Summary").append(["Done"])
    workbook.save(path)
    assert parse_file(path) == ParsedFile(
        "XLSX", "## Inventory\n\n| Item | Stock |  |\n| --- | --- | --- |\n"
        "| A\\|B<br>C | 0 | False |\n| Total | =SUM(B2:B2) |  |\n\n"
        "## Empty\n\n## Summary\n\n| Done |\n| --- |"
    )


@pytest.mark.parametrize("suffix", [".pdf", ".docx", ".pptx", ".xlsx"])
def test_corrupt_document_is_skipped(tmp_path, suffix):
    path = tmp_path / ("damaged" + suffix)
    with ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<broken")
    assert parse_file(path) == SkippedFile("invalid")


@pytest.mark.parametrize(("name", "data", "reason"), [
    ("legacy.doc", b"legacy", "unsupported"),
    ("locked.xlsx", bytes.fromhex("d0cf11e0a1b11ae1"), "compound"),
    ("photo.svg", b"<svg/>", "image"),
    ("fake.txt", b"a\x00b", "binary"),
    ("bad.txt", b"\xff\xfeA", "binary"),
    ("bad-bom.txt", b"\xef\xbb\xbf\xff", "binary"),
    ("missing.txt", None, "unreadable"),
])
def test_unusable_input_is_skipped(tmp_path, name, data, reason):
    path = tmp_path / name
    if data is not None:
        path.write_bytes(data)
    assert parse_file(path) == SkippedFile(reason)
