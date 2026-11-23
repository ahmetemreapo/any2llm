from datetime import date, datetime
from io import BytesIO
from subprocess import CalledProcessError, CompletedProcess, TimeoutExpired
from unittest.mock import Mock, call
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import pypdf
import pytest
from docx import Document
from openpyxl import Workbook
from openpyxl.utils.datetime import to_excel
from pptx import Presentation
from pptx.util import Inches
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from any2llm import ocr, parsers
from any2llm.parsers import ParsedFile, PdfPage, SkippedFile, parse_file


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
    assert parse_file(path) == ParsedFile("PDF", "Body 1\n\nBody 2", (
        PdfPage(1, "Body 1"), PdfPage(2, "Body 2"),
    ))
    writer.encrypt("password")
    writer.write(path)
    assert parse_file(path) == SkippedFile("encrypted")


@pytest.mark.parametrize(("fallback", "expected"), [
    (b"Educational Research\n", PdfPage(3, "Educational Research")),
    (b"Educa\x00onal Research", PdfPage(3, "Educa\ufffdonal Research", partial=True)),
    (b"\n", PdfPage(3, "Educa\ufffdonal Research", partial=True)),
    (b"\xff", PdfPage(3, "Educa\ufffdonal Research", partial=True)),
    (FileNotFoundError(), PdfPage(3, "Educa\ufffdonal Research", partial=True)),
    (CalledProcessError(1, "pdftotext"), PdfPage(3, "Educa\ufffdonal Research", partial=True)),
    (TimeoutExpired("pdftotext", 10), PdfPage(3, "Educa\ufffdonal Research", partial=True)),
])
def test_pdf_repairs_only_damaged_pages(tmp_path, monkeypatch, fallback, expected):
    path = tmp_path / "report.pdf"
    path.touch()
    reader = Mock(is_encrypted=False, pages=[
        Mock(extract_text=Mock(return_value=text))
        for text in ("Introduction", "", "Educa\x00onal Research", "Results")
    ])
    monkeypatch.setattr(pypdf, "PdfReader", Mock(return_value=reader))
    executable = str(tmp_path / "tools" / "pdftotext")
    monkeypatch.setattr(parsers, "resolve_tool", lambda _: executable)
    run = Mock(side_effect=fallback) if isinstance(fallback, Exception) else Mock(
        return_value=CompletedProcess("pdftotext", 0, stdout=fallback),
    )
    monkeypatch.setattr(parsers.subprocess, "run", run)

    parsed = parse_file(path)
    assert parsed.pages == (
        PdfPage(1, "Introduction"), PdfPage(2, "", no_text=True), expected, PdfPage(4, "Results"),
    )
    assert parsed.text == f"Introduction\n\n{expected.text}\n\nResults"
    run.assert_called_once()
    assert run.call_args.args[0] == [
        executable, "-f", "3", "-l", "3", "-layout", "-nopgbrk", "-enc", "UTF-8", str(path), "-",
    ]


def test_pdf_distinguishes_margin_cleanup_from_missing_text(tmp_path, monkeypatch):
    path = tmp_path / "report.pdf"
    path.touch()
    reader = Mock(is_encrypted=False, pages=[
        Mock(extract_text=Mock(return_value=text))
        for text in ("Introduction", "Page 2 of 5", "  \n", "\ufffd", "Results")
    ])
    monkeypatch.setattr(pypdf, "PdfReader", Mock(return_value=reader))
    monkeypatch.setattr(parsers, "_pdftotext", lambda *_: "")
    assert parse_file(path) == ParsedFile("PDF", "Introduction\n\n\ufffd\n\nResults", (
        PdfPage(1, "Introduction"),
        PdfPage(2, ""),
        PdfPage(3, "", no_text=True),
        PdfPage(4, "\ufffd", partial=True, no_text=True),
        PdfPage(5, "Results"),
    ))
    reader.pages = reader.pages[2:3]
    assert parse_file(path) == SkippedFile("no_pdf_text")


