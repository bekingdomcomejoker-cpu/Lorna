# Lorna2 Agent Mode

Lorna2 Agent Mode combines the existing Bash and `llama-cli` orchestration menu with a lightweight, **local-only** Python and Ollama console. It is launched from the Lorna menu with option `15`, or directly with:

```bash
lorna agent2
```

The aliases `lorna agent` and `lorna lorna2` are equivalent.

## Prerequisites

Agent mode requires the following components on the Android or Termux device.

| Component | Purpose | Check |
|---|---|---|
| Python 3 | Runs the agent console | `python3 --version` |
| Ollama Python package | Connects the console to local Ollama | `python3 -c 'import ollama'` |
| Local Ollama service | Serves the model aliases | `ollama list` |
| Model aliases | Supplies the four agent nodes | See the table below |

Install the Python dependency from the repository root:

```bash
python3 -m pip install -r agents/requirements.txt
```

The agent expects these aliases to be available in the local Ollama installation.

| Node | Expected alias | Intended use |
|---|---|---|
| `fast` | `smollm-fast` | Fast chat |
| `deep` | `deepseek-r1:1.5b` | Reasoning-oriented chat |
| `code` | `tool-model` | Code-oriented chat |
| `agent` | `tool-model` | Interactive local tools |

Model weights and Ollama state are deliberately **not** stored in this repository. Create or adapt aliases for the models installed on your own device.

## Using the agent

Start Lorna, select option `15`, then use `/node` to choose a node:

```text
/node fast
/node deep
/node code
/node agent
```

The agent starts in `/sdcard` when that location is available, otherwise it starts in the Termux home directory. In `agent` mode, it recognizes local commands such as `ls`, `cd`, `cat`, `write`, `cp`, `mv`, `rm --force`, `run`, `fetch`, `find`, `grep`, `df`, `free`, and `ps`. Use `/tools` inside the console to display the command list and `/exit` to leave it.

## Safety boundary

> Agent mode is intended only for an interactive session on a device you control. Its `run` command can execute shell commands, and `rm --force` can delete files. Do not expose this program through a web server, public tunnel, chat bot, or any network-facing service without adding strict authentication, authorization, input validation, and filesystem restrictions.

The agent source is in `agents/lorna_v2.py`. The launcher uses that tracked repository copy rather than a private `~/.lorna_v2` installation, which makes a clean clone reproducible without committing device-specific configuration.

## Integrated Drive skills

The agent includes four Drive-sourced resources as selectable model contexts. Use `/skills` to list them and `/skill use <id>` to activate one. See [Integrated Drive Skills](drive-skills.md) for the complete command reference, included source files, and external-service requirements.
