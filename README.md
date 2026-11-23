# any2llm

Prepare documents for an AI chat from a folder on your computer. Choose the documents, then attach the files that any2llm prepares and paste the accompanying instructions. You choose what to upload.

## Try it with three sample files

The [delivery dates example](examples/delivery-dates/) contains a supplier offer (PDF), a delivery schedule (Excel), and a meeting note (text). Page 2 of the offer contains an image with text. After installation, run this command from the repository root. If first-run setup opens, press Enter at each question to accept the defaults.

```sh
any2llm examples/delivery-dates -y --no-open --lang en --max-tokens 12000 --task "List delivery dates in a table and cite the source for each date."
```

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

In your AI chat, attach `examples/delivery-dates/_llm_pack/batch_01_of_1.md`, then paste the contents of `PROMPT.txt` from that same folder into the message box and send.

## Install from this source folder

Use Python 3.10 or newer with pip and venv. Open a terminal in the source folder containing `pyproject.toml`. These commands install into a private environment without administrator access.

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
3. All readable files that pass the scan filters start selected. Press Enter to keep them all, or use the arrow keys and Space to remove individual files. With `any2llm --plain`, use numbered choices. Run `any2llm -r` to look in subfolders too.
4. At the end, follow the terminal instructions. Attach the named `batch_*.md` files to one message. The terminal confirms whether it automatically copied the instructions to your clipboard. Paste those instructions into the message box and send. You can also copy them from `PROMPT.txt` in the output folder.
5. When you receive the first reply from your AI chat, type the continuation word shown in the terminal to move to the next numbered file.

Desktop sessions use Explorer on Windows, Finder on macOS, or `xdg-open` on Linux. For SSH sessions, containers and servers, use `--no-open`. The instructions are always available in `PROMPT.txt`.

The terminal shows the full folder path, even when the folder cannot open automatically. The default folder is `_llm_pack` inside your documents folder. If a file at the destination cannot safely be replaced, use another folder, such as `any2llm -o chat_files`. This also applies to output made by versions that did not record which files they wrote.

## Languages

The terminal interface and chat instructions support English (`en`), Mandarin Chinese in simplified script (`zh`), Hindi (`hi`), Spanish (`es`), French (`fr`), Arabic (`ar`), Bengali (`bn`), Portuguese (`pt`), Russian (`ru`), Urdu (`ur`), and Turkish (`tr`). Run `any2llm setup` to change the saved language or use `--lang CODE` for one run. For Arabic and Urdu menus, use a terminal that supports right-to-left text. Numbered menus are available with `--plain`.

## What gets included

any2llm extracts text from PDFs, paragraphs and tables from Word documents, text and tables from slides, and cell values or formulas from Excel sheets. Selected PDFs with some extractable text retain their physical page numbers. Pages from which no text could be extracted are reported in the terminal and marked in the pack. A PDF without any usable text is skipped. Images, audio and video stay out of the prepared files. HTML remains source text, including any CSS and JavaScript. Grouping reduces the number of attachments. Your chat service still sets its own size and attachment limits.

The scan skips common environment and build directories and flags potentially sensitive filenames such as `credentials.json`, `id_rsa`, and `server.pem`. Use `--include-sensitive` to allow those filenames through the sensitive-file filter. The scan also applies simple rules from the root `.gitignore`. Add your own exclusions with `--exclude '*.log' --exclude 'private/'`. Quote globs to prevent your shell from expanding them.

For reported skips, the terminal explains each reason and suggests what to try. Run `any2llm --details` for the full list of reported files, or `any2llm setup` to change your preferences. Run `any2llm --help` for advanced options. Without an interactive terminal, `any2llm -y` selects all readable files that pass the scan filters and uses saved settings or temporary defaults.
