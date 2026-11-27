# Contributing to any2llm

Thanks for helping. Bug reports, examples, translations, and code are all welcome. Issues labeled [good first issue](https://github.com/ahmetemreapo/any2llm/labels/good%20first%20issue) are a good place to start.

## Set up

```sh
git clone https://github.com/ahmetemreapo/any2llm.git
cd any2llm
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]" ruff
```

On Windows, use `.venv\Scripts\python.exe` instead of `.venv/bin/python`.

## Before you open a pull request

```sh
.venv/bin/ruff check
.venv/bin/python -m pytest -q
```

Both must pass. CI also runs the tests on Windows, macOS, Linux, and Alpine.

## Guidelines

- **Never crash on bad input.** Corrupted, encrypted, unreadable, and binary files must be skipped with a reason the user can act on. Add a test with a damaged sample when you add a format.
- **Keep dependencies light.** The allowed libraries are listed in the [specification](docs/SPEC.md#dependencies). Prefer the standard library, and open an issue before proposing a new dependency.
- **Localize user-facing text.** Terminal messages and prompts live in `src/any2llm/locales/*.json` and must exist in all 11 languages. If you can't translate a string, write it in English in every file and say so in the pull request so a native speaker can help.
- **Keep modules small** and focused on one job.
- **Update the docs.** Behavior changes belong in [docs/SPEC.md](docs/SPEC.md), and user-visible changes in [CHANGELOG.md](CHANGELOG.md).
- **Commit messages** follow [Conventional Commits](https://www.conventionalcommits.org/), for example `feat: read EPUB files` or `fix: keep page numbers for empty PDF pages`.

## Reporting security issues

Please don't open a public issue. Follow the [security policy](SECURITY.md).
