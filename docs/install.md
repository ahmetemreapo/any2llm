# Install any2llm

Use Python 3.11 or newer. The [quick install](../README.md#install) uses pipx to install from PyPI. If an existing pipx installation works but your shell cannot find `any2llm`, run `pipx ensurepath` and open a new terminal.

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
