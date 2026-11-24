# any2llm

**Ask AI about your documents, then check its PDF citations on the original pages.**

any2llm turns a folder of PDF, Word, PowerPoint, Excel, text, and code files into Markdown attachments for an AI chat, with numbered batches and a ready-to-paste prompt.

[Türkçe](README.tr.md)

![Three delivery documents become two Markdown attachments. A local chat cites the original PDF page, which the demo shows for verification.](examples/delivery-dates-chat-demo.gif)

[Terminal-only recording](examples/delivery-dates-demo.gif)

## Install

Requires Python 3.11 or newer and [pipx](https://pipx.pypa.io/stable/how-to/install-pipx.html).

```sh
pipx install any2llm
```

[Installation help for Windows, macOS, and Linux](docs/install.md)

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB)](pyproject.toml)
[![MIT license](https://img.shields.io/badge/License-MIT-2E8555)](LICENSE)
[![Platform compatibility](https://github.com/ahmetemreapo/any2llm/actions/workflows/platforms.yml/badge.svg)](https://github.com/ahmetemreapo/any2llm/actions/workflows/platforms.yml)

## Who is it for?

| If you work with… | Try this |
| --- | --- |
| Office and finance records | Reconcile dates in a supplier offer and a spreadsheet. See the [delivery dates example](#work-example-delivery-dates). |
| Legal documents | Compare clauses across contract drafts and check quoted wording in the original PDF. |
| Research material | Summarize methods across papers and check a definition against its source page. |
| Software and documentation | Ask how a configuration setting is used across source files and technical notes. |
| Course material | Turn lecture slides, readings, and a worksheet into a practice question. See the [midterm example](#student-example-midterm-practice). |

## Try it without installing

If GitHub opens the attachment as text, use the download arrow (↓) at the top of the file view to save the original `.md` file.

### Work example: delivery dates

The pack contains a supplier offer (PDF), a delivery schedule (Excel), and a meeting note (text). [Browse the source files](examples/delivery-dates/).

1. Open the [delivery dates attachment](examples/delivery-dates-pack/batch_01_of_1.md?plain=1), download it with **↓**, and attach it in your AI chat.
2. Paste this question and send it with the attachment.

   > List the pilot and main shipment dates. Cite the Excel sheet and the original PDF page for each date, and flag any page whose text could not be read.

3. Check the dates on pages 1 and 3 of the [original supplier offer](https://raw.githubusercontent.com/ahmetemreapo/any2llm/main/examples/delivery-dates/supplier-offer.pdf#page=1).

<details>
<summary>Expected answer</summary>

| Shipment | Delivery date | Sources |
| --- | --- | --- |
| Pilot | March 12, 2027 | `delivery-schedule.xlsx`, **Schedule** sheet, and `supplier-offer.pdf`, **page 1** |
| Main | March 26, 2027 | `delivery-schedule.xlsx`, **Schedule** sheet, and `supplier-offer.pdf`, **page 3** |

The batch flags page 2 because its text is in an image. Open the original page to read the freight note.

</details>

### Student example: midterm practice

Four research methods practice files (PDF, PowerPoint, Word, and Excel) fit in one attachment. The CLI also generates [the full chat prompt](examples/midterm/en/PROMPT.txt).

1. Open the [midterm attachment](examples/midterm/en/batch_01_of_1.md?plain=1), download it with **↓**, and attach it in your AI chat.
2. Paste this question and send it with the attachment.

   > Which research design fits the measurement plan? Cite the Excel sheet for what was measured in each class and the original PDF page for the design definition.

3. Check the definition on [page 2 of the original PDF](https://raw.githubusercontent.com/ahmetemreapo/any2llm/main/src/any2llm/demo_assets/en/research-designs.pdf#page=2). If your viewer opens on page 1, scroll to page 2.

<details>
<summary>Expected answer</summary>

The plan uses a **quasi-experimental pretest–posttest design with a nonequivalent comparison group**. Two existing classes take the same 10-item terms test before and after the activity, with no random assignment. Class A recalls the terms from memory and Class B rereads them, each for eight minutes. See the **Plan** sheet in `measurement-plan.xlsx` and **page 2** of `research-designs.pdf`.

</details>

If the example helps with work you do, consider giving the repository a star.

## How is this different?

any2llm keeps the PDF page numbers inside the chat attachments and generates a prompt that asks for source citations and guides multi-batch chats. A dash marks a feature left unspecified here.

| Tool | PDF page numbers | Output splitting | OCR | Local processing | Example inputs | Chat instructions |
| --- | --- | --- | --- | --- | --- | --- |
| **any2llm** | Page tags in Markdown | Token-budgeted Markdown batches | Optional Tesseract for PDF pages without usable text | Local extraction and OCR | PDF, DOCX, PPTX, XLSX, text, code | Generated citation prompt and continuation messages |
| MarkItDown | — | — | Vision model via OCR plugin | Local file conversion is available | PDF, Word, PowerPoint, Excel, CSV, HTML | — |
| Docling | Page numbers in document provenance | JSONL chunks with a configurable token budget | Configurable OCR engines | Local execution is available | PDF, DOCX, PPTX, XLSX, HTML, images | — |
| Pandoc | — | Section-based chunks in HTML output | — | Local CLI | Markdown, HTML, LaTeX, DOCX, EPUB | — |
| Repomix | — | Numbered output files by size | — | Local CLI | Repository files such as code and Markdown | Includes a user-written instructions file |

Official sources

- MarkItDown ([project README](https://github.com/microsoft/markitdown/blob/main/README.md), [OCR plugin](https://github.com/microsoft/markitdown/tree/main/packages/markitdown-ocr))
- Docling ([formats and chunks](https://docling-project.github.io/docling/usage/supported_formats/), [page provenance](https://docling-project.github.io/docling/reference/docling_document/#docling_core.types.doc.ProvenanceItem), [OCR engines](https://docling-project.github.io/docling/getting_started/installation/#ocr-engines), [local execution](https://docling-project.github.io/docling/))
- Pandoc ([input formats](https://pandoc.org/MANUAL.html#option--from), [chunked HTML](https://pandoc.org/MANUAL.html#chunked-html))
- Repomix ([quick start](https://repomix.com/guide/), [output splitting](https://repomix.com/guide/configuration), [custom instructions](https://repomix.com/guide/custom-instructions))

## Pack your own folder

Replace the example path with your folder. Keep the quotes around paths with spaces.

```sh
any2llm "./documents" --lang en
```

1. Choose your preferences on the first run, then select the files to include.
2. Attach the numbered Markdown files from the `_llm_pack` output folder. Paste the generated `PROMPT.txt` text into the chat.
3. For multiple batches, follow the terminal’s upload order and send the continuation word in the same chat when another batch remains. Model behavior can vary. If the model does not move on, resend your last message and name the next batch, attaching its file if you haven’t already. Verify important PDF citations in the original.

Use `-r` to include subfolders, `--max-tokens` to set a per-batch token budget, `--task` to supply your question, and `--details` to see every reported skip. Token counts can differ from your chat service’s.

The terminal and generated prompts support 11 languages via `--lang` (`en`, `zh`, `hi`, `es`, `fr`, `ar`, `bn`, `pt`, `ru`, `ur`, `tr`). See the [CLI reference](docs/SPEC.md#command-line-options).

Run the bundled midterm demo with `any2llm demo --lang en --no-open`. It prints the path to a fresh output folder.

## Limits, privacy, and OCR

- **Extraction.** Batches keep PDF text and physical page numbers, Word and PowerPoint text and tables, visible Excel sheets with values and formulas, and readable text and code. Charts, images, and layout can be lost. The terminal flags PDF pages with missing or partial text. Check the original wherever an answer depends on an important detail or a visual.
- **File limits.** Up to 32 MiB per source file, 500 pages per PDF, 128 MiB uncompressed per Office archive, and 120 seconds per file for extraction. Unreadable, encrypted, and unsupported files are reported and skipped. Your chat’s attachment and context limits still apply.
- **Privacy.** Extraction and OCR run locally. tiktoken may download its vocabulary on first use. Review the output before uploading it to a chat. The CLI skips common credential filenames and warns about some credential patterns in extracted text, which stays in the output. See the [security policy](SECURITY.md).
- **OCR.** Install Poppler (`pdftoppm`) and Tesseract with the language data you need. Add their installation directories to `PATH` as absolute paths. Use `--ocr` for English or `--ocr-lang` to choose installed languages independently of the chat prompt language. OCR tries PDF pages without usable text and marks recognized pages in the batch. Check important names and numbers against the scan. [Tesseract installation guide](https://tesseract-ocr.github.io/tessdoc/Installation.html)
