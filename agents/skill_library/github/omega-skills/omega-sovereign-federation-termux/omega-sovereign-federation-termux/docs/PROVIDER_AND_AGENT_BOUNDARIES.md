# Provider, subscription, connector and Agent boundaries

## ChatGPT / OpenAI

- OpenAI API access uses an API key and the Responses API.
- A ChatGPT plan is separate from API billing.
- Codex CLI can authenticate using a ChatGPT account on eligible plans.
- The federation therefore supports both:
  - `codex exec` for authenticated local subscription-backed work;
  - OpenAI Responses API when an API key is configured.

## Gemini

- Gemini CLI can sign in with Google and run non-interactively.
- Gemini API uses a separate API key.
- Both paths are supported.

## Claude

- Claude Code CLI can authenticate with a Claude subscription or Console
  account and supports print mode.
- Anthropic API access is a separate metered path.
- Both paths are supported.

## ChatGPT Agent Mode

A personal ChatGPT Agent Mode session is a supervised product surface, not a
generic local REST endpoint. The federation therefore creates an Agent Task
Packet containing:

- task;
- context;
- source boundaries;
- permitted actions;
- prohibited actions;
- required outputs;
- completion conditions;
- attachments;
- hashes and timestamps.

Packets are stored locally and may be mirrored to Google Drive or Dropbox. They
can then be brought into Agent Mode with the required connectors enabled.

An optional generic webhook is supported for a workspace/custom agent endpoint
that the operator explicitly configures.

## Google Drive and Dropbox

The local runtime cannot silently inherit the ChatGPT app's connector
credentials. Local integration uses an operator-configured mount, sync tool,
`rclone`, or custom agent/webhook. ChatGPT Agent Mode can separately use enabled
apps under its own confirmation and safety controls.
