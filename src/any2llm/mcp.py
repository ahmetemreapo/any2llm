"""Serve the document tools over the Model Context Protocol on stdio.

The server speaks the stateless 2026-07-28 protocol and also answers the
``initialize`` handshake of earlier protocol versions.
"""

import argparse
import json
import os
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import BinaryIO

from . import ocr
from .languages import LANGUAGE_NAMES, system_language
from .mcp_tools import TOOLS, Library, ToolError
from .messages import MESSAGES, help_text

MODERN_VERSIONS = ("2026-07-28",)
LEGACY_VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
_VERSION_KEY = "io.modelcontextprotocol/protocolVersion"
_CACHE = {"ttlMs": 3_600_000, "cacheScope": "public"}
INSTRUCTIONS = (
    "any2llm reads local PDF, Office, EPUB, HTML, text, and code files. Call list_documents to see what a folder "
    "contains, then read_documents. Cite PDF content with the physical page number from its <page> tag, as a short "
    "word-for-word quote followed by its source: \"exact words\" [filename, p. N]. Before answering, call "
    "check_citations with your draft and fix any citation it does not confirm."
)

PARSE_ERROR, INVALID_REQUEST, METHOD_NOT_FOUND, INVALID_PARAMS, INTERNAL_ERROR = -32700, -32600, -32601, -32602, -32603
UNSUPPORTED_VERSION = -32022


def _server_info() -> dict:
    try:
        number = version("any2llm")
    except PackageNotFoundError:
        number = "0"
    return {"name": "any2llm", "title": "any2llm", "version": number}


class Server:
    def __init__(self, library: Library):
        self.library = library

    def handle(self, message: object) -> dict | None:
        """Return the response to one JSON-RPC message, or None for notifications."""
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0" or not isinstance(
            message.get("method"), str,
        ):
            ident = message.get("id") if isinstance(message, dict) else None
            return _error(ident, INVALID_REQUEST, "Invalid request")
        if "id" not in message:
            return None
        ident = message["id"]
        params = message.get("params") or {}
        if not isinstance(params, dict):
            return _error(ident, INVALID_PARAMS, "params must be an object")
        meta = params.get("_meta") or {}
        requested = meta.get(_VERSION_KEY) if isinstance(meta, dict) else None
        if requested is not None and requested not in (*MODERN_VERSIONS, *LEGACY_VERSIONS):
            return _error(ident, UNSUPPORTED_VERSION, "Unsupported protocol version", {
                "supported": [*MODERN_VERSIONS, *LEGACY_VERSIONS], "requested": requested,
            })
        try:
            result = self._dispatch(message["method"], params)
        except _RpcError as exc:
            return _error(ident, exc.code, exc.message)
        except Exception:  # noqa: BLE001 - one failing request must not stop the server.
            return _error(ident, INTERNAL_ERROR, "Internal error")
        return {"jsonrpc": "2.0", "id": ident, "result": {"resultType": "complete", **result}}

    def _dispatch(self, method: str, params: dict) -> dict:
        if method == "server/discover":
            return {
                "supportedVersions": [*MODERN_VERSIONS, *LEGACY_VERSIONS],
                "capabilities": {"tools": {}},
                "_meta": {"io.modelcontextprotocol/serverInfo": _server_info()},
                "instructions": INSTRUCTIONS, **_CACHE,
            }
        if method == "initialize":
            requested = params.get("protocolVersion")
            negotiated = requested if requested in LEGACY_VERSIONS else LEGACY_VERSIONS[0]
            return {
                "protocolVersion": negotiated, "capabilities": {"tools": {}},
                "serverInfo": _server_info(), "instructions": INSTRUCTIONS,
            }
        if method == "ping":
            return {}
        if method == "tools/list":
            return {"tools": TOOLS, **_CACHE}
        if method == "tools/call":
            return self._call(params)
        raise _RpcError(METHOD_NOT_FOUND, f"Method not found: {method}")

    def _call(self, params: dict) -> dict:
        name = params.get("name")
        if name not in {tool["name"] for tool in TOOLS}:
            raise _RpcError(INVALID_PARAMS, f"Unknown tool: {name}")
        try:
            text = self.library.call(name, params.get("arguments") or {})
        except (ToolError, TypeError) as exc:
            return {"content": [{"type": "text", "text": str(exc)}], "isError": True}
        return {"content": [{"type": "text", "text": text}], "isError": False}


class _RpcError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


def _error(ident: object, code: int, message: str, data: dict | None = None) -> dict:
    error = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": ident, "error": error}


def serve(server: Server, stdin: BinaryIO, stdout: BinaryIO) -> None:
    """Answer newline-delimited JSON-RPC messages until stdin closes."""
    for line in stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
        except ValueError:
            response = _error(None, PARSE_ERROR, "Parse error")
        else:
            response = server.handle(message)
        if response is not None:
            stdout.write(json.dumps(response, ensure_ascii=False).encode("utf-8") + b"\n")
            stdout.flush()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="any2llm mcp", add_help=False, allow_abbrev=False, exit_on_error=False)
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--lang", choices=LANGUAGE_NAMES)
    parser.add_argument("--ocr", action="store_true")
    parser.add_argument("--ocr-lang", metavar="LANG")
    parser.add_argument("-h", "--help", action="store_true")
    lang = system_language()
    try:
        args, unknown = parser.parse_known_args(argv)
    except argparse.ArgumentError as exc:
        print(MESSAGES[lang]["invalid_option"].format(option=exc.argument_name or ""), file=sys.stderr)
        return 2
    lang = args.lang or lang
    msg = MESSAGES[lang]
    if unknown:
        print(msg["unknown_option"].format(option=unknown[0]), "any2llm --help", file=sys.stderr)
        return 2
    if args.help:
        print(help_text(lang))
        return 0
    root = Path(args.root).expanduser()
    if not root.is_dir():
        print(f'{msg["not_folder"]}: {root}', file=sys.stderr)
        return 1
    ocr_lang = args.ocr_lang or ("eng" if args.ocr else None)
    if ocr_lang is not None and (error := ocr.setup_error(ocr_lang)):
        print(msg[error].format(lang=ocr_lang), file=sys.stderr)
        ocr_lang = None
    stdout = sys.stdout.buffer
    # Only protocol messages may reach stdout, so route any stray prints to stderr.
    sys.stdout = sys.stderr
    try:
        serve(Server(Library(Path(os.path.realpath(root)), lang=lang, ocr_lang=ocr_lang)), sys.stdin.buffer, stdout)
    except KeyboardInterrupt:
        return 130
    return 0
