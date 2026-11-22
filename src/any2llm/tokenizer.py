"""Count extracted content with cl100k_base or an offline estimate."""

from functools import lru_cache


@lru_cache(maxsize=1)
def get_encoding():
    """Load the vocabulary once, including when the cache or network is unavailable."""
    try:
        import tiktoken

        return tiktoken.get_encoding("cl100k_base")
    except (ImportError, OSError, ValueError):
        return None


def count_tokens(text: str) -> int:
    encoding = get_encoding()
    if encoding is None:
        return (len(text) + 3) // 4
    return len(encoding.encode_ordinary(text))
