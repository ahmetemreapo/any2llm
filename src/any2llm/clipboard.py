"""Copy the prompt without exposing platform clipboard diagnostics."""

import subprocess
import sys


def copy_prompt(prompt: str) -> bool:
    # Some native backends print errors directly to stderr or wait for a display.
    try:
        result = subprocess.run(
            [sys.executable, "-m", "any2llm.clipboard"], input=prompt.encode("utf-8"),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def _copy_and_verify(prompt: str) -> bool:
    import pyperclip

    pyperclip.copy(prompt)
    # Several pyperclip backends discard the native tool's exit status.
    return pyperclip.paste() == prompt


if __name__ == "__main__":
    sys.exit(0 if _copy_and_verify(sys.stdin.buffer.read().decode("utf-8")) else 1)
