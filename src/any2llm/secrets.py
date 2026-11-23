"""Recognize a few common credential formats in extracted text."""

import re

_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:(?:RSA|EC|DSA|OPENSSH|ENCRYPTED|PGP) )?PRIVATE KEY(?: BLOCK)?-----"),
    "api_key": re.compile(
        r"(?<![\w-])(?:"
        r"sk-(?:proj-|svcacct-|ant-api\d+-)?[A-Za-z0-9_-]{20,}"
        r"|gh[pousr]_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{30,}"
        r"|(?:AKIA|ASIA)[A-Z0-9]{16}|AIza[A-Za-z0-9_-]{35}|xox[baprs]-[A-Za-z0-9-]{10,}"
        r")(?![\w-])"
    ),
}


def finding_types(text: str) -> list[str]:
    """Return type labels without returning any matched text."""
    return [kind for kind, pattern in _PATTERNS.items() if pattern.search(text)]
