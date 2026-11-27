import json

import pytest

from any2llm import check
from any2llm.citations import (
    CLOSE,
    NO_QUOTE,
    NOT_FOUND,
    OTHER_FILE,
    OTHER_PAGE,
    PAGE_MISSING,
    UNKNOWN_SOURCE,
    VERIFIED,
    check_answer,
    find_citations,
    resolve_source,
)
from any2llm.parsers import ParsedFile, PdfPage

OFFER = ParsedFile("PDF", "", (
    PdfPage(1, "Supplier offer\nPrices are valid for 30 days from the offer date."),
    PdfPage(2, "Delivery: 14 March 2026 for the first ship-\nment. Payment is due within 45 days of delivery."),
    PdfPage(3, "", no_text=True),
))
NOTES = ParsedFile("Text", "Meeting notes\nThe freight forwarder confirmed the pickup window.")
DOCUMENTS = {"offers/supplier-offer.pdf": OFFER, "meeting-notes.txt": NOTES}


@pytest.mark.parametrize(("answer", "expected"), [
    ('"Delivery: 14 March 2026" [supplier-offer.pdf, p. 2]',
     [("supplier-offer.pdf", 2, 2, "Delivery: 14 March 2026")]),
    ('“Teslim: 14 Mart” (teklif.pdf, s. 3)', [("teklif.pdf", 3, 3, "Teslim: 14 Mart")]),
    ('"same quote" [a.pdf, pp. 2–4; notes.txt]',
     [("a.pdf", 2, 4, "same quote"), ("notes.txt", None, None, "same quote")]),
    ('«цитата здесь» [отчёт.pdf, стр. 4]', [("отчёт.pdf", 4, 4, "цитата здесь")]),
    ('"q text" [a.pdf, 第3页]', [("a.pdf", 3, 3, "q text")]),
    ('«نص مقتبس» [عقد.pdf، ص 5]', [("عقد.pdf", 5, 5, "نص مقتبس")]),
    ('“引用文字” [报告.pdf，第2页；表.xlsx]', [("报告.pdf", 2, 2, "引用文字"), ("表.xlsx", None, None, "引用文字")]),
    ('"cell" [plan.xlsx, sheet "Plan"]', [("plan.xlsx", None, None, "cell")]),
    ('Pilot ("Pilot | 2027-03-12" from delivery-schedule.xlsx)',
     [("from delivery-schedule.xlsx", None, None, "Pilot | 2027-03-12")]),
    ("Python 3.11 (released 2022) and [1] and (e.g. this) and (https://example.com/a.html)", []),
])
def test_find_citations_reads_common_styles(answer, expected):
    found = [(c.source, c.first_page, c.last_page, c.quote) for c in find_citations(answer)]
    assert found == expected


def test_quotes_belong_to_the_next_citation_only():
    answer = ('"first quote" [a.pdf, p. 1] and then [b.pdf, p. 2].\n\n'
              'Both "third quote" and "fourth quote" [c.pdf, p. 3]')
    pairs = [(citation.source, citation.quote) for citation in find_citations(answer)]
    assert pairs == [("a.pdf", "first quote"), ("b.pdf", None), ("c.pdf", "third quote"), ("c.pdf", "fourth quote")]


@pytest.mark.parametrize(("answer", "status", "found_page", "found_file"), [
    ('"Delivery: 14 March 2026" [supplier-offer.pdf, p. 2]', VERIFIED, 2, None),
    # Line breaks, hyphenation, case, and curly quotes do not matter.
    ('“delivery: 14 march 2026 for the first shipment” [offers/supplier-offer.pdf, p. 2]', VERIFIED, 2, None),
    ('"Delivery: 14 March … within 45 days" [supplier-offer.pdf, p. 2]', VERIFIED, 2, None),
    ('"Payment is due within 45 day of the delivery" [supplier-offer.pdf, p. 2]', CLOSE, 2, None),
    ('"Prices are valid for 30 days" [supplier-offer.pdf, p. 2]', OTHER_PAGE, 1, None),
    ('"confirmed the pickup window" [supplier-offer.pdf, p. 2]', OTHER_FILE, None, "meeting-notes.txt"),
    ('"Payment is due within 90 days" [supplier-offer.pdf, p. 2]', NOT_FOUND, None, None),
    ('"Delivery" [supplier-offer.pdf, p. 9]', PAGE_MISSING, None, None),
    ('"Delivery" [invoice.pdf, p. 1]', UNKNOWN_SOURCE, None, None),
    ("The offer has a delivery date [supplier-offer.pdf, p. 2].", NO_QUOTE, None, None),
    ('"freight forwarder confirmed" [meeting-notes.txt]', VERIFIED, None, None),
    ('"freight forwarder confirmed" (see meeting-notes.txt)', VERIFIED, None, None),
])
def test_check_answer_statuses(answer, status, found_page, found_file):
    [result] = check_answer(answer, DOCUMENTS).checks
    assert (result.status, result.found_page, result.found_file) == (status, found_page, found_file)


