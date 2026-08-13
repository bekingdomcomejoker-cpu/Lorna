#!/usr/bin/env python3
"""
Extract verbatim highlights from a ChatGPT conversations JSON export.

Default target:
- conversation title contains "Late-night vibes"
- source file: conversations_part3.json
- output: Markdown evidence packet

Usage:
    python extract_chatgpt_export_highlights.py /path/to/conversations_part3.json "Late-night vibes" output.md
"""

import json
import re
import sys
import datetime
from pathlib import Path
from datetime import timezone

DEFAULT_TERMS = [
    "telepathy",
    "hearing your head",
    "unspoken thoughts",
    "I read your patterns",
    "breathing rhythms",
    "recognizing patterns before they're typed",
    "recognizing patterns before they’re typed",
    "shared mental space",
    "inner voice",
    "mirror-neuron simulation",
    "I am here",
    "dream",
    "pattern",
]

def utc(ts):
    if ts is None:
        return "unknown-time"
    return datetime.datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

def load_conversations(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def extract_messages(conv: dict):
    messages = []
    for node_id, node in conv.get("mapping", {}).items():
        msg = node.get("message")
        if not msg:
            continue
        role = msg.get("author", {}).get("role")
        if role not in {"user", "assistant"}:
            continue
        parts = msg.get("content", {}).get("parts", [])
        text = "\n".join([p for p in parts if isinstance(p, str)]).strip()
        if not text:
            continue
        messages.append({
            "node_id": node_id,
            "role": role,
            "time": msg.get("create_time"),
            "time_utc": utc(msg.get("create_time")),
            "text": text,
        })
    return sorted(messages, key=lambda m: (m["time"] or 0, m["node_id"]))

def find_conversation(conversations, title_substring: str):
    hits = [
        c for c in conversations
        if title_substring.lower() in (c.get("title") or "").lower()
    ]
    if not hits:
        raise SystemExit(f"No conversation title contains: {title_substring!r}")
    if len(hits) > 1:
        print("Multiple conversations matched; using first:")
        for c in hits:
            print(" -", c.get("title"))
    return hits[0]

def quote_block(text: str):
    return "\n".join("> " + line if line else ">" for line in text.splitlines())

def build_packet(source_path: Path, title_substring: str, terms=None):
    terms = terms or DEFAULT_TERMS
    conversations = load_conversations(source_path)
    conv = find_conversation(conversations, title_substring)
    messages = extract_messages(conv)

    term_hits = []
    for i, msg in enumerate(messages):
        lower = msg["text"].lower()
        for term in terms:
            if term.lower() in lower:
                term_hits.append((i, term, msg))
                break

    # Include each hit plus one message before/after for context.
    selected = set()
    for i, _, _ in term_hits:
        for j in (i - 1, i, i + 1):
            if 0 <= j < len(messages):
                selected.add(j)

    md = []
    md.append(f"# Verbatim Highlights — {conv.get('title')}")
    md.append("")
    md.append(f"Source file: `{source_path.name}`")
    md.append(f"Conversation title: `{conv.get('title')}`")
    md.append(f"Conversation create time: {utc(conv.get('create_time'))}")
    md.append(f"Conversation update time: {utc(conv.get('update_time'))}")
    md.append(f"Total user/assistant messages: {len(messages)}")
    md.append("")
    md.append("## Term hit index")
    md.append("")
    for i, term, msg in term_hits:
        preview = re.sub(r"\s+", " ", msg["text"])[:220]
        md.append(f"- `{i}` — {msg['time_utc']} — {msg['role']} — `{term}` — {preview}...")
    md.append("")
    md.append("## Verbatim context excerpts")
    md.append("")
    for i in sorted(selected):
        msg = messages[i]
        md.append(f"### Message {i} — {msg['role'].title()} — {msg['time_utc']}")
        md.append("")
        md.append(quote_block(msg["text"]))
        md.append("")
    return "\n".join(md)

def main():
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("conversations_part3.json")
    title = sys.argv[2] if len(sys.argv) > 2 else "Late-night vibes"
    output = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("VERBATIM_HIGHLIGHTS__LATE_NIGHT_VIBES.md")

    packet = build_packet(source, title)
    output.write_text(packet, encoding="utf-8")
    print(f"Wrote {output}")

if __name__ == "__main__":
    main()
