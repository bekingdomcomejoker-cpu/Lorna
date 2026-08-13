#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from federation.core import (
    APP, BASE, audit_claim, audit_inventory, count_text,
    create_agent_packet, ledger, route, voice_resolve, Providers,
)

PID = BASE / "state" / "omega-federation.pid"
LOG = BASE / "state" / "omega-federation.log"
ENV = BASE / "secrets" / "federation.env"

def load_env():
    if not ENV.exists():
        return
    for raw in ENV.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:]
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip("'").strip('"')
        value = value.replace("$HOME", str(Path.home()))
        os.environ.setdefault(key.strip(), value)

def print_json(value):
    print(json.dumps(value, indent=2, ensure_ascii=False))

def serve(action):
    if action == "start":
        if PID.exists():
            try:
                pid = int(PID.read_text().strip())
                os.kill(pid, 0)
                print(f"Already running: PID {pid}")
                return
            except Exception:
                PID.unlink(missing_ok=True)
        LOG.parent.mkdir(parents=True, exist_ok=True)
        h = LOG.open("a", encoding="utf-8")
        proc = subprocess.Popen(
            [sys.executable, str(APP / "federation" / "server.py")],
            cwd=str(APP), stdout=h, stderr=subprocess.STDOUT,
            start_new_session=True, env=os.environ.copy(),
        )
        PID.write_text(str(proc.pid))
        print(f"Started PID {proc.pid}")
        print("Open http://127.0.0.1:8765")
    elif action == "stop":
        if not PID.exists():
            print("Not running")
            return
        pid = int(PID.read_text().strip())
        try:
            os.kill(pid, 15)
        except ProcessLookupError:
            pass
        PID.unlink(missing_ok=True)
        print("Stopped")
    elif action == "status":
        if PID.exists():
            try:
                pid = int(PID.read_text().strip())
                os.kill(pid, 0)
                print(f"RUNNING PID {pid}")
                return
            except Exception:
                PID.unlink(missing_ok=True)
        print("OFFLINE")
    elif action == "log":
        if LOG.exists():
            print("\n".join(LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-100:]))
        else:
            print("No log")
    elif action == "foreground":
        os.execv(sys.executable, [sys.executable, str(APP / "federation" / "server.py")])

def configure():
    ENV.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if ENV.exists():
        for line in ENV.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.removeprefix("export ").split("=", 1)
                existing[k.strip()] = v.strip().strip("'").strip('"')
    fields = [
        ("OPENAI_API_KEY", "OpenAI API key (blank keeps disabled)"),
        ("GEMINI_API_KEY", "Gemini API key (blank keeps disabled)"),
        ("ANTHROPIC_API_KEY", "Anthropic API key (blank keeps disabled)"),
        ("OLLAMA_MODEL", "Ollama model name (blank keeps disabled)"),
        ("OMEGA_GDRIVE_MOUNT", "Google Drive local sync/mount path"),
        ("OMEGA_DROPBOX_MOUNT", "Dropbox local sync/mount path"),
        ("OMEGA_GDRIVE_REMOTE", "rclone Google Drive remote"),
        ("OMEGA_DROPBOX_REMOTE", "rclone Dropbox remote"),
        ("OMEGA_AGENT_WEBHOOK_URL", "Optional custom/workspace agent webhook"),
        ("OMEGA_AGENT_WEBHOOK_TOKEN", "Optional agent webhook token"),
    ]
    values = dict(existing)
    for key, label in fields:
        old = values.get(key, "")
        shown = "configured" if old and "KEY" in key or "TOKEN" in key and old else old
        raw = input(f"{label} [{shown}]: ").strip()
        if raw:
            values[key] = raw
    lines = ["# OMEGA Sovereign Federation secrets and local routes"]
    for key, value in values.items():
        safe = value.replace("'", "'\"'\"'")
        lines.append(f"export {key}='{safe}'")
    ENV.write_text("\n".join(lines) + "\n")
    ENV.chmod(0o600)
    print(f"Saved securely: {ENV}")

def main():
    load_env()
    ap = argparse.ArgumentParser(prog="omega-federation")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status")
    p = sub.add_parser("route")
    p.add_argument("route")
    p.add_argument("prompt", nargs="+")
    p.add_argument("--system", default="")
    p.add_argument("--case-id")

    p = sub.add_parser("agent")
    p.add_argument("task", nargs="+")
    p.add_argument("--drive", action="store_true")
    p.add_argument("--dropbox", action="store_true")

    p = sub.add_parser("ledger")
    p.add_argument("limit", type=int, nargs="?", default=20)

    p = sub.add_parser("voice")
    p.add_argument("phrase", nargs="+")

    p = sub.add_parser("inventory")
    p.add_argument("canonical")
    p.add_argument("observed")
    p.add_argument("--canary", default="bekingdomcomejoker-cpu/glass-chess")

    p = sub.add_parser("audit-claim")
    p.add_argument("json_file")

    p = sub.add_parser("count")
    p.add_argument("path")
    p.add_argument("expected", type=int)
    p.add_argument("--tokenizer", default="whitespace")

    p = sub.add_parser("serve")
    p.add_argument("action", choices=["start", "stop", "status", "log", "foreground"])

    sub.add_parser("configure")
    sub.add_parser("self-test")

    args = ap.parse_args()
    if args.cmd == "status":
        print_json({"base": str(BASE), "providers": Providers().status()})
    elif args.cmd == "route":
        print_json(route(" ".join(args.prompt), args.route, args.system, args.case_id))
    elif args.cmd == "agent":
        mirrors = []
        if args.drive: mirrors.append("drive")
        if args.dropbox: mirrors.append("dropbox")
        print_json(create_agent_packet(" ".join(args.task), mirrors=mirrors))
    elif args.cmd == "ledger":
        print_json(ledger(args.limit))
    elif args.cmd == "voice":
        print_json(voice_resolve(" ".join(args.phrase)))
    elif args.cmd == "inventory":
        print_json(audit_inventory(args.canonical, args.observed, args.canary))
    elif args.cmd == "audit-claim":
        print_json(audit_claim(json.loads(Path(args.json_file).read_text())))
    elif args.cmd == "count":
        print_json(count_text(args.path, args.expected, args.tokenizer))
    elif args.cmd == "serve":
        serve(args.action)
    elif args.cmd == "configure":
        configure()
    elif args.cmd == "self-test":
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", str(APP/"tests"), "-v"],
            cwd=str(APP)
        )
        raise SystemExit(result.returncode)

if __name__ == "__main__":
    main()
