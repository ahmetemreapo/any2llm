"""Build one paste-ready prompt for the complete pack."""

from collections.abc import Sequence

from .messages import PROMPTS


def master_prompt(batch_names: Sequence[str], lang: str, task: str = "", *, has_ocr: bool = False) -> str:
    if lang not in PROMPTS:
        raise ValueError(f"Unsupported language: {lang}")
    text = PROMPTS[lang]
    task = task.strip()
    multiple = len(batch_names) > 1
    flow = "multi" if multiple else "single"
    opening = text[f"task_{flow}" if task else flow].format(
        first=batch_names[0], continue_word=text["continue"],
    )
    sections = [
        opening, text["reply_language"],
        text["attachments"].format(filenames=", ".join(batch_names)),
    ]
    if multiple:
        sections.append(text["upload_order"])
    if has_ocr:
        sections.append(text["ocr_sources"])
    if task:
        sections.extend((f"{text['task']}: {task}", text["task_evidence"], text["citation_format"]))
        if multiple:
            sections.append(text["task_final"])
    else:
        sections.extend((text["analysis"], text["sources"], text["citation_format"], text["closing"]))
    return "\n\n".join(sections) + "\n"
