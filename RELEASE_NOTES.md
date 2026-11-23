# any2llm v0.1.0

Turn a folder of PDFs, Word documents, slides, spreadsheets, text, and code into Markdown attachments for an AI chat. Select the files you want to share, attach the generated batches, and paste the instructions from `PROMPT.txt` or your clipboard.

- Run the interactive selection menu or use `-y` to select files that pass the scan filters. The terminal and generated prompts support 11 languages.
- Keep physical PDF page numbers and use optional local OCR with Poppler and Tesseract for scanned pages. The terminal reports pages with missing or partial text.
- Extract only selected files, with limits on source size, PDF page count, Office archive expansion, and extraction time. Excel parsing uses defusedxml.
- Get local warnings for common credential formats in extracted text. Warnings identify the filename and finding type. The generated text remains available for review before upload.
- Use an isolated clipboard helper with a saved prompt as a fallback. PDF tools are resolved from absolute PATH entries outside the working directory.

Install with Python 3.11 or newer. The [README](https://github.com/ahmetemreapo/any2llm#quick-install) includes quick installation commands and a three-file example.
