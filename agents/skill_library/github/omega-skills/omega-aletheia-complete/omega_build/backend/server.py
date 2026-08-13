#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HOME = Path.home()
BASE = Path(os.environ.get("CAT_EOF_HOME", HOME / "cat_eof")).expanduser()
STATE = BASE / "state"
JSONL = STATE / "perception_integrity.jsonl"
DB = STATE / "cat_eof.db"

HOST = os.environ.get("ALETHEIA_HOST", "127.0.0.1")
PORT = int(os.environ.get("ALETHEIA_PORT", "8765"))
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
ANTHROPIC_VERSION = os.environ.get("ANTHROPIC_VERSION", "2023-06-01")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_storage() -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS perception_records (
                record_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                record_type TEXT NOT NULL,
                case_id TEXT,
                sha256 TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        connection.commit()


def save_record(payload: dict) -> dict:
    init_storage()
    record = dict(payload)
    record.setdefault("record_id", f"record-{uuid.uuid4()}")
    record.setdefault("created_at", utc_now())
    record.setdefault("record_type", "unspecified")
    canonical = json.dumps(record, ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    record["sha256"] = digest
    canonical = json.dumps(record, ensure_ascii=False, sort_keys=True)

    with JSONL.open("a", encoding="utf-8") as handle:
        handle.write(canonical + "\n")

    with sqlite3.connect(DB) as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO perception_records (
                record_id, created_at, record_type, case_id, sha256, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                record["record_id"],
                record["created_at"],
                record["record_type"],
                record.get("case_id"),
                digest,
                canonical,
            ),
        )
        connection.commit()

    return record


def ledger(limit: int) -> list[dict]:
    init_storage()
    limit = max(1, min(limit, 500))
    with sqlite3.connect(DB) as connection:
        rows = connection.execute(
            """
            SELECT payload_json
            FROM perception_records
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [json.loads(row[0]) for row in rows]


def claude_message(payload: dict) -> dict:
    if not API_KEY:
        raise RuntimeError(
            "Claude is not configured. Set ANTHROPIC_API_KEY server-side."
        )

    prompt = str(payload.get("prompt", "")).strip()
    if not prompt:
        raise ValueError("prompt is required")

    stage = str(payload.get("stage", "unspecified"))
    context = payload.get("context", {})
    system = str(payload.get("system", "")).strip()
    max_tokens = int(payload.get("max_tokens", 1200))
    max_tokens = max(64, min(max_tokens, 8192))

    user_content = (
        f"STAGE: {stage}\n\n"
        f"STRUCTURED CONTEXT:\n"
        f"{json.dumps(context, ensure_ascii=False, indent=2)}\n\n"
        f"TASK:\n{prompt}"
    )

    request_payload = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": user_content}],
    }
    if system:
        request_payload["system"] = system

    request = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(request_payload).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-api-key": API_KEY,
            "anthropic-version": ANTHROPIC_VERSION,
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Anthropic API HTTP {error.code}: {body}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Anthropic API unavailable: {error}") from error

    text_parts = [
        block.get("text", "")
        for block in result.get("content", [])
        if block.get("type") == "text"
    ]
    text = "".join(text_parts).strip()
    if not text:
        raise RuntimeError("Anthropic response contained no text output")

    audit = save_record(
        {
            "record_type": "claude_analysis",
            "case_id": payload.get("context", {}).get("case_id"),
            "stage": stage,
            "model": result.get("model", MODEL),
            "request_id": result.get("id"),
            "generated": {"text": text},
            "usage": result.get("usage", {}),
        }
    )

    return {
        "ok": True,
        "text": text,
        "model": result.get("model", MODEL),
        "request_id": result.get("id"),
        "record_id": audit["record_id"],
        "usage": result.get("usage", {}),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "AletheiaClaudeBridge/1.0"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write(
            f"[{utc_now()}] {self.client_address[0]} {fmt % args}\n"
        )

    def _headers(self, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.end_headers()

    def _json(self, payload: dict, status: int = 200) -> None:
        self._headers(status)
        self.wfile.write(
            json.dumps(payload, ensure_ascii=False).encode("utf-8")
        )

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 2_000_000:
            raise ValueError("invalid request body length")
        raw = self.rfile.read(length)
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("JSON body must be an object")
        return payload

    def do_OPTIONS(self) -> None:
        self._headers(HTTPStatus.NO_CONTENT)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            init_storage()
            count = 0
            with sqlite3.connect(DB) as connection:
                count = connection.execute(
                    "SELECT COUNT(*) FROM perception_records"
                ).fetchone()[0]
            self._json(
                {
                    "ok": True,
                    "service": "OMEGA_ALETHEIA_CLAUDE_BRIDGE",
                    "host": HOST,
                    "port": PORT,
                    "claude_configured": bool(API_KEY),
                    "model": MODEL,
                    "record_count": count,
                    "jsonl": str(JSONL),
                    "database": str(DB),
                }
            )
            return

        if parsed.path == "/api/ledger":
            query = parse_qs(parsed.query)
            try:
                limit = int(query.get("limit", ["50"])[0])
            except ValueError:
                limit = 50
            self._json({"ok": True, "records": ledger(limit)})
            return

        self._json({"ok": False, "error": "not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        try:
            payload = self._read_json()

            if self.path == "/api/records":
                record = save_record(payload)
                self._json({"ok": True, "record": record})
                return

            if self.path == "/api/claude":
                result = claude_message(payload)
                self._json(result)
                return

            self._json({"ok": False, "error": "not found"}, HTTPStatus.NOT_FOUND)

        except ValueError as error:
            self._json(
                {"ok": False, "error": str(error)},
                HTTPStatus.BAD_REQUEST,
            )
        except Exception as error:
            self._json(
                {"ok": False, "error": str(error)},
                HTTPStatus.SERVICE_UNAVAILABLE,
            )


def main() -> int:
    init_storage()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"OMEGA · ALETHEIA Claude bridge: http://{HOST}:{PORT}")
    print(f"Claude configured: {bool(API_KEY)}")
    print(f"Model: {MODEL}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
