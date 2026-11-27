# any2llm

Convert a folder of mixed documents, code, and text into Markdown batches for an LLM conversation.

## First-run setup

Run `any2llm` in the source folder or pass a folder path. The wizard first asks for a language in your system locale. The terminal interface and generated prompts support 11 languages: English (`en`), Mandarin Chinese in simplified script (`zh`), Hindi (`hi`), Spanish (`es`), French (`fr`), Arabic (`ar`), Bengali (`bn`), Portuguese (`pt`), Russian (`ru`), Urdu (`ur`), and Turkish (`tr`). Unsupported system locales use English. The first run highlights the detected language. The remaining questions immediately use the language you choose. Choose a default detail level and whether to open the output folder automatically (enabled by default).

| Detail level | Batch limit |
| --- | --- |
| High Detail | 12,000 tokens |
| Balanced (recommended, default) | 25,000 tokens |
| Single File | Unlimited, without splitting |

The wizard saves preferences in `~/.config/any2llm/config.json` and continues to file selection. Run `any2llm setup` or `any2llm --config` to review the saved choices and change them. An interactive terminal is required for setup. Without an interactive terminal, `-y` uses the saved preferences or temporary defaults.

## Daily use

1. Scan the folder, optionally including subdirectories. Ignore hidden entries, common dependency, environment, cache and build directories, and the output directory. Apply root `.gitignore` rules and any `--exclude` globs. Skip potentially sensitive files before extracting text from PDF, DOCX, PPTX, XLSX, EPUB, HTML, code, and plain text. Report sensitive files and extraction failures with reasons and suggested next steps in the active language.
2. A single checkbox lists files that pass the discovery filters. All start checked. Use Space to toggle and Enter to confirm. Use `--plain` for numbered choices and full filenames. Read and parse only selected candidates. Skip unusable files and prepare no new pack if none remain.
3. Write `batch_01_of_N.md` and subsequent numbered batches to `_llm_pack/`. Each starts with an XML `<manifest>` followed by matching `<file>` blocks. Oversized files have numbered parts with a shared file ID. The output folder records which files belong to the pack. Reruns replace or remove only recorded files whose contents still match. For destination conflicts, choose another folder with `-o`.
4. Save one master prompt to `PROMPT.txt` and automatically try to copy it to the clipboard. Confirm whether the copy succeeded. If the clipboard is unavailable, show how to copy the saved instructions manually. The output folder opens in the system file manager when enabled.
5. Report the attachment count, total size of the UTF-8 batch files, and the token counting method. For capped batches, count tokens with `cl100k_base` or estimate one token per four characters when unavailable. Attach the batch files together if they fit the chat's attachment limit. Otherwise, attach the first file and send the remaining files in order with the continuation messages in the same chat. Paste the prompt once. By default, the prompt requests a thorough analysis and synthesis. With `--task`, it asks for an answer in the task's scope and format, with citations and any relevant gaps in the evidence. For multiple batches, the LLM processes the files in order and waits for the localized continuation word between batches. It requests missing attachments by name when their batch is due. With a custom task, intermediate replies report relevant findings and the final reply combines them into the requested output. The terminal command exits as soon as packing and handoff are complete.

Each packed PDF retains its physical page numbers in `<page number="…">` elements, including on pages that span multiple batches. Pages with no extractable text have the attribute `extraction="no-extractable-text"`. The terminal reports these pages for packed files and groups consecutive numbers into ranges. Extraction is assessed before removing repeated headers and footers. If a page's text extraction is damaged, the optional `pdftotext` utility can retry that page. If the retry fails, `status="partial"` marks the affected page and any readable text is kept. PDFs without any usable text are skipped and reported at file level.

Limit source files to 32 MiB, PDFs to 500 pages, and Office archives to 128 MiB of uncompressed entries. Run each selected extraction in a worker with a 120-second deadline. Check extracted text locally for common credential formats. Show only the filename and finding type and remind the user to review the batches before uploading. Keep the extracted content in the batch.

When OCR is enabled, the extractor also tries `pdftotext` on otherwise empty pages before running local OCR. Only pages with no usable text are rendered for OCR. Successful recognition marks the page and each of its batch fragments with `extraction="ocr"`. The terminal reports which pages were read with OCR. If OCR produces no usable text, the page retains its missing-text marker. When required tools or language data are missing, the terminal reports the prerequisite and continues with regular extraction. The master prompt asks the model to cite physical PDF page numbers and flag uncertain OCR readings when the pack contains OCR text.

Parse the manifest as XML. File and page tags have XML-escaped attributes and raw text bodies. Read each body up to its exact closing tag. Within a body, the writer inserts one backslash after `<` in each literal `</file>`, `</page>`, or `</manifest>`, including spellings that already have backslashes before the slash. For example, `</file>` becomes `<\/file>` and `<\/file>` becomes `<\\/file>`. To recover the text, remove exactly one backslash from each such spelling in each file or page fragment before joining its parts. Preserve literal entities such as `&amp;` during decoding. Lone Unicode surrogates retain their printable backslash representation for UTF-8 output.

