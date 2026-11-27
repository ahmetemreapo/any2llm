# any2llm

**Ask your documents. Get answers with page numbers, and proof that every quote is really on that page.**

any2llm reads a folder of PDF, Word, PowerPoint, Excel, EPUB, HTML, text, and code files on your computer, answers questions with a local model (Ollama, LM Studio, or llama.cpp), and checks every quote against the original page. It can also check the citations in an answer from ChatGPT, Claude, Gemini, or any other chat.

```sh
pipx install any2llm
ollama pull qwen3:4b-instruct
any2llm ask ./contracts "Which contracts renew automatically, and with how much notice?"
any2llm check ./contracts answer.md      # or copy any chat's answer and run: any2llm check ./contracts
```

- `any2llm ask` sends the model the full text with physical PDF page numbers, sets the context size for each request, and reads large folders in parts before it combines the quotes.
- `any2llm check` reports each quote as found where cited, found on another page or in another file, or not found. A changed number never passes.
- A Claude Code plugin (`/plugin install any2llm --marketplace ahmetemreapo/any2llm`) lets Claude check its own citations before it answers.
- `any2llm mcp ~/Documents` is a local, read-only MCP server with `list_documents`, `read_documents`, and `check_citations` tools.
- `any2llm ./documents` writes numbered Markdown attachments and a citation prompt for any chat, and `--stdout` pipes one pack into other tools.
- Extraction, optional OCR for scanned PDF pages (Poppler and Tesseract), local models, and the check all run on your computer.
- The terminal and the prompts come in 11 languages.

Requires Python 3.11 or newer. Find examples, usage instructions, and extraction limits in the [GitHub repository](https://github.com/ahmetemreapo/any2llm).

<!-- mcp-name: io.github.ahmetemreapo/any2llm -->
