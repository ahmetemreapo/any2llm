"""Talk to a local model server: Ollama's native API or any OpenAI-compatible endpoint.

Only the standard library is used. Nothing is sent anywhere unless a server answers at
the configured or auto-detected address, which defaults to this computer.
"""

import json
import os
import re
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

OLLAMA = "ollama"
OPENAI = "openai"
# Ollama, LM Studio, and llama.cpp's server, in that order.
LOCAL_SERVERS = ("http://localhost:11434", "http://localhost:1234/v1", "http://localhost:8080/v1")
DEFAULT_CONTEXT = 8192
MIN_CONTEXT = 2048
_PROBE_TIMEOUT = 2.5
_GENERATE_TIMEOUT = 900
_THINK = re.compile(r"<think>.*?</think>\s*", re.DOTALL)
_SKIP_MODELS = ("embed", "bge-", "rerank", "whisper", "clip")


class LLMError(Exception):
    """A problem reaching or using the model server. ``key`` names a localized message."""

    def __init__(self, key: str, detail: str = ""):
        super().__init__(detail or key)
        self.key = key
        self.detail = detail


@dataclass(frozen=True)
class Backend:
    kind: str
    base: str
    model: str
    context: int
    api_key: str = ""
    thinking: bool = False

    @property
    def label(self) -> str:
        host = urlsplit(self.base).netloc or self.base
        server = "Ollama" if self.kind == OLLAMA else host
        return f"{self.model} · {server} · {self.context:,} token context"


def _request(url: str, payload: dict | None = None, *, api_key: str = "", timeout: float = _PROBE_TIMEOUT):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "User-Agent": "any2llm"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(url, data=data, headers=headers, method="GET" if data is None else "POST")
    return urllib.request.urlopen(request, timeout=timeout)  # noqa: S310 - the URL is the user's model server.


def _get_json(url: str, *, api_key: str = "", timeout: float = _PROBE_TIMEOUT) -> dict | None:
    try:
        with _request(url, api_key=api_key, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError, urllib.error.URLError):
        return None


def _post_json(url: str, payload: dict, *, api_key: str = "") -> dict | None:
    try:
        with _request(url, payload, api_key=api_key) as response:
            return json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError, urllib.error.URLError):
        return None


def _root(base: str) -> str:
    parts = urlsplit(base.rstrip("/"))
    path = parts.path.removesuffix("/v1")
    return urlunsplit((parts.scheme, parts.netloc, path, "", "")).rstrip("/")


def _probe(base: str, api_key: str) -> tuple[str, str] | None:
    """Return (kind, base) for a server that answers at base, or None."""
    base = base.rstrip("/")
    if not urlsplit(base).path.endswith("/v1"):
        tags = _get_json(f"{base}/api/tags", api_key=api_key)
        if isinstance(tags, dict) and isinstance(tags.get("models"), list):
            return OLLAMA, base
        base = f"{base}/v1"
    models = _get_json(f"{base}/models", api_key=api_key)
    if isinstance(models, dict) and isinstance(models.get("data"), list):
        return OPENAI, base
    return None


def detect(api: str | None, api_key: str = "") -> tuple[str, str]:
    """Find the model server to use, trying common local ports when none is given."""
    candidates = (api,) if api else LOCAL_SERVERS
    for base in candidates:
        found = _probe(base, api_key)
        if found:
            return found
    raise LLMError("llm_unreachable" if api else "llm_not_found", api or "")


def list_models(kind: str, base: str, api_key: str = "") -> list[str]:
    if kind == OLLAMA:
        data = _get_json(f"{base}/api/tags", api_key=api_key) or {}
        entries = sorted(data.get("models") or [], key=lambda entry: entry.get("modified_at", ""), reverse=True)
        names = [entry.get("name") or entry.get("model") for entry in entries]
    else:
        data = _get_json(f"{base}/models", api_key=api_key) or {}
        names = [entry.get("id") for entry in data.get("data") or []]
    return [name for name in names if isinstance(name, str) and name]


def pick_model(models: list[str]) -> str | None:
    """Prefer the most recent chat model over embedding and speech models."""
    chat = [name for name in models if not any(marker in name.casefold() for marker in _SKIP_MODELS)]
    return (chat or [None])[0]


def _ollama_details(base: str, model: str, api_key: str) -> tuple[int | None, bool]:
    data = _post_json(f"{base}/api/show", {"model": model}, api_key=api_key)
    if not isinstance(data, dict):
        return None, False
    info = data.get("model_info") or {}
    lengths = [value for key, value in info.items() if key.endswith(".context_length") and isinstance(value, int)]
    capabilities = data.get("capabilities") or []
    return (max(lengths) if lengths else None), "thinking" in capabilities


def _openai_context(base: str, model: str, api_key: str) -> int | None:
    """Read the loaded context size from LM Studio or llama.cpp when they report it."""
    root = _root(base)
    studio = _get_json(f"{root}/api/v0/models", api_key=api_key)
    if isinstance(studio, dict):
        for entry in studio.get("data") or []:
            if entry.get("id") == model:
                value = entry.get("loaded_context_length") or entry.get("max_context_length")
                if isinstance(value, int) and value > 0:
                    return value
    props = _get_json(f"{root}/props", api_key=api_key)
    if isinstance(props, dict):
        value = (props.get("default_generation_settings") or {}).get("n_ctx")
        if isinstance(value, int) and value > 0:
            return value
    return None