The sensitive filename filter is case-insensitive. It matches `*.pem`, `*.key`, `*.p12`, `*.pfx`, `id_rsa*`, `id_ed25519*`, `credentials*`, `secrets*`, and `*.kdbx`. The filter applies to automatic selection with `-y`.

Use `/` as the separator in `--exclude` globs and root `.gitignore` rules. A bare pattern matches names at any depth. A leading slash or a slash within the pattern makes it relative to the scan root. A trailing slash limits the pattern to directories. The root `.gitignore` supports comments and `!` exceptions. The last matching rule takes precedence, and the scan does not descend into excluded directories. If the root `.gitignore` cannot be read, the scan reports it and stops before selecting files.

EPUB books are read in spine order, with the book title as the first heading. Each chapter's XHTML becomes readable text. Books whose `META-INF/encryption.xml` uses anything other than font obfuscation are protected with DRM and skipped as encrypted. HTML files that contain a doctype, `<html>`, or `<body>` and no template markers (`{{`, `{%`, `{#`, `<%`, `<?php`) are converted to text with headings, lists, tables, and preformatted blocks. Scripts, styles, and markup are dropped and image alt text is kept. Other HTML files stay as source code. CSV and TSV files are packed as text.

## Standard output

`--stdout` selects every candidate that passes the scan filters, packs them into one unsplit batch, and writes it to standard output. It writes no files, does not touch the clipboard, and does not run first-run setup. Scan progress, skipped files, page warnings, and credential findings go to standard error. `--max-tokens` and `--output` are rejected with `--stdout`.

## MCP server

`any2llm mcp [DIR]` serves the folder `DIR` (default: the current directory) to AI apps over the Model Context Protocol on stdio. It accepts `--lang`, `--ocr`, and `--ocr-lang`. It answers stateless `2026-07-28` requests, including `server/discover`, and the `initialize` handshake of versions `2025-11-25`, `2025-06-18`, `2025-03-26`, and `2024-11-05`. Requests whose `_meta` names another version get error `-32022` with the supported versions. Only protocol messages are written to standard output.

| Tool | Arguments | Result |
| --- | --- | --- |
| `list_documents` | `folder`, `recursive` | Readable files and skipped files with reasons |
| `read_documents` | `folder`, `paths`, `recursive`, `batch`, `max_tokens` | One batch in the pack format above, with notes on skipped files, pages without text, OCR pages, and possible credentials |

Folders resolve relative to `DIR` and must stay inside it after resolving symbolic links. Requested paths must be candidates of the scan, so hidden, ignored, and sensitive files are never read. `max_tokens` defaults to 25,000 and accepts 1,000 to 200,000. One call reads at most 100 files. A reply that is not the last batch says which batch to request next. Results are deterministic for unchanged files, so each call can request any batch without server-side session state. Invalid arguments return a tool result with `isError: true`.

## Command-line options

| Option | Effect |
| --- | --- |
| `folder` | Folder to scan, defaults to the current directory |
| `-r`, `--recursive` | Include subdirectories |
| `--lang CODE` | Override the terminal and master prompt language |
| `--max-tokens INT` | Override the batch limit with a positive integer |
| `--task TEXT` | Use a custom task to set the scope and format of the master prompt |
| `--ocr` | Use English OCR on PDF pages with no extractable text |
| `--ocr-lang LANG` | Enable OCR with one or more installed Tesseract languages, joined with `+` for a multilingual scan |
| `--no-open` | Skip opening the file manager |
| `-o DIR`, `--output DIR` | Output directory, relative to the scanned folder unless absolute |
| `-y`, `--yes` | Automatically select all candidates that pass the scan filters |
| `--include-sensitive` | Bypass the sensitive filename filter for this run |
| `--exclude GLOB` | Skip matching files and directories. Repeat to add patterns. |
| `--stdout` | Print one unsplit pack to standard output. See [Standard output](#standard-output). |
| `--plain` | Use numbered menus |
| `--details` | List all files left out |
| `-h`, `--help` | Show help |

Packing overrides apply only to the current run. The older `--ui-lang` spelling accepts the same language codes as `--lang`. The former `id` value is still accepted for compatibility and leaves the active language unchanged.

## Dependencies

Use Python 3.11 or newer. Use pypdf, python-docx, python-pptx, and openpyxl for document extraction. Require Pillow 13.0.0 or newer for python-pptx and defusedxml for Excel XML parsing. Use tiktoken with an offline fallback for token counts, questionary for interactive selection, pyperclip for clipboard access, Rich for terminal formatting, and pytest for tests.

Optional PDF OCR uses the system commands `pdftoppm` (Poppler) and `tesseract` with local language data. Resolve native PDF tools from absolute PATH entries outside the current working directory. Each render and recognition process has a timeout. The page image is passed to Tesseract in memory.
