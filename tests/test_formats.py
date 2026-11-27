from zipfile import ZipFile

import pytest

from any2llm.markup import html_to_text, is_html_document
from any2llm.parsers import ParsedFile, SkippedFile, parse_file

PAGE = """<!doctype html>
<html><head><title>Ignored</title><style>body { color: red }</style></head>
<body>
  <h2>Delivery   terms</h2>
  <p>Ship <b>before</b>
     March 12.</p>
  <ol><li>Pilot<ul><li>Two pallets</li></ul></li><li>Main</li></ol>
  <table><tr><th>Item</th><th>Qty</th></tr><tr><td>Bolts | M6</td><td>40</td></tr></table>
  <pre>def total():
    return 40</pre>
  <script>track()</script>
  <img src="chart.png" alt="Shipment chart">
  <p>Tom &amp; Jerry</p>
</body></html>
"""


def test_html_document_becomes_readable_markdown():
    assert html_to_text(PAGE) == (
        "## Delivery terms\n\nShip before March 12.\n\n1. Pilot\n  - Two pallets\n2. Main\n\n"
        "| Item | Qty |\n| --- | --- |\n| Bolts \\| M6 | 40 |\n\n"
        "```\ndef total():\n    return 40\n```\n\n[Image: Shipment chart]\n\nTom & Jerry"
    )


@pytest.mark.parametrize(("text", "expected"), [
    (PAGE, True),
    ("<div class='card'>{{ title }}</div>", False),
    ("<!doctype html><html><body>{% block content %}{% endblock %}</body></html>", False),
    ("<p>Fragment</p>", False),
])
def test_only_full_documents_are_converted(text, expected):
    assert is_html_document(text) is expected


def test_html_file_and_template(tmp_path):
    page = tmp_path / "offer.html"
    page.write_text(PAGE, encoding="utf-8")
    parsed = parse_file(page)
    assert parsed.file_type == "HTML" and "track()" not in parsed.text and "## Delivery terms" in parsed.text

    template = tmp_path / "base.html"
    source = "<!doctype html><html><body>{% block body %}{% endblock %}</body></html>\n"
    template.write_text(source, encoding="utf-8")
    assert parse_file(template) == ParsedFile("HTML", source)


def test_csv_stays_compact_text(tmp_path):
    path = tmp_path / "orders.csv"
    path.write_bytes(b"id,qty\r\n1,40\r\n")
    assert parse_file(path) == ParsedFile("CSV", "id,qty\n1,40\n")


def _epub(path, *, encryption: str | None = None, chapters=("<h1>One</h1><p>First.</p>", "<p>Second.</p>")):
    with ZipFile(path, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip")
        archive.writestr("META-INF/container.xml", """<?xml version="1.0"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
  <rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>""")
        items = "".join(
            f'<item id="c{n}" href="text/ch%20{n}.xhtml" media-type="application/xhtml+xml"/>'
            for n in range(len(chapters))
        )
        # The spine order, not the manifest order, decides the reading order.
        spine = "".join(f'<itemref idref="c{n}"/>' for n in reversed(range(len(chapters))))
        archive.writestr("OEBPS/content.opf", f"""<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Field Guide</dc:title></metadata>
  <manifest>{items}<item id="css" href="style.css" media-type="text/css"/></manifest>
  <spine>{spine}</spine>
</package>""")
        for n, body in enumerate(chapters):
            archive.writestr(f"OEBPS/text/ch {n}.xhtml", f"<html><body>{body}</body></html>")
        if encryption:
            archive.writestr("META-INF/encryption.xml", f"""<?xml version="1.0"?>
<encryption xmlns="urn:oasis:names:tc:opendocument:xmlns:container"
            xmlns:enc="http://www.w3.org/2001/04/xmlenc#">
  <enc:EncryptedData><enc:EncryptionMethod Algorithm="{encryption}"/></enc:EncryptedData>
</encryption>""")


def test_epub_follows_spine_order(tmp_path):
    path = tmp_path / "guide.epub"
    _epub(path)
    assert parse_file(path) == ParsedFile("EPUB", "# Field Guide\n\nSecond.\n\n# One\n\nFirst.")


def test_epub_font_obfuscation_is_readable_but_drm_is_skipped(tmp_path):
    fonts = tmp_path / "fonts.epub"
    _epub(fonts, encryption="http://www.idpf.org/2008/embedding")
    assert parse_file(fonts).file_type == "EPUB"

    locked = tmp_path / "locked.epub"
    _epub(locked, encryption="http://www.w3.org/2001/04/xmlenc#aes128-cbc")
    assert parse_file(locked) == SkippedFile("encrypted")


def test_damaged_epub_is_skipped(tmp_path):
    path = tmp_path / "broken.epub"
    path.write_bytes(b"PK\x03\x04 truncated")
    assert parse_file(path) == SkippedFile("invalid")
