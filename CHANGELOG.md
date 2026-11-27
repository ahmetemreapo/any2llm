# Changelog

All notable changes to any2llm are listed here. The project follows [Semantic Versioning](https://semver.org/).

## 0.4.0

### Added

- `any2llm ask [DIR] "QUESTION"` answers with a local model and checks the answer's citations. It finds Ollama, LM Studio, or llama.cpp on this computer, or uses any OpenAI-compatible server given with `--api` (key in `ANY2LLM_API_KEY`). With Ollama it sets the context size for each request (`--context`, default 8192, capped at the model's maximum). Folders larger than the context are read in parts. Quotes collected from each part are grounded in the source text: a fragment becomes its whole sentence, and a misquote becomes the closest real sentence with its page. `examples/eval_lease.py` measures facts and citations on the example lease. Thinking models keep their reasoning out of the answer. Without a question in a terminal, it keeps asking in a loop. `any2llm ask demo` uses the bundled sample.
- `any2llm check [DIR] [ANSWER]` checks every `"quote" [file, p. N]` citation in an answer from any chat against the extracted pages. It reads the answer from a file, from standard input, or from the clipboard, and reports each quote as found, found with small differences, on another page, in another file, or not found. A changed number never passes. The exit code is 0 only when every citation is confirmed. `--json` prints a machine-readable report.
- The MCP server has a third tool, `check_citations`, and its instructions ask the model to check a draft before answering.
- A Claude Code plugin and an Agent Skills skill (`plugin/`), installable with `/plugin install any2llm --marketplace ahmetemreapo/any2llm`. Claude extracts the folder with any2llm, drafts an answer with quotes, and runs `any2llm check` before it replies.
- The chat prompt asks for quotes in the checkable `"exact words" [file, p. N]` form, and the terminal shows the `any2llm check` command after packing.
- `--no-clipboard` keeps the prompt off the clipboard, and `--version` prints the version.
- A 17-page example lease (`examples/lease/`) with an example chat answer that contains two planted mistakes.

### Changed

- The README leads with asking a local model and checking citations.

## 0.3.0

### Added

- `any2llm mcp [DIR]` runs a local, read-only MCP server with `list_documents` and `read_documents` tools. It supports the stateless 2026-07-28 protocol and the `initialize` handshake of earlier versions.
- `--stdout` prints one unsplit pack to standard output for piping into tools such as `claude -p` or `llm`. Progress and warnings go to standard error.
- EPUB books are read in spine order. DRM-protected books are skipped as encrypted.
- Saved HTML pages become readable text with headings, lists, tables, and code blocks. Templates and fragments stay as source code.
- `server.json` for the official MCP Registry.

### Changed

- The README leads with `uvx any2llm`, the three ways to use the tool, and MCP setup instructions.

## 0.2.0

- See the [GitHub release](https://github.com/ahmetemreapo/any2llm/releases/tag/v0.2.0).

## 0.1.0

- See the [GitHub release](https://github.com/ahmetemreapo/any2llm/releases/tag/v0.1.0).
