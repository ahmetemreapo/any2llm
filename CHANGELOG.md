# Changelog

All notable changes to any2llm are listed here. The project follows [Semantic Versioning](https://semver.org/).

## 0.3.0 (unreleased)

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
