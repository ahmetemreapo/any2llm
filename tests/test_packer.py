from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from any2llm import tokenizer
from any2llm.packer import write_batches
from any2llm.parsers import ParsedFile, PdfPage


@pytest.fixture(autouse=True)
def offline_tokenizer(monkeypatch):
    monkeypatch.setattr(tokenizer, "get_encoding", lambda: None)


def read_batches(paths, limit=None):
    batches = []
    for number, path in enumerate(paths, 1):
        assert path.name == f"batch_{number:02d}_of_{len(paths)}.md"
        text = path.read_text(encoding="utf-8")
        if limit is not None:
            assert tokenizer.count_tokens(text) <= limit
        assert text.startswith("<manifest")
        manifest, *blocks = ET.fromstring(f"<root>{text}</root>")
        assert manifest.attrib == {"batch": str(number), "total": str(len(paths))}
        assert all(block.tag == "file" for block in blocks)
        assert [entry.attrib for entry in manifest] == [block.attrib for block in blocks]
        batches.append(blocks)
    return batches


@pytest.mark.parametrize(("preset", "limit", "expected"), [
    ("High Detail", 12_000, [1, 1, 1, 1]),
    ("Balanced", 25_000, [3, 1]),
    ("Single File", None, [4]),
])
def test_groups_whole_files_in_order(tmp_path, preset, limit, expected):
    files = {Path(f"{i}/notes.md"): ParsedFile("MD", "data" * 8_000) for i in range(4)}
    batches = read_batches(write_batches(files, tmp_path, preset=preset), limit)
    assert list(map(len, batches)) == expected
    blocks = [block for batch in batches for block in batch]
    assert [block.get("name") for block in blocks] == [path.as_posix() for path in files]
    assert len({block.get("id") for block in blocks}) == 4
    assert all(block.get("part") is None and block.text == "data" * 8_000 for block in blocks)


@pytest.mark.parametrize(("text", "boundary"), [
    ("  ünicode & <tag>  \n" * 220, "\n"),
    ("merhaba dünyaya " * 250, " "),
    ("😀中" * 1_500, None),
])
def test_large_file_splits_losslessly(tmp_path, text, boundary):
    name = 'nested/a&"b.md'
    selected = {Path(name): ParsedFile("MD", text)}
    paths = write_batches(selected, tmp_path, preset="Single File", max_tokens=100)
    assert len(paths) >= 10
    batches = read_batches(paths, 100)
    assert all(len(batch) == 1 for batch in batches)
    blocks = [batch[0] for batch in batches]
    assert "".join(block.text for block in blocks) == text
    assert len({block.get("id") for block in blocks}) == 1
    for i, block in enumerate(blocks, 1):
        assert block.get("name") == name
        assert block.get("type") == "MD"
        assert block.get("part") == f"{i}/{len(blocks)}"
        if boundary and i < len(blocks):
            assert block.text.endswith(boundary)


def test_exact_limit_and_failed_repack_preserve_output(tmp_path):
    files = {Path("empty"): ParsedFile("Text", "")}
    path, = write_batches(files, tmp_path)
    original = path.read_text()
    limit = tokenizer.count_tokens(original)
    assert write_batches(files, tmp_path, max_tokens=limit) == [path]
    assert read_batches([path], limit)[0][0].text is None
    with pytest.raises(ValueError, match="too small"):
        write_batches(files, tmp_path, max_tokens=limit - 1)
    assert path.read_text() == original


def test_split_pdf_keeps_missing_pages_and_repeats_partial_status(tmp_path):
    body = "A & B\n" * 200
    pages = (
        PdfPage(1, "Introduction"), PdfPage(2, "", no_text=True),
        PdfPage(3, body, partial=True), PdfPage(4, "Results"),
    )
    files = {Path("report.pdf"): ParsedFile("PDF", f"Introduction\n\n{body}\n\nResults", pages)}
    docs = read_batches(write_batches(files, tmp_path, max_tokens=100), limit=100)
    elements = [page for batch in docs for block in batch for page in block.findall("page")]
    assert elements[0].attrib == {"number": "1"}
    assert elements[1].attrib == {"number": "2", "extraction": "no-extractable-text"}
    assert elements[1].text is None
    assert elements[-1].attrib == {"number": "4"}
    middle = elements[2:-1]
    assert len(middle) > 1
    assert all(page.attrib == {"number": "3", "status": "partial"} for page in middle)
    assert "".join(page.text for page in middle) == body


def test_rerun_clears_obsolete_batches(tmp_path):
    selected = {Path("a.md"): ParsedFile("MD", "one line\n" * 300)}
    previous = write_batches(selected, tmp_path, max_tokens=100)
    unrelated = tmp_path / "notes.md"
    unrelated.write_text("keep me")
    current = write_batches(selected, tmp_path, preset="Single File")
    assert set(tmp_path.glob("*.md")) == {*current, unrelated}
    assert len(previous) > len(current)
    assert unrelated.read_text() == "keep me"
