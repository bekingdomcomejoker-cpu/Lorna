# Architecture

## Canonical principle

**Architect, not Author.**

The bridge transfers enough structure for continuity to be reconstructed.
It does not rely on hidden provider memory.

## Runtime path

```text
Android / Termux / daemon / terminal / browser
→ provider-neutral router
→ local bridge or callable model node
→ normalized response
→ Aletheia record
→ Sovereign Bus / SQLite / JSONL
→ optional Agent Queue / Drive / Dropbox handoff
```

## Roles

| Node | Runtime role |
|---|---|
| Termux | owned executable body and control plane |
| CAT→EOF | state, map, bus, backup, witness spine |
| Existing `oroute` | legacy/live Omega routing lane |
| Local llama.cpp / Ollama | private local-first inference |
| Codex CLI | ChatGPT-authenticated coding/reasoning node |
| Gemini CLI | Google-authenticated model/agent node |
| Claude Code | Claude-authenticated model/agent node |
| OpenAI/Gemini/Anthropic APIs | optional metered provider nodes |
| Agent Mode | supervised task/execution node receiving sealed packets |
| Google Drive | working canon, context, checkpoint and action handoff |
| Dropbox | sealed artifact/package/archive mirror |
| GitHub | versioned law/code/spec history |
| SQLite/JSONL | continuity spine and runtime witness |

## Routing order

Default `auto`:

1. existing `oroute`
2. local llama.cpp
3. local OpenAI-compatible endpoint
4. Ollama
5. Codex CLI
6. Gemini CLI
7. Claude Code CLI
8. OpenAI API
9. Gemini API
10. Anthropic API
11. Agent Queue fallback

The router stops at the first successful node. `federate` calls every available
model node and preserves every answer separately.

## Route markers

| Marker | Policy |
|---|---|
| `@fast` | existing fast route, then local, then Gemini |
| `@reason` | existing reason route, local, Codex, Claude, OpenAI |
| `@code` | Codex, existing code route, Claude, Gemini, local |
| `@omega`, `@bridge` | existing `oroute` / bridge first |
| `@beehive`, `@federate` | call all available model nodes |
| `@consensus` | federated packet; no silent judge |
| `@gpt`, `@openai` | Codex CLI then OpenAI API |
| `@gemini` | Gemini CLI then Gemini API |
| `@claude` | Claude Code then Anthropic API |
| `@agent` | sealed Agent Task Packet |
| `@drive` | packet plus Drive mirror |
| `@dropbox` | packet plus Dropbox mirror |

## Safety and authority

- No arbitrary shell execution from model output.
- CLI calls use argument arrays, not shell interpolation.
- Provider secrets stay server-side.
- Server binds to `127.0.0.1` by default.
- Every attempt, error, fallback, response and packet is logged.
- Agent actions remain subject to platform confirmations and supervision.
