"""any2llm ask: answer a question about a folder with a local model, then check its citations."""

import argparse
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

from . import demo, ocr
from .check import print_report
from .citations import Report, check_answer, ground_quotes
from .languages import LANGUAGE_NAMES, system_language
from .llm import Backend, LLMError, chat, connect
from .messages import MESSAGES, PROMPTS, help_text
from .packer import build_batches
from .parsers import ParsedFile
from .sources import load
from .terminal import display_count, display_path
from .tokenizer import count_tokens

FINAL_TOKENS = 1536
NOTE_TOKENS = 768
# Model tokenizers often need more tokens than cl100k_base, especially outside English.
_TOKENIZER_MARGIN = 0.8
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


class Asker:
    """Answer questions over parsed documents with map-and-combine passes that fit the model's context."""

    def __init__(
        self, backend: Backend, documents: Mapping[Path, ParsedFile], lang: str, *,
        status: Callable[[str], None] = lambda _: None, send=chat,
    ):
        self.backend = backend
        self.documents = documents
        self.text = PROMPTS[lang]
        self.msg = MESSAGES[lang]
        self.status = status
        self.send = send
        self._by_name = {path.as_posix(): parsed for path, parsed in documents.items()}

    def _budget(self, system: str, question: str, reply: int) -> int:
        reply = min(reply, self.backend.context // 4)
        fixed = count_tokens(system) + count_tokens(question) + 96
        budget = int((self.backend.context - fixed - reply) * _TOKENIZER_MARGIN)
        if budget < 400:
            raise LLMError("ask_context_small")
        return budget

    def answer(self, question: str, on_text: Callable[[str], None]) -> str:
        system = self.text["ask_system"]
        plain_question = f'{self.text["question"]}: {question}'
        question_block = f'{plain_question}\n\n{self.text["ask_format"]}'
        budget = self._budget(system, question_block, FINAL_TOKENS)
        batches = list(build_batches(self.documents, max_tokens=budget).values())
        if len(batches) == 1:
            self.status(self.msg["ask_thinking"])
            return self._final(system, f"{batches[0]}\n\n{question_block}", on_text)

        notes = []
        map_system = self.text["ask_notes"]
        map_budget = self._budget(map_system, map_system + plain_question, NOTE_TOKENS)
        if map_budget < budget:
            batches = list(build_batches(self.documents, max_tokens=map_budget).values())
        for number, batch in enumerate(batches, 1):
            self.status(self.msg["ask_reading"].format(part=number, total=len(batches)))
            instruction = map_system.format(part=number, total=len(batches))
            # Small models follow the instruction they read last, so it closes the message too.
            reply = self.send(self.backend, [
                {"role": "system", "content": instruction},
                {"role": "user", "content": f"{batch}\n\n{plain_question}\n\n{instruction}"},
            ], max_tokens=NOTE_TOKENS)
            if not _is_empty_note(reply):
                notes.append(ground_quotes(reply, self._by_name))
        if not notes:
            on_text(self.msg["ask_nothing"])
            return ""
        notes = self._merge(notes, plain_question, budget)
        self.status(self.msg["ask_combining"].format(parts=display_count(len(batches), self.msg)))
        content = "<notes>\n" + "\n\n".join(notes) + "\n</notes>\n\n" + question_block
        # The notes replace the <file> blocks, so the final request has its own instructions.
        return self._final(self.text["ask_final"], content, on_text)

    def _merge(self, notes: list[str], question_block: str, budget: int) -> list[str]:
        """Shrink notes until they fit one final request."""
        for _ in range(4):
            if count_tokens("\n\n".join(notes)) <= budget:
                return notes
            groups: list[list[str]] = [[]]
            for note in notes:
                if groups[-1] and count_tokens("\n\n".join([*groups[-1], note])) > budget:
                    groups.append([])
                groups[-1].append(note)
            merged = []
            for group in groups:
                reply = self.send(self.backend, [
                    {"role": "system", "content": self.text["ask_merge"]},
                    {"role": "user", "content": "<notes>\n" + "\n\n".join(group) + "\n</notes>\n\n" + question_block},
                ], max_tokens=NOTE_TOKENS)
                if not _is_empty_note(reply):
                    merged.append(reply)
            notes = merged or notes[:1]
        return notes

    def _final(self, system: str, content: str, on_text: Callable[[str], None]) -> str:
        return self.send(self.backend, [
            {"role": "system", "content": system}, {"role": "user", "content": content},
        ], max_tokens=FINAL_TOKENS, on_text=on_text)

    def check(self, answer: str) -> Report:
        return check_answer(answer, self._by_name)


def _is_empty_note(reply: str) -> bool:
    words = reply.strip().strip("*.`").split()
    return not words or (words[0].upper().startswith("NONE") and len(words) <= 3)


def _arguments(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="any2llm ask", add_help=False, allow_abbrev=False, exit_on_error=False)
    parser.add_argument("words", nargs="*")
    parser.add_argument("-r", "--recursive", action="store_true")
    parser.add_argument("--model")
    parser.add_argument("--api", metavar="URL")
    parser.add_argument("--context", type=int, metavar="TOKENS")
    parser.add_argument("--lang", choices=LANGUAGE_NAMES)
    parser.add_argument("--ocr", action="store_true")
    parser.add_argument("--ocr-lang", metavar="LANG")
    parser.add_argument("--exclude", action="append", default=[], metavar="GLOB")
    parser.add_argument("--include-sensitive", action="store_true")
    parser.add_argument("--no-check", action="store_true")
    parser.add_argument("-h", "--help", action="store_true")
    return parser.parse_args(argv)


def _split_target(words: list[str]) -> tuple[str, str]:
    """The first word is the folder when it names one; the rest is the question."""
    if words and (words[0] == "demo" or Path(words[0]).is_dir()):
        return words[0], " ".join(words[1:]).strip()
    return ".", " ".join(words).strip()


class _Output:
    def __init__(self, stream):
        self.stream = stream
        self.wrote = False

    def __call__(self, text: str) -> None:
        self.wrote = True
        self.stream.write(text)
        self.stream.flush()


def _status(line: str) -> None:
    print(f"… {line}", file=sys.stderr, flush=True)


def main(argv: list[str]) -> int:
    lang = system_language()
    try:
        args = _arguments(argv)
    except (argparse.ArgumentError, SystemExit) as exc:
        option = getattr(exc, "argument_name", "") or ""
        print(MESSAGES[lang]["invalid_option"].format(option=option), "any2llm ask --help", file=sys.stderr)
        return 2
    lang = args.lang or lang
    msg = MESSAGES[lang]
    if args.help:
        print(help_text(lang))
        return 0
    folder, question = _split_target(args.words)
    interactive = sys.stdin.isatty() and sys.stdout.isatty()
    if folder == "demo":
        source_lang = "tr" if lang == "tr" else "en"
        with TemporaryDirectory(prefix="any2llm-demo-") as temporary:
            demo.copy_sources(source_lang, Path(temporary))
            return _run(args, Path(temporary), question or demo.QUESTIONS[source_lang], lang, interactive=False)
    if not question and not interactive:
        print(msg["ask_no_question"], file=sys.stderr)
        return 2
    return _run(args, Path(folder), question, lang, interactive=interactive)


def _run(args: argparse.Namespace, folder: Path, question: str, lang: str, *, interactive: bool) -> int:
    msg = MESSAGES[lang]
    try:
        backend = connect(args.api, args.model, args.context)
    except LLMError as exc:
        print(msg[exc.key].format(address=exc.detail, model=exc.detail, detail=exc.detail), file=sys.stderr)
        return 1
    host = urlsplit(backend.base).hostname or ""
    print(f"any2llm · {backend.label}", file=sys.stderr)
    if host not in _LOCAL_HOSTS:
        print(msg["llm_remote"].format(host=host), file=sys.stderr)

    ocr_lang = args.ocr_lang or ("eng" if args.ocr else None)
    if ocr_lang is not None and (error := ocr.setup_error(ocr_lang)):
        print(msg[error].format(lang=display_path(ocr_lang)), file=sys.stderr)
        ocr_lang = None
    try:
        library = load(
            folder, recursive=args.recursive, exclude=args.exclude,
            include_sensitive=args.include_sensitive, ocr_lang=ocr_lang,
        )
    except OSError as exc:
        key = {FileNotFoundError: "no_folder", NotADirectoryError: "not_folder"}.get(type(exc), "read_folder")
        print(f'{msg[key]}: {display_path(folder)}', file=sys.stderr)
        return 1
    if not library.documents:
        print(msg["empty"], file=sys.stderr)
        return 1
    summary = msg["ask_read"].format(files=display_count(len(library.documents), msg))
    if library.skipped:
        summary += " · " + msg["ask_skipped"].format(count=display_count(len(library.skipped), msg))
    print(f"… {summary}", file=sys.stderr, flush=True)

    asker = Asker(backend, library.documents, lang, status=_status)
    code = 0
    while True:
        if not question:
            try:
                question = input(f'\n{msg["ask_prompt"]} › ').strip()
            except (EOFError, KeyboardInterrupt):
                print(file=sys.stderr)
                return code
            if not question:
                return code
        output = _Output(sys.stdout)
        try:
            if interactive:
                print(file=sys.stdout)
            answer = asker.answer(question, output)
        except LLMError as exc:
            print(file=sys.stderr)
            print(msg[exc.key].format(address=backend.base, model=backend.model, detail=exc.detail), file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            print(f'\n{msg["cancelled"]}', file=sys.stderr)
            return 130
        if output.wrote:
            print(file=sys.stdout, flush=True)
        if answer and not args.no_check:
            report = asker.check(answer)
            print_report(report, msg, stream=sys.stderr)
            if not report.passed:
                code = 1
        if not interactive:
            return code
        question = ""
