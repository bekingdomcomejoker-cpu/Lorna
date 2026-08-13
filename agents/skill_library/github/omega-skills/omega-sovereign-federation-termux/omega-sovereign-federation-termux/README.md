# Ω OMEGA Sovereign Federation — Termux

A local-first, provider-neutral control plane for Dominique Snyman's
OMEGA · ALETHEIA Perception Integrity system.

This package replaces the Claude-only proxy with a federation router:

```text
Termux / local trigger / browser dashboard
    ↓
OMEGA router
    ├── existing `oroute` / Omega Bridge
    ├── local llama.cpp endpoint
    ├── local Ollama endpoint
    ├── Codex CLI authenticated with ChatGPT
    ├── Gemini CLI authenticated with Google
    ├── Claude Code CLI authenticated with Claude
    ├── OpenAI Responses API
    ├── Gemini generateContent API
    ├── Anthropic Messages API
    ├── generic agent webhook
    └── Agent Queue → Google Drive / Dropbox mirror
    ↓
Sovereign Bus + SQLite + JSONL + final witness packets
```

## What this does not pretend

- A personal ChatGPT Agent Mode session is not exposed as a normal API endpoint.
  The router creates a sealed Agent Task Packet and mirrors it to the configured
  queue, Drive, and/or Dropbox lane.
- Consumer subscriptions are not raw API keys.
  Where official authenticated CLIs support subscription/login use, the router
  calls those CLIs locally.
- Provider models do not own memory. The local SQLite/JSONL ledger does.
- Model output is never executed as arbitrary shell code.

## Install in Termux

```bash
cd ~/storage/downloads
unzip -o OMEGA_SOVEREIGN_FEDERATION_TERMUX.zip
cd omega-sovereign-federation-termux
bash scripts/install-termux.sh
```

The installer preserves the existing `~/cat_eof` body and installs under:

```text
~/cat_eof/apps/omega-sovereign-federation
```

Command:

```text
~/cat_eof/tools/omega-federation
```

## Start

```bash
omega-federation serve start
omega-federation serve status
```

Open:

```text
http://127.0.0.1:8765
```

## Core CLI

```bash
omega-federation status
omega-federation route auto "Explain this claim"
omega-federation route reason "Audit this contradiction"
omega-federation route code "Review this function"
omega-federation route federate "Ask every available node independently"
omega-federation agent "Research this using Agent Mode and connected sources"
omega-federation ledger 20
omega-federation self-test
```

Markers are also accepted inside prompts:

```text
@fast @reason @code @local @omega @bridge @beehive
@gpt @openai @gemini @claude @agent @drive @dropbox
@federate @consensus
```

## Subscription-backed local CLIs

The router detects these commands when installed and authenticated:

```text
codex   → ChatGPT/Codex login
gemini  → Google OAuth or Gemini API authentication
claude  → Claude Code login
```

No credentials are placed in browser JavaScript.

## API-backed routes

Configure keys with:

```bash
omega-federation configure
```

Or copy:

```text
~/cat_eof/secrets/federation.env.example
```

to:

```text
~/cat_eof/secrets/federation.env
```

and restrict it:

```bash
chmod 600 ~/cat_eof/secrets/federation.env
```

## Existing Omega integration

The router checks for:

- `oroute`
- `omega_router_v5.2.py`
- `omega_bridge_adapter.py`
- `~/cat_eof/cat_bus.jsonl`
- `~/cat_eof/comm_bus.jsonl`
- `127.0.0.1:8080/completion`
- `127.0.0.1:8080/v1/chat/completions`
- Ollama on `127.0.0.1:11434`

It integrates what exists and does not overwrite it.

## Drive and Dropbox

The Termux runtime can mirror agent packets and exports through:

1. configured local mount/sync directories; or
2. `rclone` remotes.

Example environment:

```bash
export OMEGA_GDRIVE_REMOTE='gdrive:OMEGA_DEPLOYMENT/06_RUNTIME/AGENT_QUEUE'
export OMEGA_DROPBOX_REMOTE='dropbox:OMEGA_120_REPO_PACK/AGENT_QUEUE'
```

The authenticated ChatGPT connectors remain available inside ChatGPT/Agent Mode;
the local router's durable handoff is the sealed packet.

## Truth boundary

The Five-Sense audit includes:

- Hearing
- Sight
- Touch
- Smell
- Taste

ABCDE is a hard gate. A missing required gate cannot be averaged into VERIFIED.

`7^7` verification is implemented only as a reproducible local text-count
operation with an explicitly supplied expected value and tokenizer. The package
does not claim that 823,543 is the KJV word count.

See `docs/ARCHITECTURE.md`, `docs/CLAUDE_DRAFT_AUDIT.md`, and
`docs/PROVIDER_AND_AGENT_BOUNDARIES.md`.
