from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

BASE = Path(os.environ.get("CAT_EOF_HOME", Path.home() / "cat_eof")).expanduser()
APP = BASE / "apps" / "omega-sovereign-federation"
STATE = BASE / "state"
OUTPUT = BASE / "output" / "federation"
REGISTRY = BASE / "registry"
AGENT_PENDING = BASE / "agent_queue" / "pending"
AGENT_COMPLETE = BASE / "agent_queue" / "complete"
DB = STATE / "cat_eof.db"
JSONL = STATE / "perception_integrity.jsonl"
FED_BUS = STATE / "federation_bus.jsonl"
CAT_BUS = BASE / "cat_bus.jsonl"
COMM_BUS = BASE / "comm_bus.jsonl"
VOICE_REGISTRY = REGISTRY / "voice_registry.json"

MARKERS = {
    "@fast": "fast", "@reason": "reason", "@code": "code",
    "@local": "local", "@omega": "omega", "@bridge": "bridge",
    "@beehive": "federate", "@federate": "federate",
    "@consensus": "consensus", "@gpt": "gpt", "@openai": "openai",
    "@gemini": "gemini", "@claude": "claude", "@agent": "agent",
    "@drive": "drive", "@dropbox": "dropbox",
}

DEFAULT_VOICE = {
    "manuscriptly": {"canonical": "Node 4 / Manus", "status": "corrected"},
    "deep-sea": {"canonical": "DeepSeek", "status": "corrected"},
    "claw": {"canonical": "Claude", "status": "corrected"},
}

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

def ensure_dirs() -> None:
    for p in [STATE, OUTPUT, REGISTRY, AGENT_PENDING, AGENT_COMPLETE]:
        p.mkdir(parents=True, exist_ok=True)

def sha256_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

