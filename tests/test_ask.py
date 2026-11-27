import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from any2llm import ask, cli, llm
from any2llm.ask import Asker
from any2llm.llm import OLLAMA, OPENAI, Backend, LLMError
from any2llm.parsers import ParsedFile, PdfPage


class _Server:
    """A tiny Ollama- or OpenAI-style server that records requests."""

    def __init__(self, kind: str, reply: str = "Hello there.", models=("qwen3:4b",), context=32768):
        self.kind, self.reply, self.models, self.context = kind, reply, list(models), context
        self.requests: list[dict] = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _json(self, data, status=200):
                body = json.dumps(data).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if owner.kind == OLLAMA and self.path == "/api/tags":
                    return self._json({"models": [{"name": name, "modified_at": f"2026-01-0{i + 1}"}
                                                  for i, name in enumerate(owner.models)]})
                if owner.kind == OPENAI and self.path == "/v1/models":
                    return self._json({"data": [{"id": name} for name in owner.models]})
                return self._json({"error": "not found"}, 404)

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if self.path == "/api/show":
                    return self._json({"model_info": {"qwen3.context_length": owner.context},
                                       "capabilities": ["completion", "thinking"]})
                owner.requests.append({"path": self.path, **body})
                self.send_response(200)
                self.end_headers()
                words = [word + " " for word in owner.reply.split(" ")]
                if owner.kind == OLLAMA:
                    for word in ["<think>hidden</think>", *words]:
                        line = {"message": {"role": "assistant", "content": word}, "done": False}
                        self.wfile.write(json.dumps(line).encode() + b"\n")
                    self.wfile.write(json.dumps({"message": {"content": ""}, "done": True}).encode() + b"\n")
                else:
                    for word in words:
                        chunk = {"choices": [{"delta": {"content": word}, "finish_reason": None}]}
                        self.wfile.write(b"data: " + json.dumps(chunk).encode() + b"\n\n")
                    self.wfile.write(b"data: [DONE]\n\n")

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()


@pytest.fixture
def ollama_server():
    server = _Server(OLLAMA)
    yield server
    server.close()


@pytest.fixture
def openai_server():
    server = _Server(OPENAI, models=("nomic-embed-text", "local-model"))
    yield server
    server.close()


def test_ollama_connection_sets_context_and_hides_thinking(ollama_server):
    backend = llm.connect(ollama_server.url)
    assert (backend.kind, backend.model, backend.context, backend.thinking) == (OLLAMA, "qwen3:4b", 8192, True)
    streamed = []
    reply = llm.chat(backend, [{"role": "user", "content": "hi"}], max_tokens=50, on_text=streamed.append)
    assert reply == "Hello there."
    assert "".join(streamed).strip() == "Hello there." and "hidden" not in "".join(streamed)
    request = ollama_server.requests[-1]
    assert request["options"]["num_ctx"] == 8192 and request["think"] is True


def test_context_never_exceeds_the_model_limit(ollama_server):
    ollama_server.context = 4096
    assert llm.connect(ollama_server.url, context=32000).context == 4096


def test_openai_compatible_server_skips_embedding_models(openai_server):
    backend = llm.connect(openai_server.url + "/v1")
    assert (backend.kind, backend.model, backend.context) == (OPENAI, "local-model", 4096)
    assert llm.chat(backend, [{"role": "user", "content": "hi"}], max_tokens=10) == "Hello there."
    assert openai_server.requests[-1]["path"] == "/v1/chat/completions"


def test_connection_errors_name_the_fix(ollama_server, monkeypatch):
    with pytest.raises(LLMError) as missing:
        llm.connect(ollama_server.url, model="llama9")
    assert missing.value.key == "llm_model_missing"
    ollama_server.models = []
    with pytest.raises(LLMError) as empty:
        llm.connect(ollama_server.url)
    assert empty.value.key == "llm_no_models"
    monkeypatch.setattr(llm, "LOCAL_SERVERS", ("http://127.0.0.1:9",))
    with pytest.raises(LLMError) as nothing:
        llm.connect()
    assert nothing.value.key == "llm_not_found"