def test_pdf_ocr_runs_only_after_both_text_extractors_find_nothing(tmp_path, monkeypatch):
    path = tmp_path / "notes.pdf"
    path.touch()
    reader = Mock(is_encrypted=False, pages=[
        Mock(extract_text=Mock(return_value=text))
        for text in ("Introduction", "Page 2 of 7", "  \n", "", "par\x00ial", "", "\ufffd")
    ])
    fallback = Mock(side_effect=lambda _, page: "From the second extractor\n" if page == 3 else "")
    recognize = Mock(side_effect=["A scanned paragraph.  \n\f", "  \f", "Recovered damaged page.\n"])
    monkeypatch.setattr(pypdf, "PdfReader", Mock(return_value=reader))
    monkeypatch.setattr(parsers, "_pdftotext", fallback)
    monkeypatch.setattr(ocr, "read_page", recognize)

    parsed = parse_file(path, ocr_lang="tur+eng")

    assert fallback.call_args_list == [call(path, page) for page in (3, 4, 5, 6, 7)]
    assert recognize.call_args_list == [call(path, page, "tur+eng") for page in (4, 6, 7)]
    assert parsed.pages == (
        PdfPage(1, "Introduction"), PdfPage(2, ""), PdfPage(3, "From the second extractor"),
        PdfPage(4, "A scanned paragraph.", ocr=True), PdfPage(5, "par\ufffdial", partial=True),
        PdfPage(6, "", no_text=True), PdfPage(7, "Recovered damaged page.", ocr=True),
    )


def test_pdf_with_only_scanned_pages_becomes_readable_with_ocr(tmp_path, monkeypatch):
    path = tmp_path / "scan.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    writer.write(path)
    monkeypatch.setattr(parsers, "_pdftotext", lambda *_: "")
    recognize = Mock(return_value="Lecture notes\n")
    monkeypatch.setattr(ocr, "read_page", recognize)

    assert parse_file(path) == SkippedFile("no_pdf_text")
    assert parse_file(path, ocr_lang="eng") == ParsedFile("PDF", "Lecture notes", (
        PdfPage(1, "Lecture notes", ocr=True),
    ))
    writer.encrypt("password")
    writer.write(path)
    assert parse_file(path, ocr_lang="eng") == SkippedFile("encrypted")
    recognize.assert_called_once_with(path, 1, "eng")


def test_docx_preserves_paragraph_and_table_order(tmp_path):
    path = tmp_path / "report.docx"
    doc = Document()
    doc.add_paragraph("Before")
    table = doc.add_table(rows=2, cols=2)
    for row, values in zip(table.rows, [("Item", "Qty"), ("Apple", "3")], strict=False):
        for cell, value in zip(row.cells, values, strict=False):
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
    hidden = workbook.create_sheet("Hidden")
    hidden.append(["Do not export"])
    hidden.sheet_state = "hidden"
    workbook.create_sheet("Summary").append(["Done"])
    very_hidden = workbook.create_sheet("Very\nHidden")
    very_hidden.append(["Do not export this either"])
    very_hidden.sheet_state = "veryHidden"
    workbook.save(path)
    assert parse_file(path) == ParsedFile(
        "XLSX", "## Inventory\n\n| Item | Stock |  |\n| --- | --- | --- |\n"
        "| A\\|B<br>C | 0 | False |\n| Total | =SUM(B2:B2) |  |\n\n"
        "## Empty\n\n## Summary\n\n| Done |\n| --- |\n\nSkipped hidden sheets (Hidden, Very Hidden)."
    )


@pytest.mark.parametrize("iso_dates", [False, True])
def test_xlsx_formats_dates_and_datetimes_as_iso(tmp_path, iso_dates):
    path = tmp_path / "dates.xlsx"
    workbook = Workbook(iso_dates=iso_dates)
    workbook.active.append(["Date", "Midnight", "Appointment", "Fractional"])
    workbook.active.append([
        date(2027, 3, 12), datetime(2027, 3, 12),
        datetime(2027, 3, 12, 9, 15, 6), datetime(2027, 3, 12, 0, 0, 0, 123000),
    ])
    workbook.save(path)

    assert parse_file(path) == ParsedFile(
        "XLSX", "## Sheet\n\n| Date | Midnight | Appointment | Fractional |\n| --- | --- | --- | --- |\n"
        "| 2027-03-12 | 2027-03-12 | 2027-03-12T09:15:06 | 2027-03-12T00:00:00.123000 |"
    )


