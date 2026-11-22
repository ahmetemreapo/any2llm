from unittest.mock import Mock

import pyperclip
import pytest

from any2llm import clipboard, prompts


@pytest.mark.parametrize(("lang", "signal", "single", "synthesis"), [
    ("en", '"continue"', "entire batch", "comprehensive synthesis across all files"),
    ("tr", '"devam"', "paketin tamamını", "tüm dosyaları kapsayan bir sentez"),
])
def test_master_prompt(lang, signal, single, synthesis):
    names = ["batch_01_of_2.md", "batch_02_of_2.md"]
    multi = prompts.master_prompt(names, lang)
    one = prompts.master_prompt(["batch_01_of_1.md"], lang)
    assert signal in multi and signal not in one
    assert single in one
    assert names[0] in multi
    assert "batch_01_of_1.md" in one
    for text in (one, multi):
        assert "<manifest>" in text and synthesis in text
    assert prompts.master_prompt(names, lang, " \n\t ") == multi


@pytest.mark.parametrize(("lang", "task", "signal", "intermediate", "final", "citation", "gap"), [
    ("en", "List delivery dates in a table.", '"continue"', "only task-relevant findings",
     "one answer in the format requested by the task", "cite the filename", "gaps in the evidence"),
    ("tr", "Teslim tarihlerini tabloya dök.", '"devam"', "yalnızca görevle ilgili bulguları",
     "görevin istediği biçimde tek bir yanıtta", "dosya adını", "kanıt eksiklerini"),
])
@pytest.mark.parametrize("multiple", [False, True])
def test_custom_task_controls_scope_and_format(lang, task, signal, intermediate, final, citation, gap, multiple):
    names = ["batch_01_of_2.md", "batch_02_of_2.md"] if multiple else ["batch_01_of_1.md"]
    custom = prompts.master_prompt(names, lang, f"  {task}\n")
    catalog = prompts.PROMPTS[lang]
    assert task in custom and citation in custom.casefold() and gap in custom and "<page>" in custom
    assert 'extraction="no-extractable-text"' in custom
    assert custom.index(names[0]) < custom.index(task)
    assert (signal in custom) is multiple
    assert (intermediate in custom) is multiple
    assert (final in custom) is multiple
    assert catalog["analysis"] not in custom and catalog["closing"] not in custom
    assert catalog["single"].format(first=names[0]) not in custom


@pytest.mark.parametrize(("lang", "instructions"), [
    ("en", [
        "tables, quotations, and numerical claims", "physical PDF page number in the <page>",
        "research questions, hypotheses, and quotations", "effect versus association",
        "report the original wording", "label your interpretation or calculation",
        "quote the readable source text first", "label the reconstruction as uncertain",
    ]),
    ("tr", [
        "tablolar, alıntılar ve sayısal iddialar", "<page> işaretindeki fiziksel PDF sayfa numarasını",
        "Araştırma sorularında, hipotezlerde ve alıntılarda", "etki ile ilişki arasındaki ayrım",
        "önce kaynaktaki ifadeyi veya sayıları ver", "kendi yorumunu veya hesabını açıkça belirt",
        "önce kaynaktaki okunabilen metni aktar", "tahminini belirsiz olarak işaretle",
    ]),
])
def test_master_prompt_requests_citations_and_source_fidelity(lang, instructions):
    for names in (["batch_01_of_1.md"], ["batch_01_of_2.md", "batch_02_of_2.md"]):
        prompt = prompts.master_prompt(names, lang)
        assert all(instruction in prompt for instruction in instructions)


@pytest.mark.parametrize(("contents", "expected"), [("prompt", True), ("", False)])
def test_clipboard_verifies_silent_backend_failures(monkeypatch, contents, expected):
    copy = Mock()
    monkeypatch.setattr(pyperclip, "copy", copy)
    monkeypatch.setattr(pyperclip, "paste", lambda: contents)
    assert clipboard._copy_and_verify("prompt") is expected
    copy.assert_called_once_with("prompt")


@pytest.mark.parametrize(("lang", "missing", "document_text"), [
    ("en", "ask for it by name", "material to analyze"),
    ("tr", "dosyayı adıyla iste", "incelenecek belge içeriği"),
])
def test_prompt_lists_attachments_and_handles_missing_files(lang, missing, document_text):
    names = ["batch_01_of_2.md", "batch_02_of_2.md"]
    prompt = prompts.master_prompt(names, lang, "Custom goal")
    assert all(name in prompt for name in names)
    assert missing in prompt and document_text in prompt and "Custom goal" in prompt