def test_report_passes_only_without_failures():
    good = check_answer('"Delivery: 14 March 2026" [supplier-offer.pdf, p. 2]', DOCUMENTS)
    bad = check_answer('"Delivery: 14 March 2026" [supplier-offer.pdf, p. 1]', DOCUMENTS)
    assert good.passed and not bad.passed
    assert not check_answer("No citations here.", DOCUMENTS).passed


def test_resolve_source_prefers_exact_then_unique_basename():
    available = ["a/report.pdf", "b/report.pdf", "notes.txt"]
    assert resolve_source("a/report.pdf", available) == "a/report.pdf"
    assert resolve_source("NOTES.TXT", available) == "notes.txt"
    assert resolve_source("report.pdf", available) is None
    assert resolve_source("./notes.txt", available) == "notes.txt"


def test_check_command_reads_a_file_and_returns_status(tmp_path, capsys):
    (tmp_path / "notes.txt").write_text("The freight forwarder confirmed the pickup window.\n")
    answer = tmp_path / "answer.md"
    answer.write_text('"confirmed the pickup window" [notes.txt]', encoding="utf-8")
    assert check.main([str(tmp_path), str(answer), "--lang", "en"]) == 0
    assert "1 of 1 citations match" in capsys.readouterr().out

    answer.write_text('"confirmed the delivery window" [notes.txt]', encoding="utf-8")
    assert check.main([str(tmp_path), str(answer), "--lang", "en", "--json"]) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["failed"] == 1 and result["citations"][0]["status"] == NOT_FOUND


def test_check_command_reads_standard_input(tmp_path, monkeypatch, capsys):
    import io

    (tmp_path / "notes.txt").write_text("Alpha beta gamma.\n")
    monkeypatch.setattr("sys.stdin", io.StringIO('"beta gamma" [notes.txt]'))
    assert check.main([str(tmp_path), "-", "--lang", "en"]) == 0
    assert "✓" in capsys.readouterr().out


def test_check_command_without_an_answer(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(check, "_read_clipboard", lambda: "")
    monkeypatch.setattr("sys.stdin.isatty", lambda: True, raising=False)
    assert check.main([str(tmp_path), "--lang", "en"]) == 2
    assert "any2llm check" in capsys.readouterr().err


def test_ground_quotes_expands_fragments_and_fixes_misquotes():
    from any2llm.citations import ground_quotes

    notes = (
        '"Payment is due within 45 days" [supplier-offer.pdf, p. 2]\n'
        '"Prices stay valid for 30 days from the offer date" [supplier-offer.pdf, p. 2]\n'
        '"The moon is made of cheese" [supplier-offer.pdf, p. 1]'
    )
    grounded = ground_quotes(notes, DOCUMENTS)
    # A correct fragment becomes its whole sentence on the same page.
    assert '"Payment is due within 45 days of delivery." [offers/supplier-offer.pdf, p. 2]' in grounded
    # A misquote becomes the real sentence, with the page where it actually is.
    assert '"Prices are valid for 30 days from the offer date." [offers/supplier-offer.pdf, p. 1]' in grounded
    # Nothing similar exists, so the note stays as written and will fail the final check.
    assert '"The moon is made of cheese" [supplier-offer.pdf, p. 1]' in grounded
    assert check_answer(grounded, DOCUMENTS).count(VERIFIED) == 2
