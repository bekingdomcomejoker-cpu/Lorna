#!/usr/bin/env python3
"""LORNA v2 + Home Assistant MCP interactive launcher.

This keeps the existing LORNA v2 model selection and adds Home Assistant's
native MCP Server as an external tool source. Configure LORNA_HA_MCP_URL and
LORNA_HA_TOKEN in the environment before starting.
"""

import os
import sys

try:
    from .lorna_v2 import MODELS, read_integrated_skill
    from .mcp_bridge import chat_with_mcp, mcp_status
except ImportError:
    from lorna_v2 import MODELS, read_integrated_skill
    from mcp_bridge import chat_with_mcp, mcp_status

MODEL = os.environ.get("LORNA_MCP_MODEL", MODELS.get("agent", "tool-model"))

SYSTEM = """You are LORNA 2, a local voice/agent assistant.
You have access to Home Assistant through MCP tools.
Use Home Assistant tools when the user asks about or wants to control their
home. Do not claim an action happened unless the MCP tool reports success.
Prefer read-only state queries before destructive or broad actions.
"""


def main():
    global MODEL
    print("[Ω] LORNA v2 — Home Assistant MCP mode")
    print(f"    Model: {MODEL}")
    print(f"    MCP URL: {os.environ.get('LORNA_HA_MCP_URL', 'http://homeassistant:8123/api/mcp')}")
    print("    Commands: /status, /model <name>, /quit")
    print("")

    while True:
        try:
            text = input("LORNA> ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break
        if not text:
            continue
        if text.lower() in {"/quit", "/exit"}:
            break
        if text.lower() == "/status":
            print(mcp_status())
            continue
        if text.startswith("/model "):
            candidate = text.split(None, 1)[1].strip()
            if candidate in MODELS.values():
                MODEL = candidate
                print(f"Model: {MODEL}")
            else:
                print("Unknown model. Available configured models: " + ", ".join(sorted(set(MODELS.values()))))
            continue

        print(chat_with_mcp(text, MODEL, SYSTEM))


if __name__ == "__main__":
    main()
