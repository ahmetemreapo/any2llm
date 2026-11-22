"""Generate batch-specific prompts and guide uploads in conversation order."""

from collections.abc import Sequence
from subprocess import SubprocessError

import pyperclip


_EN = {
    "heading": "Turn {number} of {total} — {batch}",
    "task": "Task",
    "default": "Explain the material in depth so the reader can understand and apply it.",
    "analyze": (
        "Read the attached batch. Use its manifest to check every file and numbered part. "
        "For each, explain the findings relevant to the task and cite the filename and part. "
        "Preserve concrete evidence such as definitions, figures, examples, and exceptions. "
        "Identify gaps explicitly. Ground each conclusion in the supplied material."
    ),
    "first": (
        "Start the analysis now. End with a record of findings, open questions, and incomplete "
        "files to carry into the next turn. Reserve the overall synthesis for the final batch."
    ),
    "middle": (
        "Relate this batch to the earlier findings. Join numbered parts by file ID, explain "
        "what the new evidence adds or changes, and update the record of open questions and "
        "incomplete files. Reserve the overall synthesis for the final batch."
    ),
    "final": (
        "Analyze this last batch in the same detail as the earlier batches. Then deliver a "
        "standalone synthesis answering the task across all turns. Reconnect split files, "
        "reconcile conflicting evidence, and identify any questions the sources leave open. "
        "Check every batch against the synthesis so earlier details survive."
    ),
    "single": (
        "This batch contains the entire pack. After analyzing each file, deliver a standalone "
        "synthesis answering the task. Connect findings across sources, explain conflicting "
        "evidence, and identify any questions the sources leave open."
    ),
}

_TR = {
    "heading": "Tur {number}/{total} — {batch}",
    "task": "Görev",
    "default": "İçeriği, okuyucunun anlayıp uygulayabileceği kadar ayrıntılı açıkla.",
    "analyze": (
        "Ekteki paketi oku. Başındaki dosya listesinden her dosyayı ve numaralı parçayı "
        "kontrol et. Her biri için görevle ilgili bulguları açıkla, dosya adını ve varsa "
        "parça numarasını belirt. Tanımları, sayısal verileri, örnekleri ve istisnaları "
        "koru. Eksikleri açıkça belirt. Her sonucu kaynaklardaki kanıtlarla destekle."
    ),
    "first": (
        "Analize bu turda başla. Yanıtın sonunda sonraki tura aktarılacak bulguları, açık "
        "soruları ve parçaları eksik dosyaları listele. Genel sentezi son pakete bırak."
    ),
    "middle": (
        "Bu paketi önceki bulgularla ilişkilendir. Numaralı parçaları dosya kimliğine göre "
        "birleştir. Yeni kanıtların hangi bulguları desteklediğini veya değiştirdiğini açıkla. "
        "Açık sorular ve parçaları eksik dosyalar listesini güncelle. Genel sentezi son pakete bırak."
    ),
    "final": (
        "Bu son paketi de öncekiler kadar ayrıntılı incele. Ardından tüm turları kapsayan, "
        "görevi yanıtlayan ve tek başına okunabilen bir sentez yaz. Bölünmüş dosyaların "
        "parçalarını bir araya getir, çelişkileri değerlendir ve yanıtsız kalan soruları "
        "belirt. Önceki ayrıntıların korunduğunu her paketi sentezle karşılaştırarak denetle."
    ),
    "single": (
        "Tüm içerik bu pakette. Her dosyayı inceledikten sonra görevi yanıtlayan, tek başına "
        "okunabilen bir sentez yaz. Kaynaklardaki bulguları ilişkilendir, çelişkileri "
        "değerlendir ve yanıtsız kalan soruları belirt."
    ),
}


def generate_prompts(batch_names: Sequence[str], lang: str = "en", task: str = "") -> list[str]:
    """Return one paste-ready Markdown prompt for each batch in upload order."""
    templates = {"en": _EN, "tr": _TR}
    if lang not in templates:
        raise ValueError(f"Unsupported prompt language: {lang}")
    words = templates[lang]
    goal = task.strip() or words["default"]
    total = len(batch_names)
    prompts = []
    for number, batch in enumerate(batch_names, 1):
        if total == 1:
            stage = "single"
        elif number == 1:
            stage = "first"
        elif number == total:
            stage = "final"
        else:
            stage = "middle"
        heading = words["heading"].format(number=number, total=total, batch=batch)
        prompts.append(
            f"## {heading}\n\n**{words['task']}**\n\n{goal}\n\n"
            f"{words['analyze']}\n\n{words[stage]}"
        )
    return prompts


def clipboard_walkthrough(batch_names: Sequence[str], prompts: Sequence[str]) -> None:
    """Copy each saved prompt and wait for the user before advancing."""
    clipboard_available = True
    for number, (batch, prompt) in enumerate(zip(batch_names, prompts, strict=True), 1):
        if clipboard_available:
            try:
                pyperclip.copy(prompt)
            except (pyperclip.PyperclipException, OSError, SubprocessError, ImportError):
                clipboard_available = False
                print("Clipboard unavailable. Use PROMPTS.md in the output folder.")
        action = "Paste the copied prompt" if clipboard_available else f"Copy turn {number} from PROMPTS.md"
        print(f"Turn {number}: {action} and attach {batch} in the same chat.")
        if number < len(prompts):
            input("After the reply, press Enter for the next turn. ")
