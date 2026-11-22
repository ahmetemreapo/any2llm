"""Pack selected, parsed files into token-limited Markdown documents."""

import re
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET

from .parsers import ParsedFile
from .tokenizer import count_tokens

PRESETS = {"High Detail": 12_000, "Balanced": 25_000, "Single File": None}
_BATCH_NAME = re.compile(r"batch_[0-9]{2,}_of_[0-9]+\.md")
_INVALID_XML = re.compile(r"[^\x09\x0a\x0d\x20-\ud7ff\ue000-\ufffd\U00010000-\U0010ffff]")


def is_batch_name(name: str) -> bool:
    return _BATCH_NAME.fullmatch(name) is not None


def _xml_text(text: str) -> str:
    # Represent characters XML 1.0 cannot encode, including surrogateescaped paths.
    return _INVALID_XML.sub(lambda match: ascii(match[0])[1:-1], text)


@dataclass(frozen=True)
class _Part:
    id: str
    name: str
    file_type: str
    text: str
    number: int = 0


def _render(parts: list[_Part], number: int, total: int, counts: Counter[str]) -> str:
    manifest = ET.Element("manifest", batch=str(number), total=str(total))
    blocks = []
    for part in parts:
        attrs = {"id": part.id, "name": part.name, "type": part.file_type}
        if part.number:
            attrs["part"] = f"{part.number}/{counts[part.id] or 1}"
        ET.SubElement(manifest, "entry", attrs)
        block = ET.Element("file", attrs)
        block.text = part.text
        blocks.append(ET.tostring(block, encoding="unicode", short_empty_elements=False))
    ET.indent(manifest)
    return "\n\n".join([ET.tostring(manifest, encoding="unicode"), *blocks]) + "\n"


def _split_end(text: str, start: int, limit: int, fits: Callable[[str], bool]) -> int:
    """Find a fitting prefix without repeatedly encoding the entire remaining file."""
    low = start
    high = min(len(text), start + 4 * limit)
    while fits(text[start:high]):
        if high == len(text):
            return high
        low, high = high, min(len(text), start + 2 * (high - start))
    while high - low > 1:
        mid = (low + high) // 2
        if fits(text[start:mid]):
            low = mid
        else:
            high = mid
    if low == start:
        raise ValueError("Token limit is too small for the file metadata and content.")
    for separator in ("\n", " ", "\t"):
        end = text.rfind(separator, start, low) + 1
        # BPE token counts can increase when shortening a prefix.
        if end > start and fits(text[start:end]):
            return end
    return low


def _group(files: list[_Part], limit: int, total: int, counts: Counter[str]) -> list[list[_Part]]:
    batches: list[list[_Part]] = [[]]

    def fits(part: _Part) -> bool:
        batch = [*batches[-1], part]
        return count_tokens(_render(batch, len(batches), total, counts)) <= limit

    for file in files:
        if fits(file):
            batches[-1].append(file)
            continue
        if batches[-1]:
            batches.append([])
            if fits(file):
                batches[-1].append(file)
                continue

        if not file.text:
            raise ValueError("Token limit is too small for the file metadata.")
        start = 0
        number = 1
        while start < len(file.text):
            part = replace(file, number=number)

            def prefix_fits(prefix: str) -> bool:
                return fits(replace(part, text=prefix))

            end = _split_end(file.text, start, limit, prefix_fits)
            batches[-1].append(replace(part, text=file.text[start:end]))
            start = end
            number += 1
            if start < len(file.text):
                batches.append([])
    return batches


def _documents(files: list[_Part], limit: int | None) -> list[str]:
    if not files:
        return []
    if limit is None:
        return [_render(files, 1, 1, Counter())]

    reserved_total = 1
    reserved_counts: Counter[str] = Counter()
    while True:
        batches = _group(files, limit, reserved_total, reserved_counts)
        total = len(batches)
        counts = Counter(part.id for batch in batches for part in batch if part.number)
        docs = [_render(batch, i, total, counts) for i, batch in enumerate(batches, 1)]
        # Crossing a digit boundary in the final totals can require another pass.
        if all(count_tokens(doc) <= limit for doc in docs):
            return docs
        reserved_total = max(reserved_total, total)
        reserved_counts |= counts


def build_batches(
    selected: Mapping[Path, ParsedFile],
    *,
    preset: str = "Balanced",
    max_tokens: int | None = None,
) -> dict[str, str]:
    """Render named batches in upload order."""
    limit = PRESETS[preset] if max_tokens is None else max_tokens
    if limit is not None and limit < 1:
        raise ValueError("Token limit must be positive.")
    files = [
        _Part(str(i), _xml_text(path.as_posix()), _xml_text(parsed.file_type), _xml_text(parsed.text))
        for i, (path, parsed) in enumerate(selected.items(), 1)
    ]
    docs = _documents(files, limit)
    return {f"batch_{i:02d}_of_{len(docs)}.md": doc for i, doc in enumerate(docs, 1)}


def write_pack(output_dir: Path, documents: Mapping[str, str]) -> list[Path]:
    """Stage all documents before replacing the previous pack."""
    if not documents:
        return []

    output_dir.mkdir(parents=True, exist_ok=True)
    paths = [output_dir / name for name in documents]
    with TemporaryDirectory(dir=output_dir) as staging:
        for path in paths:
            if path.is_dir():
                raise IsADirectoryError(f"Output path is a directory: {path}")
            (Path(staging) / path.name).write_text(documents[path.name], encoding="utf-8", newline="\n")
        for path in paths:
            (Path(staging) / path.name).replace(path)
    for stale in set(output_dir.iterdir()).difference(paths):
        if is_batch_name(stale.name) and stale.is_file():
            stale.unlink()
    return paths


def write_batches(
    selected: Mapping[Path, ParsedFile],
    output_dir: Path,
    *,
    preset: str = "Balanced",
    max_tokens: int | None = None,
) -> list[Path]:
    """Write batches in selection order and return their paths in upload order."""
    return write_pack(output_dir, build_batches(selected, preset=preset, max_tokens=max_tokens))
