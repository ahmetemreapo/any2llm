# AGENTS.md — any2llm

## Project Rules
- Language: Python 3.10+ using `src/any2llm/` layout and `pyproject.toml`.
- Keep code, comments, and documentation in English.
- Support 11 languages for terminal output and generated LLM prompts through `--lang` (`en`, `zh`, `hi`, `es`, `fr`, `ar`, `bn`, `pt`, `ru`, `ur`, `tr`).
- Never crash on corrupted, unreadable, encrypted, or binary files. Skip them safely and report them clearly.
- Keep modules small, clean, and single-responsibility.
- Always run `pytest` after making changes and verify everything passes before finishing a task.
- Do not add unnecessary heavy dependencies. Stick to the libraries listed in `SPEC.md`.
