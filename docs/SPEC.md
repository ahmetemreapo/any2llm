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
| `check_citations` | `answer`, `folder` | The [citation check](#citation-check) report for the answer, against the files below `folder` |

Folders resolve relative to `DIR` and must stay inside it after resolving symbolic links. Requested paths must be candidates of the scan, so hidden, ignored, and sensitive files are never read. `max_tokens` defaults to 25,000 and accepts 1,000 to 200,000. One call reads at most 100 files. A reply that is not the last batch says which batch to request next. Results are deterministic for unchanged files, so each call can request any batch without server-side session state. Invalid arguments return a tool result with `isError: true`.

## Asking a local model

`any2llm ask [DIR] [QUESTION…]` answers a question from the documents in `DIR`. The first word is the folder only when it names an existing directory or `demo`; otherwise the folder is the current directory and every word belongs to the question. `demo` copies the bundled midterm sources to a temporary folder and uses the demo question unless one is given. Without a question, an interactive terminal asks for questions in a loop until an empty line, and other input exits with status 2.

The model server comes from `--api`, then `ANY2LLM_API`, then the first of these that answers: Ollama at `http://localhost:11434` (`GET /api/tags`), LM Studio at `http://localhost:1234/v1`, and llama.cpp at `http://localhost:8080/v1` (`GET /models`). A URL whose path ends in `/v1` is treated as OpenAI-compatible. `ANY2LLM_API_KEY` is sent as a bearer token. A host other than `localhost`, `127.0.0.1`, `::1`, or `0.0.0.0` prints a warning that documents will be sent there. The model is `--model`, then `ANY2LLM_MODEL`, then the first model whose name does not mark it as an embedding, reranking, or speech model: the most recently modified one with Ollama, or the first one the server lists.

With Ollama, any2llm reads the model's maximum context from `POST /api/show` (`model_info["<architecture>.context_length"]`) and sends `options.num_ctx` with every request: `--context` or 8,192, capped at that maximum. Models with the `thinking` capability get `think: true` so that reasoning stays in its own field, plus 8,192 extra tokens of `num_predict`. For OpenAI-compatible servers, the context is `--context`, else the loaded context reported by LM Studio (`/api/v0/models`) or llama.cpp (`/props`), else 4,096. `<think>` blocks are removed from streamed text. The minimum context is 2,048.

Documents are packed in the format above with a token budget of 80% of the context left after the system prompt, the question, and the reply allowance (1,536 tokens for the answer and 768 for notes, each at most a quarter of the context), because model tokenizers often need more tokens than `cl100k_base`. If everything fits in one batch, one request streams the answer. Otherwise each batch is sent with a request to copy every sentence about anything the question asks, with its source, or reply `NONE`; the instruction closes the user message as well as forming the system prompt. Each quote in the notes is then grounded: a quote found on its cited page becomes the whole sentence that contains it, and any other quote becomes the most similar sentence in the cited file (similarity ratio at least 0.6, with that sentence's page). Sentences end at `.`, `!`, `?`, their full-width forms, blank lines, and short unpunctuated heading lines. Notes that do not fit one request are merged in groups, up to four rounds, and a final request with its own instructions answers from the notes. If every batch replies `NONE`, the terminal says that no document is relevant. The answer streams to standard output; status lines and the citation report go to standard error. The exit status is 1 when the check fails or finds nothing to confirm.

The system prompt, the note and merge instructions, the answer format with an example, and the question label are localized in the 11 languages. All of them ask for citations in the [checkable form](#citation-check).

## Citation check

`any2llm check [DIR] [ANSWER]` checks an answer against the documents below `DIR` (default: the current directory), scanned recursively with the usual filters. A single argument that is not a directory is the answer. The answer is read from the file `ANSWER`, from standard input when `ANSWER` is `-` or standard input is not a terminal, and otherwise from the clipboard. An answer file inside `DIR` is not treated as a source. In folders with more than 50 candidates, only the cited files are parsed.

A citation is a group in square brackets or parentheses that holds one or more references separated by semicolons (including the Arabic and full-width forms). A reference is a file name with an extension, optionally followed by a comma (also `،`, `，`, `、`) or colon and a locator. The first number of the locator is the first page, and a second number after a dash is the last page, so `p. 3`, `pp. 3–5`, `s. 3`, `стр. 4`, and `第3页` all work. Words before the file name, such as "see" or "from", are ignored. A group that does not start with a quote uses every quote (`"…"`, `“…”`, `«…»`, `„…“`, `「…」`, `『…』`) since the previous citation in the same paragraph. A group that starts with a quote, such as `("exact words" from file.xlsx)`, uses the quotes inside it. Each quote and reference pair is checked separately.

The cited name matches an extracted path exactly, then case-insensitively, then by a unique base name or path suffix. Quotes and page text are compared after NFKC normalization, case folding, joining words hyphenated across lines, removing quote marks, turning typographic dashes into hyphens and table pipes, asterisks, underscores, and number signs into spaces, and collapsing whitespace. An ellipsis splits a quote into parts that must appear in order. A quote of at least 16 characters also matches a passage with a similarity ratio of at least 0.86, as long as every number in the quote also appears in the passage.

| Status | Meaning |
| --- | --- |
| `verified` | The quote is on a cited page, or anywhere in a file without pages |
| `close` | A near match on a cited page or in the file |
| `other_page` | The quote is on another page of the cited file, which the report names |
| `other_file` | The quote is in another file, which the report names with its page |
| `not_found` | The quote is not in any extracted file |
| `page_missing` | The cited PDF has no such page |
| `unknown_source` | No extracted file has this name |
| `no_quote` | The citation has no quote, so only the file and page were checked |

The report passes when at least one citation is `verified` or `close` and none has a failing status (`other_page`, `other_file`, `not_found`, `page_missing`, or `unknown_source`). The exit status is 0 when it passes, 1 otherwise, and 2 when there is no answer to check. `--json` prints the counts and every citation with its status.

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
| `--no-clipboard` | Don't copy the master prompt to the clipboard |
| `--version` | Print the version |
| `-h`, `--help` | Show help |

`ask` also accepts `-r`, `--lang`, `--ocr`, `--ocr-lang`, `--exclude`, and `--include-sensitive`, plus `--model NAME`, `--api URL`, `--context TOKENS`, and `--no-check`. `check` accepts `--lang`, `--ocr`, `--ocr-lang`, `--exclude`, `--include-sensitive`, and `--json`.

Packing overrides apply only to the current run. The older `--ui-lang` spelling accepts the same language codes as `--lang`. The former `id` value is still accepted for compatibility and leaves the active language unchanged.

## Dependencies

Use Python 3.11 or newer. Use pypdf, python-docx, python-pptx, and openpyxl for document extraction. Require Pillow 13.0.0 or newer for python-pptx and defusedxml for Excel XML parsing. Use tiktoken with an offline fallback for token counts, questionary for interactive selection, pyperclip for clipboard access, Rich for terminal formatting, and pytest for tests.

`ask` talks to model servers with the standard library (`urllib`) and needs no extra package.

Optional PDF OCR uses the system commands `pdftoppm` (Poppler) and `tesseract` with local language data. Resolve native PDF tools from absolute PATH entries outside the current working directory. Each render and recognition process has a timeout. The page image is passed to Tesseract in memory.
