# How any2llm compares

Of the tools below, only any2llm keeps PDF page numbers inside the chat attachments, writes a prompt that asks for citations, and checks the quotes an answer cites against the original pages.

| Tool | PDF page numbers | Output splitting | OCR | Chat instructions | Citation check |
| --- | --- | --- | --- | --- | --- |
| any2llm | Page tags in Markdown | Token-budgeted batches | Optional local Tesseract | Citation prompt and continuation messages | Each quote against its cited page (`any2llm check`) |
| MarkItDown | — | — | Vision model via plugin | — | — |
| Docling | In document provenance | JSONL chunks by token budget | Configurable engines | — | — |
| Pandoc | — | Section-based HTML chunks | — | — | — |
| Repomix | — | Numbered files by size | — | User-written instructions file | — |

A dash marks a feature these sources don’t describe.

## Sources

- MarkItDown ([README](https://github.com/microsoft/markitdown/blob/main/README.md), [OCR plugin](https://github.com/microsoft/markitdown/tree/main/packages/markitdown-ocr))
- Docling ([formats and chunks](https://docling-project.github.io/docling/usage/supported_formats/), [page provenance](https://docling-project.github.io/docling/reference/docling_document/#docling_core.types.doc.ProvenanceItem), [OCR engines](https://docling-project.github.io/docling/getting_started/installation/#ocr-engines))
- Pandoc ([input formats](https://pandoc.org/MANUAL.html#option--from), [chunked HTML](https://pandoc.org/MANUAL.html#chunked-html))
- Repomix ([quick start](https://repomix.com/guide/), [output splitting](https://repomix.com/guide/configuration), [custom instructions](https://repomix.com/guide/custom-instructions))
