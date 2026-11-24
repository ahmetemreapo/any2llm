# Good first issue ideas

## Show how to check a PDF whose printed and physical page numbers differ

Add a short example to the [specification](SPEC.md) using a cover page or Roman-numbered front matter. Show how a reader finds physical page 3 when the page itself displays a different number. Keep the example independent of a specific PDF viewer.

## Document what happens to Excel formulas and hidden sheets

Use a small, synthetic worksheet to show a literal value, a formula with a cached value, and a hidden sheet. Add a before-and-after excerpt and explain that the workbook’s cached result can be stale. [Existing Excel extraction tests](../tests/test_parsers.py)

## Add a walkthrough for continuing a chat across batches

Use a checked-in sample folder and a small token budget to produce multiple attachments. Document which message gets the first attachment and prompt, what to send with the next attachment, and where to check the generated filenames. Verify the steps against the [session flow](SPEC.md#daily-use).

## Show how to confirm OCR prerequisites

Add a brief troubleshooting section to the [installation guide](install.md) for locating Poppler and listing Tesseract’s installed languages. Include the difference between the chat language and the OCR language, and verify the walkthrough with the sample supplier PDF.
