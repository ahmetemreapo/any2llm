# Install any2llm

Use Python 3.11 or newer. The [quick install](../README.md) uses pipx to install from PyPI. If an existing pipx installation works but your shell cannot find `any2llm`, run `pipx ensurepath` and open a new terminal.

## Run without installing

With [uv](https://docs.astral.sh/uv/getting-started/installation/), `uvx any2llm` downloads any2llm into a cached environment and runs it. MCP app configurations can use the same command.

```sh
uvx any2llm ./documents
uvx any2llm mcp ~/Documents
```

## Set up a local model for `any2llm ask`

`any2llm ask` needs a model server on your computer. `any2llm check` and packing don't.

1. Install [Ollama](https://ollama.com/download) (Windows, macOS, or Linux) and start it.
2. Download a small instruction model: `ollama pull qwen3:4b-instruct`. It needs about 2.5 GB of disk and runs on a 6 GB GPU or, more slowly, on the CPU. Larger models such as `qwen3:8b` usually follow the quote format more reliably if you have the memory.
3. Run `any2llm ask demo` to check the setup.

LM Studio and llama.cpp work too. Start their local server, and any2llm finds it on port 1234 or 8080. For another address, pass `--api http://host:port/v1`.

## Install from GitHub

With Git and pipx installed, use this command to install the current `main` branch from source.

```sh
pipx install git+https://github.com/ahmetemreapo/any2llm.git@main
```

## Install from a local checkout

Open a terminal in the source folder containing `pyproject.toml`. Use a checkout without an existing virtual environment at `.venv`, or pick a different directory name in the commands below.

### Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\any2llm.exe --help
```

If the Python launcher is unavailable, use `python` in place of `py -3`. Call the executable by its full path when you run it from another folder. You can also add the virtual environment’s `Scripts` folder to your user PATH.

### macOS and Linux

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .
. .venv/bin/activate
any2llm --help
```

In fish, use `source .venv/bin/activate.fish` for the activation step. Activate the environment in each new terminal where you want to use the short command name. You can also call the executable in `.venv/bin` by its full path.

Some Linux distributions package `venv` and pip separately. If environment creation fails, install your distribution’s Python venv and pip packages. If pip needs to compile a dependency, use the compiler and development libraries named in its build error.
