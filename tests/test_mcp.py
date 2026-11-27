import json
import subprocess
import sys
from io import BytesIO

import pytest

from any2llm import mcp, pipeline, tokenizer
from any2llm.mcp_tools import Library
from any2llm.parsers import parse_file

MODERN = {"_meta": {
    "io.modelcontextprotocol/protocolVersion": "2026-07-28",
    "io.modelcontextprotocol/clientCapabilities": {},
}}


@pytest.fixture
def server(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "parse_selected", lambda path, **kwargs: parse_file(path, **kwargs))
    monkeypatch.setattr(tokenizer, "get_encoding", lambda: None)
    docs = tmp_path / "docs"
    (docs / "nested").mkdir(parents=True)
    (docs / "notes.txt").write_text("Pilot shipment is due on March 12.\n", encoding="utf-8")
    (docs / "nested" / "terms.md").write_text("# Terms\n\nNet 30.\n", encoding="utf-8")
    (docs / "photo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (docs / "credentials.json").write_text("{}", encoding="utf-8")
    (tmp_path / "outside.txt").write_text("Private", encoding="utf-8")
    return mcp.Server(Library(docs))


def _request(server, method, params=None, ident=1):
    return server.handle({"jsonrpc": "2.0", "id": ident, "method": method, "params": params or {}})


def _call(server, name, **arguments):
    response = _request(server, "tools/call", {**MODERN, "name": name, "arguments": arguments})
    result = response["result"]
    return result["content"][0]["text"], result["isError"]


def test_modern_discovery_and_legacy_handshake(server):
    discovered = _request(server, "server/discover", MODERN)["result"]
    assert discovered["resultType"] == "complete"
    assert "2026-07-28" in discovered["supportedVersions"] and discovered["capabilities"] == {"tools": {}}
    assert discovered["_meta"]["io.modelcontextprotocol/serverInfo"]["name"] == "any2llm"

    legacy = _request(server, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {}})["result"]
    assert legacy["protocolVersion"] == "2025-06-18" and legacy["serverInfo"]["name"] == "any2llm"
    future = _request(server, "initialize", {"protocolVersion": "2099-01-01"})["result"]
    assert future["protocolVersion"] == mcp.LEGACY_VERSIONS[0]
    assert server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None

    tools = _request(server, "tools/list", MODERN)["result"]["tools"]
    assert [tool["name"] for tool in tools] == ["list_documents", "read_documents"]
    assert all(tool["annotations"]["readOnlyHint"] for tool in tools)


def test_protocol_errors(server):
    unsupported = _request(server, "tools/list", {"_meta": {"io.modelcontextprotocol/protocolVersion": "1999"}})
    assert unsupported["error"]["code"] == -32022 and unsupported["error"]["data"]["requested"] == "1999"
    assert _request(server, "resources/list")["error"]["code"] == -32601
    assert _request(server, "tools/call", {"name": "delete_everything"})["error"]["code"] == -32602
    assert server.handle(["not", "a", "request"])["error"]["code"] == -32600


def test_list_and_read_documents(server):
    listing, error = _call(server, "list_documents")
    assert not error
    assert "- notes.txt" in listing and "photo.png" in listing and "credentials.json" in listing
    assert "recursive=true" in listing and "terms.md" not in listing

    text, error = _call(server, "read_documents", recursive=True)
    assert not error
    assert 'name="nested/terms.md"' in text and "March 12" in text
    assert "Skipped credentials.json" in text and '"credentials.json"' not in text.split("\n\n", 1)[1]

    chosen, _ = _call(server, "read_documents", paths=["nested/terms.md", "missing.pdf"])
    assert "Net 30." in chosen and "March 12" not in chosen and "Skipped missing.pdf" in chosen


def test_large_content_is_served_in_batches(server, tmp_path):
    (tmp_path / "docs" / "notes.txt").write_text("A line of shipment notes.\n" * 2000, encoding="utf-8")
    first, _ = _call(server, "read_documents", max_tokens=5000)
    assert "batch 1 of" in first and "batch=2" in first
    total = int(first.split("batch 1 of ", 1)[1].split(" ", 1)[0])
    last, _ = _call(server, "read_documents", max_tokens=5000, batch=total)
    assert f"batch {total} of {total}" in last and "More content remains" not in last
    missing, error = _call(server, "read_documents", max_tokens=5000, batch=total + 1)
    assert error and "does not exist" in missing


@pytest.mark.parametrize("arguments", [
    {"folder": ".."}, {"folder": "/"}, {"folder": "nested/../../"},
    {"max_tokens": 10}, {"batch": 0}, {"batch": True}, {"paths": "notes.txt"}, {"surprise": 1},
])
def test_invalid_arguments_are_tool_errors(server, arguments):
    text, error = _call(server, "read_documents", **arguments)
    assert error and "Private" not in text


def test_stdio_server_writes_only_protocol_messages(tmp_path):
    (tmp_path / "notes.txt").write_text("Hello from stdio.\n", encoding="utf-8")
    messages = [
        {"jsonrpc": "2.0", "id": 1, "method": "server/discover", "params": MODERN},
        {"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 9}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {**MODERN, "name": "read_documents", "arguments": {}}},
    ]
    stdin = "\n".join(map(json.dumps, messages)) + "\n{not json\n"
    result = subprocess.run(
        [sys.executable, "-m", "any2llm", "mcp", str(tmp_path), "--lang", "en"],
        input=stdin.encode(), capture_output=True, timeout=120, check=True,
    )
    responses = [json.loads(line) for line in result.stdout.decode().splitlines()]
    assert [response["id"] for response in responses] == [1, 2, None]
    assert "Hello from stdio." in responses[1]["result"]["content"][0]["text"]
    assert responses[2]["error"]["code"] == -32700


def test_serve_skips_blank_lines():
    out = BytesIO()
    mcp.serve(mcp.Server(Library(".")), BytesIO(b"\n  \n"), out)
    assert out.getvalue() == b""


def test_invalid_root_is_reported(tmp_path, capsys):
    assert mcp.main([str(tmp_path / "missing"), "--lang", "en"]) == 1
    assert "missing" in capsys.readouterr().err
