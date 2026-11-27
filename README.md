# any2llm

any2llm turns a folder of PDFs, Office files, and code into Markdown that an AI chat can cite page by page.

<img src="examples/delivery-dates-chat-demo.gif" width="800" alt="Three delivery documents become two Markdown attachments. A local chat cites the original PDF page, which the demo shows for verification.">

```sh
pipx install any2llm
any2llm demo
```

[![PyPI](https://img.shields.io/pypi/v/any2llm?color=3776AB&label=PyPI)](https://pypi.org/project/any2llm/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB)](pyproject.toml)
[![MCP Registry](https://img.shields.io/badge/MCP_Registry-listed-7c3aed)](https://registry.modelcontextprotocol.io/v0/servers?search=io.github.ahmetemreapo/any2llm)
[![Platform compatibility](https://github.com/ahmetemreapo/any2llm/actions/workflows/platforms.yml/badge.svg)](https://github.com/ahmetemreapo/any2llm/actions/workflows/platforms.yml)
[![MIT license](https://img.shields.io/badge/License-MIT-2E8555)](LICENSE)

[Quick start](#quick-start) · [Examples](examples/README.md) · [Claude and Cursor (MCP)](#use-it-in-claude-cursor-and-other-mcp-apps) · [Docs](docs/SPEC.md) · [Türkçe](README.tr.md)

## Why any2llm?

AI chats read documents well, but it is hard to check where an answer came from. Most converters drop page numbers, so the chat can't cite them.

- Each PDF fragment carries its source page number, so you can check the answer against the original page.
- One run handles a mixed folder: PDF, Word, PowerPoint, Excel (values and formulas), EPUB, HTML, CSV, Markdown, and source code.
- Large folders are split into batches that fit your chat's context window, and the prompt tells the chat how to read them in order.
- You can attach the output in any chat, pipe it into a CLI, or connect Claude and Cursor through MCP.
- Everything runs on your computer. Credential files are skipped, likely secrets are flagged, and broken, encrypted, or binary files are reported instead of crashing the run.
- The terminal and the generated prompts come in 11 languages.

People use it for supplier offers and spreadsheets, contract drafts, research papers, course material, books, and codebases. Unlike MarkItDown, Docling, Pandoc, or Repomix, it keeps PDF page numbers inside the chat attachment and writes a prompt that asks for citations. See the [comparison](docs/comparison.md) for details.

## Quick start

1. Run `any2llm ./my-documents`. With [uv](https://docs.astral.sh/uv/getting-started/installation/) you can skip the install and run `uvx any2llm ./my-documents`. See [installation help for Windows, macOS, and Linux](docs/install.md).
2. Pick your files. All readable files start checked. Press Enter to continue.
3. Attach the numbered `.md` files from `_llm_pack/` and paste the prompt that's already on your clipboard. Then check the cited pages.

| Where | You run | You get |
| --- | --- | --- |
| Any AI chat | `any2llm ./docs` | Numbered Markdown attachments and a citation prompt on your clipboard |
| Claude, Cursor, and MCP apps | `claude mcp add any2llm -- uvx any2llm mcp ~/Documents` | The AI reads your folder itself, on request |
| Scripts and pipes | `any2llm ./docs --stdout \| llm "List every deadline"` | One Markdown stream on standard output |

## Try it without installing

Ready-made output files are in [examples/](examples/README.md): a work example with delivery dates and a student example with midterm material. Attach one to your AI chat, ask the question listed there, and compare the answer with the original PDF page.

## Use it with any AI chat

```sh
any2llm "./documents"          # keep the quotes if the path has spaces
any2llm ./documents -r         # include subfolders
any2llm ./documents --task "Find every payment deadline and who owes it"
```

1. On the first run, choose your language, a detail level, and whether to open the output folder.
2. Select files, then attach the numbered Markdown files from `_llm_pack/` and paste the prompt (also saved as `PROMPT.txt`).
3. If there are several batches, follow the upload order the terminal prints and send the continuation word between them in the same chat.

> [!NOTE]
> Models don't always follow multi-batch instructions. If one doesn't move on, resend your last message and name the next batch. **Check important citations against the original.**

## Use it in Claude, Cursor, and other MCP apps

`any2llm mcp` runs a local [Model Context Protocol](https://modelcontextprotocol.io) server. The AI gets two read-only tools: `list_documents` shows what a folder contains, and `read_documents` returns Markdown with PDF page tags, in batches when the content is large. The server never reads outside the folder you give it.

Claude Code:

```sh
claude mcp add any2llm -- uvx any2llm mcp ~/Documents
```

<details>
<summary>Claude Desktop, Cursor, Windsurf, and other apps with an <code>mcpServers</code> file</summary>

```json
{
  "mcpServers": {
    "any2llm": {
      "command": "uvx",
      "args": ["any2llm", "mcp", "/Users/you/Documents"]
    }
  }
}
```

If the app can't find `uvx`, use its full path (`which uvx` on macOS and Linux, `where uvx` on Windows). With a pipx install, use `"command": "any2llm"` and `"args": ["mcp", "/Users/you/Documents"]`. Add `--ocr` or `--ocr-lang tur` after the folder to read scanned pages.

</details>

Then ask: *"Read the contracts folder and list each termination clause with its PDF page."*

## Use it in scripts and pipes

`--stdout` prints one unsplit pack to standard output and sends progress and warnings to standard error. It selects every readable file and writes nothing to disk.

```sh
any2llm ./contracts --stdout | claude -p "Which contract renews automatically? Cite the PDF page."
any2llm ./papers -r --stdout | llm "Compare the sample sizes across these papers"
any2llm ./notes --stdout | pbcopy        # macOS (Linux: wl-copy or xclip, Windows: clip)
any2llm ./notes --stdout > notes-pack.md
```

<details>
<summary>All command-line options</summary>

| Option | Effect |
| --- | --- |
| `-r`, `--recursive` | Include subfolders |
| `-y`, `--yes` | Select every readable file without prompting |
| `--stdout` | Print one unsplit pack to standard output |
| `--task TEXT` | Put your question into the generated prompt |
| `--max-tokens INT` | Token budget per batch |
| `--lang CODE` | Terminal and prompt language: `en`, `zh`, `hi`, `es`, `fr`, `ar`, `bn`, `pt`, `ru`, `ur`, `tr` |
| `--ocr`, `--ocr-lang LANG` | OCR PDF pages without extractable text (for example `eng+tur`) |
| `--exclude GLOB` | Skip matching paths (repeatable). Root `.gitignore` rules also apply. |
| `-o DIR`, `--output DIR` | Output folder (default `_llm_pack`) |
| `--details` | List every skipped file |
| `--plain` | Numbered menus instead of checkboxes |
| `--no-open` | Don’t open the output folder |
| `--include-sensitive` | Include files that look like credentials |
| `setup`, `demo`, `mcp [DIR]` | Change settings, run the demo, or start the MCP server |

Full reference: [docs/SPEC.md](docs/SPEC.md#command-line-options)

</details>

## What gets extracted

| Format | What you get |
| --- | --- |
| PDF | Text per physical page in `<page>` tags. Pages without text are flagged, and optional OCR can read them. |
| Word (`.docx`) | Paragraphs and tables in document order |
| PowerPoint (`.pptx`) | Text and tables, slide by slide |
| Excel (`.xlsx`) | Visible sheets as tables, with cached values and formulas |
| EPUB | Chapters in reading order. DRM-protected books are skipped. |
| HTML | Saved pages as readable text with headings, lists, and tables. Templates stay as code. |
| Text and code | Markdown, CSV, JSON, YAML, and source code, with whitespace preserved |

Charts, images, and page layout aren’t extracted. Check the original when an answer depends on a visual.

## Privacy, limits, and OCR

- Privacy: extraction and OCR run locally. tiktoken may download its vocabulary on first use. Common credential files (`*.pem`, `id_rsa`, `credentials*`, …) are skipped, and likely secrets in extracted text are flagged but left in the output, so **review it before uploading**. See the [security policy](SECURITY.md).
- Limits: up to 32 MiB per file, 500 pages per PDF, 128 MiB uncompressed per Office or EPUB archive, and 120 seconds of extraction per file. Your chat’s attachment and context limits still apply.

<details>
<summary>Set up OCR for scanned PDFs</summary>

Install Poppler (`pdftoppm`) and [Tesseract](https://tesseract-ocr.github.io/tessdoc/Installation.html) with the language data you need, and add their folders to `PATH` as absolute paths. Use `--ocr` for English or `--ocr-lang` to choose installed languages, for example `--ocr-lang eng+tur`. OCR only runs on PDF pages without usable text, and recognized pages are marked in the batch. Check important names and numbers against the scan.

</details>

## Contributing

Bug reports, examples, translations, and code are all welcome. Start with the [contributing guide](CONTRIBUTING.md) or an issue labeled [good first issue](https://github.com/ahmetemreapo/any2llm/labels/good%20first%20issue).

If any2llm saved you time, a star helps other people find it.

## License

[MIT](LICENSE)
