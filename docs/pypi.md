# any2llm

**Ask AI about your documents, then check its PDF citations on the original pages.**

any2llm turns a folder of PDF, Word, PowerPoint, Excel, EPUB, HTML, text, and code files into numbered Markdown attachments and a ready-to-paste chat prompt. It keeps physical PDF page numbers and flags pages with missing or partial text so you can check the original.

- Run `uvx any2llm ./documents` to try it without a permanent install.
- Pipe one pack into other tools with `any2llm ./documents --stdout | llm "List every deadline"`.
- Connect Claude, Cursor, and other MCP apps with `any2llm mcp ~/Documents`, a local read-only MCP server.
- Set a token budget per batch and use the generated prompt to guide the chat through multiple attachments.
- Extract text on your computer. Optional OCR for PDF pages without usable text uses Poppler and Tesseract.
- Choose from 11 languages for terminal output and chat prompts.

Requires Python 3.11 or newer. Find examples, usage instructions, and extraction limits in the [GitHub repository](https://github.com/ahmetemreapo/any2llm).

<!-- mcp-name: io.github.ahmetemreapo/any2llm -->
