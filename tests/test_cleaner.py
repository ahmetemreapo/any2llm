from any2llm.cleaner import clean_pages, clean_text


def test_prose_whitespace_and_indentation():
    assert clean_text("\r\nTitle  \r\n  \r\n\r\n    indented\t\r\n") == "Title\n\n    indented"
    assert clean_text("  \n\t") == ""


def test_repeated_page_margins_and_numbering():
    assert clean_pages([
        "Handbook\nFirst\nShared body line\nDraft\nPage 1 of 3",
        "Handbook\nSecond\nShared body line\nDraft\nPage 2 of 3",
        "Appendix\nOther material\n3",
    ]) == "First\nShared body line\n\nSecond\nShared body line\n\nAppendix\nOther material"


def test_preserve_short_pages_and_unique_edges():
    assert clean_pages(["", "Only one line", "Only one line", "Last\npage text"]) == (
        "Only one line\n\nOnly one line\n\nLast\npage text"
    )
    assert clean_pages([]) == ""
