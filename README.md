# any2llm

[![Platform compatibility](https://github.com/ahmetemreapo/any2llm/actions/workflows/platforms.yml/badge.svg)](https://github.com/ahmetemreapo/any2llm/actions/workflows/platforms.yml)

Prepare documents for an AI chat from a folder on your computer. Choose the documents, then attach the files that any2llm prepares and paste the accompanying instructions. You choose what to upload.

## Quick install

Use Python 3.11 or newer and pipx. [Install pipx](https://pipx.pypa.io/stable/how-to/install-pipx.html)

```sh
git clone https://github.com/ahmetemreapo/any2llm.git
cd any2llm
pipx install .
```

If your terminal can't find `any2llm`, run `pipx ensurepath` and open a new terminal. For a manual install, use the [venv instructions](#install-from-this-source-folder).

Replace `<folder>` with the path to your documents. Quote paths that contain spaces.

```sh
any2llm <folder>
```

## Try it with three sample files

![Terminal recording showing selection of three delivery documents, followed by the Markdown attachment and prompt instructions](examples/delivery-dates-demo.gif)

The [delivery dates example](examples/delivery-dates/) contains a supplier offer (PDF), a delivery schedule (Excel), and a meeting note (text). After installation, run this command from the repository root.

```sh
any2llm examples/delivery-dates --no-open --lang en --task "List delivery dates in a table and cite the source for each date."
```

If first-run setup opens, press Enter at each question to accept the defaults. At file selection, press Enter to keep all three files.

In your AI chat, attach `examples/delivery-dates/_llm_pack/batch_01_of_1.md`. Paste the instructions from the clipboard or copy them from `PROMPT.txt` in the same folder, then send the message.

### Example AI reply

| Shipment | Delivery date | Sources |
| --- | --- | --- |
| Pilot | March 12, 2027 | `delivery-schedule.xlsx` (Schedule), `supplier-offer.pdf` (p. 1) |
| Main | March 26, 2027 | `delivery-schedule.xlsx` (Schedule), `supplier-offer.pdf` (p. 3) |

Page 2 of `supplier-offer.pdf` has no extractable text. Check the original page for any additional delivery details.

<details>
<summary>See what goes into the Markdown attachment</summary>

Page 2 of the offer contains an image with text.

The terminal reports the page that needs checking.

```text
  supplier-offer.pdf — PDF pages with no extractable text: 2
```

The batch contains the Excel table and all three physical PDF page numbers. The excerpt omits the manifest and the meeting note.

```text
<file id="1" name="delivery-schedule.xlsx" type="XLSX">## Schedule

| Shipment | Delivery date |
| --- | --- |
| Pilot | 2027-03-12 |
| Main | 2027-03-26 |</file>

<file id="3" name="supplier-offer.pdf" type="PDF">
<page number="1">Pilot shipment is due on 2027-03-12.</page>
<page number="2" extraction="no-extractable-text"></page>
<page number="3">Main shipment is due on 2027-03-26.</page>
</file>
```

Code and HTML stay readable inside file and page blocks. For example, `a < b && c > d` appears exactly as written. A literal closing tag reserved by the pack format gets an extra backslash, so source text containing `</file>` appears as `<\/file>`.

</details>

## Install from this source folder

Use Python 3.11 or newer with pip and venv. Open a terminal in the source folder containing `pyproject.toml`. These commands install into a private environment without administrator access.

**Windows PowerShell**

```powershell
py -3 -m venv "$env:USERPROFILE\.any2llm-env"
& "$env:USERPROFILE\.any2llm-env\Scripts\python.exe" -m pip install .
$env:Path = "$env:USERPROFILE\.any2llm-env\Scripts;$env:Path"
any2llm --help
```

Repeat the `$env:Path` line in a new PowerShell window, or add that Scripts folder to your user PATH once. If you installed Python without the `py` launcher, use `python` in the first command. The setup works without running PowerShell activation scripts.

**macOS and Linux** (sh, bash or zsh)

```sh
python3 -m venv "$HOME/.any2llm-env"
"$HOME/.any2llm-env/bin/python" -m pip install .
. "$HOME/.any2llm-env/bin/activate"
any2llm --help
```

Use the activation line in each new terminal. In fish, use `source ~/.any2llm-env/bin/activate.fish`. If the command is missing from PATH, you can always run the environment’s Python with `-m any2llm` from your documents folder.

On Linux, some distributions package venv and pip separately. If creating the environment fails, install your distribution’s Python venv and pip packages. Availability of prebuilt dependencies depends on your Python version, processor and C library. On platforms where pip needs to compile them, install the compiler and development packages requested by the build (for example Rust for tiktoken, or libxml2 and libxslt headers for lxml).

## Prepare your first chat

1. Go to the folder containing your documents. On Windows, right-click inside the folder in File Explorer and choose **Open in Terminal** if available. On macOS or Linux you can open Terminal and enter `cd "/path/to/My Documents"`, using your own folder path.
2. Run `any2llm`. On first use, choose a language, choose how to group the documents, and decide whether to open the prepared files automatically. The language menu uses your system language when supported and English otherwise. The remaining questions use your choice. Press Enter to keep the highlighted option.
3. All candidates that pass the scan filters start selected. Press Enter to keep them all, or use the arrow keys and Space to remove individual files. With `any2llm --plain`, use numbered choices. Run `any2llm -r` to look in subfolders too. After selection, any2llm reads the selected files and reports files it cannot use.
4. The terminal shows the number and combined size of the `batch_*.md` attachments and how tokens were counted. Attach all the named files to one message if your chat allows. If you hit its attachment limit, start with the first file. Paste the instructions into the message and send. The terminal confirms whether the instructions were copied to your clipboard. You can also copy them from `PROMPT.txt` in the output folder.
5. After each reply, send the continuation word shown in the terminal to move to the next numbered file. Attach that file to the continuation message if you haven't uploaded it yet.

Desktop sessions use Explorer on Windows, Finder on macOS, or `xdg-open` on Linux. For SSH sessions, containers and servers, use `--no-open`. The instructions are always available in `PROMPT.txt`.

`--max-tokens` sets a token limit for each prepared file. any2llm counts tokens with `cl100k_base` when available and estimates one token per four characters otherwise. The terminal indicates when the estimate was used. Your chat service may count tokens differently.

The terminal shows the full folder path, even when the folder cannot open automatically. The default folder is `_llm_pack` inside your documents folder. If a file at the destination cannot safely be replaced, use another folder, such as `any2llm -o chat_files`. This also applies to output made by versions that did not record which files they wrote.

## Languages

The terminal interface and chat instructions support English (`en`), Mandarin Chinese in simplified script (`zh`), Hindi (`hi`), Spanish (`es`), French (`fr`), Arabic (`ar`), Bengali (`bn`), Portuguese (`pt`), Russian (`ru`), Urdu (`ur`), and Turkish (`tr`). Run `any2llm setup` to change the saved language or use `--lang CODE` for one run. For Arabic and Urdu menus, use a terminal that supports right-to-left text. Numbered menus are available with `--plain`.

## Privacy and security

any2llm processes documents locally, including OCR. You choose which files to upload and upload them yourself. When the token vocabulary is missing from its cache, tiktoken can download it for token counting.

The CLI checks extracted text locally for common API key, access token, and private key formats. It shows the filename and finding type and keeps the extracted text in the output. Review every `batch_*.md` file before uploading, even if the CLI shows no warning. See the [security policy](SECURITY.md) for reporting guidance.

## What gets included

any2llm extracts text from PDFs, paragraphs and tables from Word documents, text and tables from slides, and cell values or formulas from Excel sheets. Selected PDFs with some extractable text retain their physical page numbers. Pages from which no text could be extracted are reported in the terminal and marked in the pack. A PDF without any usable text is skipped. Images, audio and video stay out of the prepared files. HTML remains source text, including any CSS and JavaScript. Grouping reduces the number of attachments. Your chat service still sets its own size and attachment limits.

The scan skips common environment and build directories and flags potentially sensitive filenames such as `credentials.json`, `id_rsa`, and `server.pem`. Use `--include-sensitive` to allow those filenames through the sensitive-file filter. The scan also applies simple rules from the root `.gitignore`. Add your own exclusions with `--exclude '*.log' --exclude 'private/'`. Quote globs to prevent your shell from expanding them.

For reported skips, the terminal explains each reason and suggests what to try. Run `any2llm --details` for the full list of reported files, or `any2llm setup` to change your preferences. Run `any2llm --help` for advanced options. Without an interactive terminal, `any2llm -y` selects all candidates that pass the scan filters and uses saved settings or temporary defaults.

Extraction accepts up to 32 MiB per source file, 500 pages per PDF, and 128 MiB of total uncompressed entries per Word, PowerPoint, or Excel archive. The CLI allows up to 120 seconds per selected file, including OCR. It skips files that exceed a limit.

### OCR for scanned PDFs

Install Poppler (`pdftoppm`) and Tesseract with the language data for your documents. Put their installation directories on `PATH` as absolute paths. any2llm skips the current working directory when looking for these tools and for `pdftotext`, which can repair damaged PDF text with or without OCR. Use `tesseract --list-langs` to see which languages are installed. [Tesseract installation guide](https://tesseract-ocr.github.io/tessdoc/Installation.html)

```sh
any2llm ./lectures --ocr
any2llm ./lectures --ocr-lang tur+eng
```

`--ocr` uses English (`eng`). `--ocr-lang` enables OCR with the specified installed languages, independently of the terminal language. OCR runs locally and only on PDF pages where text extraction found no usable text. The batch keeps the original page number and marks recognized text with `extraction="ocr"`. The terminal lists any pages that still have no extractable text. Check names and numbers from OCR against the original page when they matter.
