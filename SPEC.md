# SPEC.md — any2llm

## Goal
`any2llm` is an open-source CLI tool that converts mixed files in a folder (PDF, DOCX, PPTX, XLSX, code, text) into token-balanced Markdown batches with multi-turn prompts so users can bypass LLM file upload limits without losing detail.

## Target Directory Structure
any2llm/
├── pyproject.toml
├── README.md
├── LICENSE
├── AGENTS.md
├── SPEC.md
├── src/
│   └── any2llm/
│       ├── __init__.py
│       ├── cli.py          # Entry point, CLI args, interactive flow
│       ├── scanner.py      # Folder scan, ignore rules, binary detection
│       ├── parsers.py      # Extractors for text/code, pdf, docx, pptx, xlsx
│       ├── cleaner.py      # Whitespace and repetitive page noise cleanup
│       ├── tokenizer.py    # Token counting (tiktoken cl100k_base + fallback)
│       ├── packer.py       # Token-balanced batching, large-file splitting, XML manifest
│       └── prompts.py      # Multi-turn anti-laziness prompts (en/tr) + clipboard helper
└── tests/

## Dependencies
- `pypdf` (PDF)
- `python-docx` (Word)
- `python-pptx` (PowerPoint)
- `openpyxl` (Excel)
- `tiktoken` (token counting)
- `questionary` (interactive checkbox UI)
- `rich` (clean terminal tables and status)
- `pyperclip` (clipboard copy)
- `pytest` (dev dependency for tests)

## Core User Flow
1. User runs `any2llm` inside any folder (or `any2llm /path/to/dir`).
2. Tool scans files in that folder (non-recursive by default; optional `-r/--recursive`), ignoring hidden files, `.git`, `.venv`, `node_modules`, `__pycache__`, and `_llm_pack`.
3. Tool parses readable files and estimates token counts. Unreadable/binary/image files are separated into a "Skipped (attach manually)" list.
4. Interactive checkbox menu (`questionary`) lists all readable files with file type and token count. ALL files are checked by default. User toggles unwanted files with Space and confirms with Enter.
5. User selects a detail preset:
   - High Detail (~12,000 tokens per batch)
   - Balanced (~25,000 tokens per batch)
   - Single File (no split)
6. User optionally types a custom task/goal (e.g., "Explain every topic in detail for my exam") or presses Enter to use the default deep-analysis instruction.
7. Tool writes output to `_llm_pack/`:
   - `batch_01_of_N.md`, `batch_02_of_N.md`, ...
   - `PROMPTS.md` containing all turn prompts.
8. Each batch Markdown file starts with an XML `<manifest>` listing batch number, total batches, and included files, followed by `<file id="..." name="..." type="...">` blocks. If a single file exceeds the batch token limit, split it cleanly into numbered parts (`part 1/2`, `part 2/2`).
9. Interactive Clipboard Walkthrough:
   - Copy Turn 1 prompt to clipboard automatically and tell the user which batch file to upload.
   - Wait for Enter, then copy Turn 2 prompt, and repeat until the final batch.
   - Final turn prompt instructs the LLM to analyze the last batch AND synthesize all previous turns in full detail.

## CLI Flags
- `path` (optional, defaults to current directory)
- `-r, --recursive` (include subdirectories)
- `--max-tokens INT` (override batch token limit)
- `--lang [en|tr]` (language for generated LLM prompts, default `en`)
- `-o, --output DIR` (output folder name, default `_llm_pack`)
- `-y, --yes` (skip interactive prompts and pack all files immediately)
