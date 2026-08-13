#!/usr/bin/env python3
from __future__ import annotations

import json
import mimetypes
import os
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from federation.core import (
    APP, BASE, DB, JSONL, Providers, audit_claim, audit_inventory,
    count_text, create_agent_packet, init_db, ledger, mirror_path,
    route, save_record, voice_resolve,
)

HOST = os.environ.get("ALETHEIA_HOST", "127.0.0.1")
PORT = int(os.environ.get("ALETHEIA_PORT", "8765"))
FRONTEND = APP / "frontend"

class Handler(BaseHTTPRequestHandler):
    server_version = "OmegaSovereignFederation/2.0"

    def log_message(self, fmt, *args):
        sys.stderr.write(f"[OMEGA] {self.client_address[0]} {fmt % args}\n")

    def send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 2_000_000:
            raise ValueError("invalid request body length")
        value = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("JSON body must be an object")
        return value

    def serve_file(self, path: Path):
        if not path.exists() or not path.is_file():
            self.send_error(404)
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            p = Providers()
            self.send_json({
                "ok": True,
                "service": "OMEGA_SOVEREIGN_FEDERATION",
                "version": "2.0.0",
                "base": str(BASE),
                "database": str(DB),
                "jsonl": str(JSONL),
                "providers": p.status(),
                "record_count": len(ledger(500)),
            })
            return
        if parsed.path == "/api/ledger":
            q = parse_qs(parsed.query)
            self.send_json({"ok": True, "records": ledger(int(q.get("limit", ["50"])[0]))})
            return
        if parsed.path == "/api/agent/tasks":
            from federation.core import AGENT_PENDING
            tasks = []
            for p in sorted(AGENT_PENDING.glob("*.json"), reverse=True):
                try:
                    tasks.append(json.loads(p.read_text(encoding="utf-8")))
                except Exception:
                    pass
            self.send_json({"ok": True, "tasks": tasks})
            return
        if parsed.path in {"/", "/index.html"}:
            self.serve_file(FRONTEND / "index.html")
            return
        safe = parsed.path.lstrip("/")
        target = (FRONTEND / safe).resolve()
        if str(target).startswith(str(FRONTEND.resolve())) and target.exists():
            self.serve_file(target)
            return
        self.send_error(404)

    def do_POST(self):
        try:
            payload = self.read_json()
            if self.path == "/api/route":
                self.send_json(route(
                    payload.get("prompt", ""),
                    payload.get("route", "auto"),
                    payload.get("system", ""),
                    payload.get("case_id"),
                    payload.get("context", {}),
                ))
                return
            if self.path == "/api/records":
                self.send_json({"ok": True, "record": save_record(payload)})
                return
            if self.path == "/api/audit/claim":
                self.send_json({"ok": True, "result": audit_claim(payload)})
                return
            if self.path == "/api/audit/inventory":
                self.send_json({"ok": True, "result": audit_inventory(
                    payload["canonical"], payload["observed"],
                    payload.get("canary", "bekingdomcomejoker-cpu/glass-chess"),
                )})
                return
            if self.path == "/api/voice":
                self.send_json({"ok": True, "result": voice_resolve(payload["phrase"])})
                return
            if self.path == "/api/verify/count":
                self.send_json({"ok": True, "result": count_text(
                    payload["path"], int(payload["expected"]),
                    payload.get("tokenizer", "whitespace"),
                )})
                return
            if self.path == "/api/agent/queue":
                self.send_json({"ok": True, **create_agent_packet(
                    payload["task"], payload.get("context"),
                    payload.get("mirrors", []),
                )})
                return
            self.send_json({"ok": False, "error": "not found"}, 404)
        except KeyError as exc:
            self.send_json({"ok": False, "error": f"missing field: {exc}"}, 400)
        except ValueError as exc:
            self.send_json({"ok": False, "error": str(exc)}, 400)
        except Exception as exc:
            self.send_json({"ok": False, "error": str(exc)}, 503)

def main():
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"OMEGA Sovereign Federation: http://{HOST}:{PORT}")
    print(f"Local continuity body: {BASE}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