def test_xlsx_shows_formula_and_cached_value(tmp_path):
    path = tmp_path / "formulas.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Label", "Value"])
    sheet.append(["Total", "=SUM(7,8)"])
    sheet.append(["Zero", "=1-1"])
    sheet.append(["Boolean", "=FALSE()"])
    sheet.append(["Date", "=DATE(2027,3,12)"])
    sheet["B5"].number_format = "yyyy-mm-dd"
    sheet.append(["Literal text", "=not a formula"])
    sheet["B6"].data_type = "s"
    uncached = BytesIO()
    workbook.save(uncached)

    # openpyxl writes formulas without results, so populate Excel's cached values in the fixture.
    sheet_name = "xl/worksheets/sheet1.xml"
    namespaces = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    values = [("n", "15"), ("n", "0"), ("b", "0"), ("n", str(to_excel(datetime(2027, 3, 12))))]
    with ZipFile(uncached) as source, ZipFile(path, "w") as target:
        sheet_xml = ET.fromstring(source.read(sheet_name))
        for row, (cell_type, value) in enumerate(values, start=2):
            cell = sheet_xml.find(f".//s:c[@r='B{row}']", namespaces)
            cell.set("t", cell_type)
            cell.find("s:v", namespaces).text = value
        for name in source.namelist():
            target.writestr(name, ET.tostring(sheet_xml) if name == sheet_name else source.read(name))

    assert parse_file(path) == ParsedFile(
        "XLSX", "## Sheet\n\n| Label | Value |\n| --- | --- |\n"
        "| Total | 15 (=SUM(7,8)) |\n| Zero | 0 (=1-1) |\n| Boolean | False (=FALSE()) |\n"
        "| Date | 2027-03-12 (=DATE(2027,3,12)) |\n| Literal text | =not a formula |"
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


def test_source_limit_is_checked_before_extraction(tmp_path, monkeypatch):
    path = tmp_path / "notes.txt"
    path.write_text("example")
    monkeypatch.setattr(parsers, "MAX_SOURCE_BYTES", 6)
    plain = Mock(side_effect=AssertionError)
    monkeypatch.setattr(parsers, "_plain", plain)
    assert parse_file(path) == SkippedFile("source_limit")
    plain.assert_not_called()


def test_pdf_page_limit_is_checked_before_page_extraction(tmp_path, monkeypatch):
    path = tmp_path / "sample.pdf"
    writer = PdfWriter()
    for _ in range(3):
        writer.add_blank_page(width=72, height=72)
    writer.write(path)
    monkeypatch.setattr(parsers, "MAX_PDF_PAGES", 2)
    from pypdf import PageObject

    extract = Mock(side_effect=AssertionError)
    monkeypatch.setattr(PageObject, "extract_text", extract)
    assert parse_file(path) == SkippedFile("pdf_limit")
    extract.assert_not_called()


@pytest.mark.parametrize("ext", [".docx", ".pptx", ".xlsx"])
def test_office_limit_counts_all_uncompressed_entries(tmp_path, monkeypatch, ext):
    path = tmp_path / f"document{ext}"
    with ZipFile(path, "w") as archive:
        archive.writestr("first.xml", "x" * 5)
        archive.writestr("second.xml", "y" * 6)
    monkeypatch.setattr(parsers, "MAX_OFFICE_BYTES", 10)
    extract = Mock(side_effect=AssertionError)
    monkeypatch.setitem(parsers._OFFICE, ext, extract)
    assert parse_file(path) == SkippedFile("office_limit")
    extract.assert_not_called()


def test_open_failures_are_reported_as_unreadable(tmp_path, monkeypatch):
    opener = Mock(side_effect=PermissionError)
    monkeypatch.setattr(parsers, "open", opener, raising=False)
    assert parse_file(tmp_path / "notes.txt") == SkippedFile("unreadable")
