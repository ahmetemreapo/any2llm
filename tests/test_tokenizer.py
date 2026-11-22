from unittest.mock import Mock

import tiktoken

from any2llm.tokenizer import count_tokens, get_encoding


def test_uses_cl100k_and_encodes_special_markers_as_text(monkeypatch):
    encoding = Mock()
    encoding.encode_ordinary.return_value = [1, 2]
    load = Mock(return_value=encoding)
    monkeypatch.setattr(tiktoken, "get_encoding", load)
    get_encoding.cache_clear()
    try:
        assert count_tokens("<|endoftext|>") == 2
        assert get_encoding() is encoding
        load.assert_called_once_with("cl100k_base")
        encoding.encode_ordinary.assert_called_once_with("<|endoftext|>")
    finally:
        get_encoding.cache_clear()


def test_offline_estimate(monkeypatch):
    load = Mock(side_effect=OSError("offline"))
    monkeypatch.setattr(tiktoken, "get_encoding", load)
    get_encoding.cache_clear()
    try:
        assert [count_tokens(s) for s in ("", "a", "1234", "12345")] == [0, 1, 1, 2]
        load.assert_called_once_with("cl100k_base")
    finally:
        get_encoding.cache_clear()