def append_jsonl(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as h:
        h.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")

def init_db() -> None:
    ensure_dirs()
    with sqlite3.connect(DB) as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS federation_records (
          record_id TEXT PRIMARY KEY,
          created_at TEXT NOT NULL,
          record_type TEXT NOT NULL,
          case_id TEXT,
          route TEXT,
          provider TEXT,
          status TEXT NOT NULL,
          sha256 TEXT NOT NULL,
          payload_json TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_fed_created
          ON federation_records(created_at DESC);
        CREATE TABLE IF NOT EXISTS unknown_voices (
          phrase TEXT PRIMARY KEY,
          normalized TEXT NOT NULL,
          status TEXT NOT NULL,
          canonical TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS agent_tasks (
          task_id TEXT PRIMARY KEY,
          created_at TEXT NOT NULL,
          status TEXT NOT NULL,
          packet_path TEXT NOT NULL,
          payload_json TEXT NOT NULL
        );
        """)
        con.commit()

def save_record(payload: dict) -> dict:
    init_db()
    record = dict(payload)
    record.setdefault("record_id", f"fed-{uuid.uuid4()}")
    record.setdefault("created_at", now())
    record.setdefault("record_type", "federation_event")
    record.setdefault("status", "recorded")
    digest_source = dict(record)
    digest_source.pop("sha256", None)
    record["sha256"] = sha256_json(digest_source)
    body = json.dumps(record, ensure_ascii=False, sort_keys=True)
    with sqlite3.connect(DB) as con:
        con.execute(
            """INSERT OR REPLACE INTO federation_records
               (record_id, created_at, record_type, case_id, route, provider,
                status, sha256, payload_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record["record_id"], record["created_at"], record["record_type"],
                record.get("case_id"), record.get("route"), record.get("provider"),
                record["status"], record["sha256"], body,
            ),
        )
        con.commit()
    append_jsonl(JSONL, record)
    append_jsonl(FED_BUS, {
        "timestamp": record["created_at"],
        "kind": record["record_type"],
        "route": record.get("route"),
        "provider": record.get("provider"),
        "status": record["status"],
        "record_id": record["record_id"],
        "sha256": record["sha256"],
    })
    for legacy in [CAT_BUS, COMM_BUS]:
        if legacy.exists():
            append_jsonl(legacy, {
                "timestamp": record["created_at"],
                "kind": "federation_result",
                "route": record.get("route"),
                "source": record.get("provider"),
                "status": record["status"],
                "record_id": record["record_id"],
            })
    return record

def ledger(limit: int = 50) -> list[dict]:
    init_db()
    limit = max(1, min(int(limit), 500))
    with sqlite3.connect(DB) as con:
        rows = con.execute(
            "SELECT payload_json FROM federation_records ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [json.loads(r[0]) for r in rows]

def command_exists(name: str) -> bool:
    return bool(shutil.which(name))

def http_json(url: str, payload: dict | None = None, headers: dict | None = None,
              timeout: int = 120, method: str | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method=method or ("POST" if payload is not None else "GET"),
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Endpoint unavailable: {exc}") from exc

def run_command(args: list[str], prompt: str | None = None, timeout: int = 300,
                cwd: Path | None = None) -> str:
    proc = subprocess.run(
        args,
        input=prompt,
        text=True,
        capture_output=True,
        timeout=timeout,
        cwd=str(cwd or BASE),
        check=False,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout).strip()
        raise RuntimeError(f"exit={proc.returncode}: {err[:1500]}")
    text = (proc.stdout or proc.stderr).strip()
    if not text:
        raise RuntimeError("command returned no output")
    return text

def extract_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts = [extract_text(v) for v in value]
        return "\n".join(p for p in parts if p)
    if isinstance(value, dict):
        for key in ["output_text", "result", "response", "text", "content", "message"]:
            if key in value:
                text = extract_text(value[key])
                if text:
                    return text
        for val in value.values():
            text = extract_text(val)
            if text:
                return text
    return ""

def parse_marker(prompt: str, route: str = "auto") -> tuple[str, str]:
    stripped = prompt.strip()
    first = stripped.split(maxsplit=1)[0].lower() if stripped else ""
    if first in MARKERS:
        clean = stripped[len(first):].lstrip()
        return MARKERS[first], clean
    return route, stripped

@dataclass
class Attempt:
    provider: str
    ok: bool
    text: str = ""
    error: str = ""
    meta: dict | None = None

class Providers:
    def __init__(self):
        self.oroute = os.environ.get("OMEGA_OROUTE_COMMAND", "oroute")
        self.codex = os.environ.get("CODEX_COMMAND", "codex")
        self.gemini = os.environ.get("GEMINI_COMMAND", "gemini")
        self.claude = os.environ.get("CLAUDE_COMMAND", "claude")
        self.local_completion = os.environ.get(
            "OMEGA_LOCAL_COMPLETION_URL", "http://127.0.0.1:8080/completion"
        )
        self.local_openai = os.environ.get(
            "OMEGA_LOCAL_OPENAI_URL", "http://127.0.0.1:8080/v1/chat/completions"
        )
        self.ollama_url = os.environ.get(
            "OLLAMA_URL", "http://127.0.0.1:11434/api/generate"
        )
        self.ollama_model = os.environ.get("OLLAMA_MODEL", "")

    def existing_oroute(self, prompt: str, subroute: str = "reason") -> str:
        if not command_exists(self.oroute):
            raise RuntimeError("oroute command not found")
        return run_command([self.oroute, subroute, prompt], timeout=300)

    def llama_completion(self, prompt: str) -> str:
        data = http_json(self.local_completion, {
            "prompt": prompt, "n_predict": 1024, "temperature": 0.2
        }, timeout=120)
        text = extract_text(data)
        if not text:
            raise RuntimeError("local /completion response contained no text")
        return text

    def local_openai_chat(self, prompt: str) -> str:
        data = http_json(self.local_openai, {
            "model": os.environ.get("OMEGA_LOCAL_MODEL", "local"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }, timeout=120)
        try:
            return data["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            text = extract_text(data)
            if text:
                return text
            raise RuntimeError("local OpenAI-compatible response contained no text") from exc

    def ollama(self, prompt: str) -> str:
        if not self.ollama_model:
            raise RuntimeError("OLLAMA_MODEL is not configured")
        data = http_json(self.ollama_url, {
            "model": self.ollama_model, "prompt": prompt, "stream": False
        }, timeout=180)
        text = extract_text(data.get("response", ""))
        if not text:
            raise RuntimeError("Ollama response contained no text")
        return text

    def codex_cli(self, prompt: str) -> str:
        if not command_exists(self.codex):
            raise RuntimeError("Codex CLI not found")
        return run_command(
            [self.codex, "exec", "--skip-git-repo-check",
             "--sandbox", "read-only", "--ephemeral", "-"],
            prompt=prompt, timeout=600, cwd=BASE
        )

    def gemini_cli(self, prompt: str) -> str:
        if not command_exists(self.gemini):
            raise RuntimeError("Gemini CLI not found")
        raw = run_command(
            [self.gemini, "-p", prompt, "--output-format", "json"],
            timeout=600, cwd=BASE
        )
        try:
            text = extract_text(json.loads(raw))
            return text or raw
        except json.JSONDecodeError:
            return raw

    def claude_cli(self, prompt: str) -> str:
        if not command_exists(self.claude):
            raise RuntimeError("Claude Code CLI not found")
        raw = run_command(
            [self.claude, "-p", prompt, "--output-format", "json",
             "--permission-mode", "plan", "--no-session-persistence"],
            timeout=600, cwd=BASE
        )
        try:
            text = extract_text(json.loads(raw))
            return text or raw
        except json.JSONDecodeError:
            return raw

    def openai_api(self, prompt: str, system: str = "") -> str:
        key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        model = os.environ.get("OPENAI_MODEL", "gpt-5.5")
        payload = {"model": model, "input": prompt, "store": False}
        if system:
            payload["instructions"] = system
        data = http_json(
            "https://api.openai.com/v1/responses", payload,
            {"Authorization": f"Bearer {key}"}, timeout=240
        )
        text = extract_text(data.get("output_text", ""))
        if not text:
            outputs = data.get("output", [])
            text = "\n".join(
                c.get("text", "")
                for item in outputs
                for c in item.get("content", [])
                if c.get("type") == "output_text"
            ).strip()
        if not text:
            raise RuntimeError("OpenAI response contained no output text")
        return text

    def gemini_api(self, prompt: str, system: str = "") -> str:
        key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not key:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
        payload: dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        if system:
            payload["system_instruction"] = {"parts": [{"text": system}]}
        data = http_json(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            payload, {"x-goog-api-key": key}, timeout=240
        )
        try:
            return "\n".join(
                p.get("text", "")
                for c in data["candidates"]
                for p in c["content"]["parts"]
                if p.get("text")
            ).strip()
        except Exception as exc:
            raise RuntimeError("Gemini response contained no text") from exc

    def anthropic_api(self, prompt: str, system: str = "") -> str:
        key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured")
        model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": 1800,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            payload["system"] = system
        data = http_json(
            "https://api.anthropic.com/v1/messages", payload,
            {"x-api-key": key, "anthropic-version": "2023-06-01"},
            timeout=240
        )
        text = "\n".join(
            part.get("text", "") for part in data.get("content", [])
            if part.get("type") == "text"
        ).strip()
        if not text:
            raise RuntimeError("Anthropic response contained no text")
        return text

    def agent_webhook(self, packet: dict) -> str:
        url = os.environ.get("OMEGA_AGENT_WEBHOOK_URL", "").strip()
        if not url:
            raise RuntimeError("OMEGA_AGENT_WEBHOOK_URL is not configured")
        token = os.environ.get("OMEGA_AGENT_WEBHOOK_TOKEN", "").strip()
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        data = http_json(url, packet, headers, timeout=240)
        return extract_text(data) or json.dumps(data, ensure_ascii=False)

    def status(self) -> dict:
        return {
            "existing_bridge": {
                "oroute": command_exists(self.oroute),
                "omega_router_v5_2": any(BASE.rglob("omega_router_v5.2.py")),
                "omega_bridge_adapter": any(BASE.rglob("omega_bridge_adapter.py")),
            },
            "local": {
                "llama_completion_url": self.local_completion,
                "openai_compatible_url": self.local_openai,
                "ollama_url": self.ollama_url,
                "ollama_model_configured": bool(self.ollama_model),
            },
            "subscription_cli": {
                "codex": command_exists(self.codex),
                "gemini": command_exists(self.gemini),
                "claude": command_exists(self.claude),
            },
            "api": {
                "openai": bool(os.environ.get("OPENAI_API_KEY", "").strip()),
                "gemini": bool(os.environ.get("GEMINI_API_KEY", "").strip()),
                "anthropic": bool(os.environ.get("ANTHROPIC_API_KEY", "").strip()),
            },
            "agent": {
                "webhook": bool(os.environ.get("OMEGA_AGENT_WEBHOOK_URL", "").strip()),
                "queue": str(AGENT_PENDING),
            },
        }

PROVIDER_METHODS = {
    "oroute_fast": lambda p, x, s: p.existing_oroute(x, "fast"),
    "oroute_reason": lambda p, x, s: p.existing_oroute(x, "reason"),
    "oroute_code": lambda p, x, s: p.existing_oroute(x, "code"),
    "oroute_omega": lambda p, x, s: p.existing_oroute(x, "omega"),
    "llama_completion": lambda p, x, s: p.llama_completion(x),
    "local_openai": lambda p, x, s: p.local_openai_chat(x),
    "ollama": lambda p, x, s: p.ollama(x),
    "codex_cli": lambda p, x, s: p.codex_cli(x),
    "gemini_cli": lambda p, x, s: p.gemini_cli(x),
    "claude_cli": lambda p, x, s: p.claude_cli(x),
    "openai_api": lambda p, x, s: p.openai_api(x, s),
    "gemini_api": lambda p, x, s: p.gemini_api(x, s),
    "anthropic_api": lambda p, x, s: p.anthropic_api(x, s),
}

POLICIES = {
    "auto": ["oroute_reason", "llama_completion", "local_openai", "ollama",
             "codex_cli", "gemini_cli", "claude_cli",
             "openai_api", "gemini_api", "anthropic_api"],
    "fast": ["oroute_fast", "llama_completion", "local_openai", "ollama",
             "gemini_cli", "gemini_api"],
    "reason": ["oroute_reason", "llama_completion", "codex_cli", "claude_cli",
               "openai_api", "gemini_cli", "gemini_api", "anthropic_api"],
    "code": ["codex_cli", "oroute_code", "claude_cli", "gemini_cli",
             "local_openai", "llama_completion", "openai_api"],
    "local": ["oroute_reason", "llama_completion", "local_openai", "ollama"],
    "omega": ["oroute_omega", "oroute_reason", "llama_completion"],
    "bridge": ["oroute_reason", "oroute_omega"],
    "gpt": ["codex_cli", "openai_api"],
    "openai": ["openai_api", "codex_cli"],
    "gemini": ["gemini_cli", "gemini_api"],
    "claude": ["claude_cli", "anthropic_api"],
}

def attempt_provider(provider: str, prompt: str, system: str = "") -> Attempt:
    method = PROVIDER_METHODS[provider]
    p = Providers()
    try:
        text = method(p, prompt, system)
        return Attempt(provider, True, text=text)
    except Exception as exc:
        return Attempt(provider, False, error=str(exc))

def create_agent_packet(task: str, context: dict | None = None,
                        mirrors: list[str] | None = None) -> dict:
    init_db()
    task_id = f"agent-{uuid.uuid4()}"
    packet = {
        "task_id": task_id,
        "created_at": now(),
        "status": "PENDING",
        "operator": "Dominique",
        "node_type": "supervised_agent_task",
        "task": task,
        "context": context or {},
        "source_boundary": (
            "Treat quoted/model-generated material as external source unless the "
            "Operator explicitly adopts it."
        ),
        "authority": {
            "allowed": ["research", "read configured sources", "draft", "analyze",
                        "create reviewable artifacts"],
            "requires_confirmation": ["send", "publish", "share", "purchase",
                                      "delete", "change permissions", "irreversible action"],
            "forbidden": ["reveal secrets", "bypass authorization",
                          "execute arbitrary model-generated shell text"],
        },
        "required_output": {
            "facts": True, "inferences": True, "unknowns": True,
            "sources": True, "actions_taken": True, "failures": True,
        },
    }
    packet["sha256"] = sha256_json(packet)
    path = AGENT_PENDING / f"{task_id}.json"
    path.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    with sqlite3.connect(DB) as con:
        con.execute(
            "INSERT INTO agent_tasks VALUES (?, ?, ?, ?, ?)",
            (task_id, packet["created_at"], "PENDING", str(path),
             json.dumps(packet, ensure_ascii=False, sort_keys=True)),
        )
        con.commit()
    mirror_results = []
    for lane in mirrors or []:
        mirror_results.append(mirror_path(path, lane))
    record = save_record({
        "record_type": "agent_task",
        "route": "agent",
        "provider": "agent_queue",
        "status": "queued",
        "task_id": task_id,
        "packet_path": str(path),
        "mirrors": mirror_results,
    })
    return {"packet": packet, "path": str(path), "mirrors": mirror_results,
            "record_id": record["record_id"]}

def mirror_path(path: Path, lane: str) -> dict:
    lane = lane.lower()
    mount_var = "OMEGA_GDRIVE_MOUNT" if lane == "drive" else "OMEGA_DROPBOX_MOUNT"
    remote_var = "OMEGA_GDRIVE_REMOTE" if lane == "drive" else "OMEGA_DROPBOX_REMOTE"
    mount = os.environ.get(mount_var, "").strip()
    remote = os.environ.get(remote_var, "").strip()
    if mount:
        dest = Path(mount).expanduser()
        dest.mkdir(parents=True, exist_ok=True)
        target = dest / path.name
        shutil.copy2(path, target)
        return {"lane": lane, "status": "copied", "target": str(target)}
    if remote and command_exists("rclone"):
        proc = subprocess.run(
            ["rclone", "copyto", str(path), f"{remote.rstrip('/')}/{path.name}"],
            text=True, capture_output=True, timeout=300, check=False
        )
        if proc.returncode == 0:
            return {"lane": lane, "status": "mirrored", "target": remote}
        return {"lane": lane, "status": "error",
                "error": (proc.stderr or proc.stdout).strip()}
    return {"lane": lane, "status": "not_configured"}

def route(prompt: str, route_name: str = "auto", system: str = "",
          case_id: str | None = None, context: dict | None = None) -> dict:
    route_name, prompt = parse_marker(prompt, route_name)
    if not prompt:
        raise ValueError("prompt is required")

    if route_name in {"agent", "drive", "dropbox"}:
        mirrors = []
        if route_name == "drive":
            mirrors = ["drive"]
        elif route_name == "dropbox":
            mirrors = ["dropbox"]
        return {
            "ok": True, "route": route_name, "queued": True,
            **create_agent_packet(prompt, context, mirrors)
        }

    if route_name in {"federate", "consensus"}:
        names = [
            "oroute_reason", "llama_completion", "local_openai", "ollama",
            "codex_cli", "gemini_cli", "claude_cli",
            "openai_api", "gemini_api", "anthropic_api",
        ]
        attempts = [attempt_provider(n, prompt, system) for n in names]
        outputs = [
            {"provider": a.provider, "text": a.text}
            for a in attempts if a.ok
        ]
        failures = [
            {"provider": a.provider, "error": a.error}
            for a in attempts if not a.ok
        ]
        status = "success" if outputs else "queued"
        queued = None
        if not outputs:
            queued = create_agent_packet(prompt, context)
        record = save_record({
            "record_type": "federated_response",
            "case_id": case_id,
            "route": route_name,
            "provider": "multi",
            "status": status,
            "prompt": prompt,
            "outputs": outputs,
            "failures": failures,
            "agent_fallback": queued,
        })
        return {
            "ok": bool(outputs), "route": route_name, "outputs": outputs,
            "failures": failures, "agent_fallback": queued,
            "record_id": record["record_id"],
            "note": (
                "Consensus is not silently manufactured. Independent outputs "
                "are preserved for operator or explicit judge review."
            ),
        }

    policy = POLICIES.get(route_name, POLICIES["auto"])
    attempts: list[Attempt] = []
    for provider in policy:
        result = attempt_provider(provider, prompt, system)
        attempts.append(result)
        if result.ok:
            record = save_record({
                "record_type": "model_response",
                "case_id": case_id,
                "route": route_name,
                "provider": provider,
                "status": "success",
                "prompt": prompt,
                "output": result.text,
                "attempts": [
                    {"provider": a.provider, "ok": a.ok, "error": a.error}
                    for a in attempts
                ],
            })
            return {
                "ok": True, "route": route_name, "provider": provider,
                "text": result.text, "attempts": record["attempts"],
                "record_id": record["record_id"],
            }

    queued = create_agent_packet(prompt, context)
    record = save_record({
        "record_type": "routing_failure",
        "case_id": case_id,
        "route": route_name,
        "provider": "agent_queue",
        "status": "queued",
        "prompt": prompt,
        "attempts": [
            {"provider": a.provider, "ok": False, "error": a.error}
            for a in attempts
        ],
        "agent_task_id": queued["packet"]["task_id"],
    })
    return {
        "ok": False, "route": route_name, "queued": True,
        "attempts": record["attempts"],
        "agent_task": queued, "record_id": record["record_id"],
    }

def hard_gate(senses: dict, abcde: dict, contradictions: list | None = None) -> dict:
    contradictions = contradictions or []
    values = list(abcde.values())
    missing = [k for k, v in abcde.items() if str(v).upper() == "MISSING"]
    unresolved = [
        k for k, v in abcde.items()
        if str(v).upper() in {"UNVERIFIED", "UNKNOWN"}
    ]
    if missing:
        return {"verdict": "HOLD", "movement": "DRY_RUN_ONLY",
                "reason": f"Required ABCDE gates missing: {', '.join(missing)}"}
    if contradictions:
        return {"verdict": "HOLD", "movement": "DRY_RUN_ONLY",
                "reason": "Contradictions remain unresolved."}
    if unresolved:
        return {"verdict": "UNKNOWN", "movement": "NO_IRREVERSIBLE_ACTION",
                "reason": f"Unresolved ABCDE gates: {', '.join(unresolved)}"}
    missing_senses = [
        k for k, v in senses.items() if str(v).upper() == "MISSING"
    ]
    if missing_senses:
        return {"verdict": "PARTIAL", "movement": "REVERSIBLE_ONLY",
                "reason": f"Missing sensory channels: {', '.join(missing_senses)}"}
    return {"verdict": "VERIFIED", "movement": "GATE_ELIGIBLE",
            "reason": "Required gates confirmed and no contradiction is open."}

def audit_claim(payload: dict) -> dict:
    senses = payload.get("senses", {})
    abcde = payload.get("abcde", {})
    required_senses = ["hearing", "sight", "touch", "smell", "taste"]
    required_letters = ["A", "B", "C", "D", "E"]
    normalized_senses = {
        k: str(senses.get(k, "MISSING")).upper() for k in required_senses
    }
    normalized_abcde = {
        k: str(abcde.get(k, "MISSING")).upper() for k in required_letters
    }
    result = hard_gate(
        normalized_senses, normalized_abcde,
        payload.get("contradictions", [])
    )
    ratings = {"STRONG": 3, "PARTIAL": 2, "WEAK": 1, "MISSING": 0,
               "CONFIRMED": 3, "UNVERIFIED": 1, "UNKNOWN": 1}
    score = sum(ratings.get(v, 0) for v in normalized_senses.values())
    score += sum(ratings.get(v, 0) for v in normalized_abcde.values())
    result["score"] = score
    result["max_score"] = 30
    result["percentage"] = round(score / 30 * 100, 2)
    result["senses"] = normalized_senses
    result["abcde"] = normalized_abcde
    record = save_record({
        "record_type": "aletheia_claim_audit",
        "case_id": payload.get("case_id"),
        "route": "audit",
        "provider": "local_hard_gate",
        "status": result["verdict"].lower(),
        "raw": payload,
        "result": result,
    })
    result["record_id"] = record["record_id"]
    return result

def read_inventory(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(path)
    out = []
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = re.sub(r"^\d+\s*[.)-]\s*", "", line)
        out.append(line.lower().removesuffix(".git").strip("/"))
    return sorted(set(out))

def audit_inventory(canonical_path: str, observed_path: str,
                    canary: str = "bekingdomcomejoker-cpu/glass-chess") -> dict:
    canonical = read_inventory(Path(canonical_path).expanduser())
    observed = read_inventory(Path(observed_path).expanduser())
    c, o = set(canonical), set(observed)
    missing = sorted(c - o)
    unexpected = sorted(o - c)
    result = {
        "canonical_count": len(c), "observed_count": len(o),
        "missing": missing, "unexpected": unexpected,
        "canary": canary, "canary_present": canary.lower() in o,
        "status": "COMPLETE" if not missing and not unexpected else "GAPS_DETECTED",
    }
    record = save_record({
        "record_type": "inventory_audit", "route": "inventory",
        "provider": "local_set_comparison",
        "status": result["status"].lower(), "result": result,
    })
    result["record_id"] = record["record_id"]
    return result

def load_voice_registry() -> dict:
    ensure_dirs()
    if not VOICE_REGISTRY.exists():
        VOICE_REGISTRY.write_text(
            json.dumps(DEFAULT_VOICE, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8"
        )
    try:
        data = json.loads(VOICE_REGISTRY.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def voice_resolve(phrase: str) -> dict:
    registry = load_voice_registry()
    key = phrase.strip().lower()
    if key in registry:
        item = registry[key]
        result = {"heard": phrase, "status": "CORRECTED",
                  "canonical": item.get("canonical")}
    else:
        init_db()
        stamp = now()
        with sqlite3.connect(DB) as con:
            con.execute(
                """INSERT OR IGNORE INTO unknown_voices
                   (phrase, normalized, status, canonical, created_at, updated_at)
                   VALUES (?, ?, 'UNKNOWN', NULL, ?, ?)""",
                (phrase, key, stamp, stamp),
            )
            con.commit()
        result = {"heard": phrase, "status": "UNKNOWN", "canonical": None,
                  "decision": "HOLD_FOR_OPERATOR"}
    save_record({
        "record_type": "voice_resolution", "route": "voice",
        "provider": "local_registry", "status": result["status"].lower(),
        "result": result,
    })
    return result

def count_text(path: str, expected: int, tokenizer: str = "whitespace") -> dict:
    p = Path(path).expanduser()
    raw = p.read_text(encoding="utf-8")
    if tokenizer == "whitespace":
        count = len([w for w in re.split(r"\s+", raw) if w])
    elif tokenizer == "word_regex":
        count = len(re.findall(r"[A-Za-z0-9']+", raw))
    else:
        raise ValueError("tokenizer must be whitespace or word_regex")
    result = {
        "path": str(p), "source_sha256": hashlib.sha256(raw.encode()).hexdigest(),
        "tokenizer": tokenizer, "count": count, "expected": int(expected),
        "passed": count == int(expected),
        "boundary": "This verifies this file and tokenizer only; it does not establish a universal edition count.",
    }
    save_record({
        "record_type": "text_count_verification", "route": "verification",
        "provider": "local_reproducible_counter",
        "status": "passed" if result["passed"] else "failed", "result": result,
    })
    return result