PDF = ParsedFile("PDF", "", tuple(
    PdfPage(number, f"Page {number} filler text about the project timeline. " * 40
            + (" Payment is due within 45 days of delivery." if number == 7 else ""))
    for number in range(1, 13)
))


class _Script:
    """Answer map requests with notes from the page that holds the fact."""

    def __init__(self):
        self.calls = []

    def __call__(self, backend, messages, *, max_tokens, on_text=None):
        self.calls.append(messages)
        content = messages[-1]["content"]
        if "<notes>" in content:
            reply = 'Payment terms: "Payment is due within 45 days of delivery" [contract.pdf, p. 7]'
        elif "within 45 days" in content:
            reply = '- "Payment is due within 45 days of delivery" [contract.pdf, p. 7]'
        else:
            reply = "NONE"
        if on_text:
            on_text(reply)
        return reply


def test_large_documents_are_read_in_parts_and_combined():
    backend = Backend(OLLAMA, "http://x", "m", 4096)
    script = _Script()
    asker = Asker(backend, {Path("contract.pdf"): PDF}, "en", send=script)
    shown = []
    answer = asker.answer("When is payment due?", shown.append)
    assert len(script.calls) > 2
    assert "<notes>" in script.calls[-1][-1]["content"]
    assert shown == [answer]
    report = asker.check(answer)
    assert report.passed and report.checks[0].found_page == 7


def test_small_documents_take_one_request():
    backend = Backend(OLLAMA, "http://x", "m", 32768)
    script = _Script()
    asker = Asker(backend, {Path("contract.pdf"): PDF}, "en", send=script)
    asker.answer("When is payment due?", lambda _: None)
    assert len(script.calls) == 1


def test_nothing_relevant_says_so_without_a_final_request():
    backend = Backend(OLLAMA, "http://x", "m", 4096)
    calls = []

    def send(backend, messages, *, max_tokens, on_text=None):
        calls.append(messages)
        return "NONE"

    shown = []
    asker = Asker(backend, {Path("contract.pdf"): PDF}, "en", send=send)
    assert asker.answer("Who won the match?", shown.append) == ""
    assert shown and all("<notes>" not in call[-1]["content"] for call in calls)


def test_ask_command_end_to_end(ollama_server, tmp_path, capsys):
    (tmp_path / "notes.txt").write_text("The freight forwarder confirmed the pickup window.\n")
    ollama_server.reply = 'The pickup is confirmed: "confirmed the pickup window" [notes.txt]'
    code = cli.main(["ask", str(tmp_path), "Is", "the", "pickup", "confirmed?", "--api", ollama_server.url,
                     "--lang", "en"])
    captured = capsys.readouterr()
    assert code == 0
    assert "confirmed the pickup window" in captured.out
    assert "1 of 1 citations match" in captured.err
    sent = ollama_server.requests[-1]["messages"]
    assert "Is the pickup confirmed?" in sent[-1]["content"] and "<file" in sent[-1]["content"]


def test_ask_command_reports_a_failed_citation(ollama_server, tmp_path, capsys):
    (tmp_path / "notes.txt").write_text("The freight forwarder confirmed the pickup window.\n")
    ollama_server.reply = 'Yes: "the pickup was cancelled" [notes.txt]'
    assert cli.main(["ask", str(tmp_path), "Pickup?", "--api", ollama_server.url, "--lang", "en"]) == 1
    assert "quote not found" in capsys.readouterr().err


def test_ask_without_server_explains_setup(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(llm, "LOCAL_SERVERS", ("http://127.0.0.1:9",))
    assert ask.main([str(tmp_path), "question", "--lang", "en"]) == 1
    assert "ollama pull" in capsys.readouterr().err


def test_first_word_is_the_folder_only_when_it_is_one(tmp_path):
    assert ask._split_target([str(tmp_path), "what", "is", "due?"]) == (str(tmp_path), "what is due?")
    assert ask._split_target(["what", "is", "due?"]) == (".", "what is due?")
    assert ask._split_target(["demo"]) == ("demo", "")
