# Integrated Drive Skills

Lorna2 now ships four Drive-sourced skill resources under `agents/drive_skills/`. Their source contents are included verbatim. They can be read from the REPL and attached as active context for the selected local model.

## Commands

```text
/skills
/skill <id>
/skill use <id>
/skill off
```

The `skill` command is also available while using the `agent` node:

```text
skills
skill <id>
skill use <id>
skill off
```

`/skill <id>` displays the stored source. `/skill use <id>` selects that source as the active context for later model prompts. `/skill off` removes the active context. The active skill is marked in `/skills` output.

## Included resources

| Skill ID | Stored source | Purpose declared by its source |
|---|---|---|
| `manus-api` | `SKILL_1_manus_api.md` | Manus API task, project, connector, skill, and OAuth integration guide. |
| `manus-config` | `SKILL_2_manus_config.md` | Connector, project configuration, and scheduling guide. |
| `mikrotik-hotspot-branding` | `SKILL_3_mikrotik_hotspot_branding.md` | MikroTik Hotspot captive-portal design and deployment guide. |
| `skill-registry` | `skill_registry.py` | Repo 120 governed skill-registry source. |

## Launch

```bash
cd "$HOME/Lorna"
python3 -m pip install -r agents/requirements.txt
bash ./lorna.sh agent2
```

Then select an integrated skill:

```text
/skills
/skill use manus-api
Explain how to create a task with structured output.
```

## External services

The local Lorna2 console reads and supplies these packaged skill sources to the chosen local model. The documents may describe remote services such as the Manus API, external connectors, Google Drive, or MikroTik routers. Using such services requires the relevant service endpoint, account authorization, network access, and credentials to be configured in the environment where the action is performed.

The included `skill-registry.py` is available as source through `skill-registry`; it is not automatically imported by Lorna2 and has its own dependency on `audit_log.py` when used as a standalone Python module.