def connect(api: str | None = None, model: str | None = None, context: int | None = None) -> Backend:
    """Resolve the server, model, and context size from arguments and environment."""
    api = api or os.environ.get("ANY2LLM_API") or None
    model = model or os.environ.get("ANY2LLM_MODEL") or None
    api_key = os.environ.get("ANY2LLM_API_KEY", "")
    kind, base = detect(api, api_key)
    models = list_models(kind, base, api_key)
    if model is None:
        model = pick_model(models)
        if model is None:
            raise LLMError("llm_no_models", base)
    elif models and model not in models and f"{model}:latest" not in models:
        raise LLMError("llm_model_missing", model)
    thinking = False
    if kind == OLLAMA:
        limit, thinking = _ollama_details(base, model, api_key)
        # Ollama allocates only a small context unless asked, and long prompts then lose their start.
        size = context or min(DEFAULT_CONTEXT, limit or DEFAULT_CONTEXT)
        if limit:
            size = min(size, limit)
    else:
        size = context or _openai_context(base, model, api_key) or 4096
    return Backend(kind, base, model, max(MIN_CONTEXT, size), api_key, thinking)


def _stream_lines(response) -> Iterator[str]:
    for raw in response:
        line = raw.decode("utf-8", errors="replace").strip()
        if line:
            yield line


def chat(
    backend: Backend, messages: list[dict], *, max_tokens: int,
    on_text: Callable[[str], None] | None = None,
) -> str:
    """Send one conversation and return the reply, streaming text to on_text as it arrives."""
    if backend.kind == OLLAMA:
        url = f"{backend.base}/api/chat"
        payload = {
            "model": backend.model, "messages": messages, "stream": True, "keep_alive": "10m",
            "options": {"num_ctx": backend.context, "num_predict": max_tokens, "temperature": 0.1},
        }
        if backend.thinking:
            # Some models cannot switch thinking off and would then think inside the answer.
            # Keep the reasoning in its own field and leave room for it.
            payload["think"] = True
            payload["options"]["num_predict"] = max_tokens + 8192
    else:
        url = f"{backend.base}/chat/completions"
        payload = {
            "model": backend.model, "messages": messages, "stream": True,
            "max_tokens": max_tokens, "temperature": 0.1,
        }
    pieces: list[str] = []
    visible = _Visible(on_text)
    try:
        with _request(url, payload, api_key=backend.api_key, timeout=_GENERATE_TIMEOUT) as response:
            for line in _stream_lines(response):
                text, done = _parse_chunk(backend.kind, line)
                if text:
                    pieces.append(text)
                    visible.feed(text)
                if done:
                    break
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise LLMError("llm_failed", detail or str(exc)) from exc
    except (OSError, urllib.error.URLError) as exc:
        raise LLMError("llm_failed", str(exc)) from exc
    visible.flush()
    return _THINK.sub("", "".join(pieces)).strip()


def _parse_chunk(kind: str, line: str) -> tuple[str, bool]:
    if kind == OPENAI:
        if not line.startswith("data:"):
            return "", False
        line = line[5:].strip()
        if line == "[DONE]":
            return "", True
    try:
        data = json.loads(line)
    except ValueError:
        return "", False
    if not isinstance(data, dict):
        return "", False
    if data.get("error"):
        raise LLMError("llm_failed", str(data["error"])[:300])
    if kind == OLLAMA:
        return (data.get("message") or {}).get("content") or "", bool(data.get("done"))
    choices = data.get("choices") or [{}]
    delta = choices[0].get("delta") or {}
    return delta.get("content") or "", choices[0].get("finish_reason") is not None


class _Visible:
    """Forward streamed text while hiding <think> blocks that some servers inline."""

    def __init__(self, sink: Callable[[str], None] | None):
        self.sink = sink
        self.buffer = ""
        self.thinking = False
        self.started = False

    def feed(self, text: str) -> None:
        if self.sink is None:
            return
        self.buffer += text
        while self.buffer:
            if self.thinking:
                end = self.buffer.find("</think>")
                if end < 0:
                    self.buffer = self.buffer[-8:]
                    return
                self.buffer = self.buffer[end + 8:]
                self.thinking = False
                continue
            start = self.buffer.find("<think>")
            if start >= 0:
                self._emit(self.buffer[:start])
                self.buffer = self.buffer[start + 7:]
                self.thinking = True
                continue
            # Keep a possible partial tag for the next chunk.
            keep = next((n for n in range(min(6, len(self.buffer)), 0, -1) if "<think>".startswith(
                self.buffer[-n:])), 0)
            self._emit(self.buffer[:len(self.buffer) - keep])
            self.buffer = self.buffer[len(self.buffer) - keep:]
            return

    def _emit(self, text: str) -> None:
        if not self.started:
            text = text.lstrip()
        if text:
            self.started = True
            self.sink(text)

    def flush(self) -> None:
        if self.sink is not None and not self.thinking and self.buffer:
            self._emit(self.buffer)
        self.buffer = ""
