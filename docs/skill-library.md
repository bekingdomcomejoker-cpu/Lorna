# Lorna2 Complete Skill Library

Lorna2 includes a collected skill library at `agents/skill_library/`. This library keeps the original source material available alongside the built-in Drive skills in `agents/drive_skills/`.

## Sources

| Library root | Contents |
|---|---|
| `drive/` | Direct Drive resources discovered through the skill inventory. `manifest.json` records their Drive IDs, source URLs, types, and download status. |
| `drive_folders/` | Every file recursively collected from the five remaining Drive skill folders. `collection_manifest.json` records the source IDs and relative paths. |
| `omnipc/` | Skill and code resources from the `OMNI PC` and `OMNI PC (1)` Google Drive Skills folders. `manifest.json` records their source folder and Drive IDs. |
| `github/omega-skills/` | Full working-tree copy of the public `bekingdomcomejoker-cpu/omega-skills` repository, excluding its Git metadata. |
| `termux/` | `SKILL.md` documents collected from the connected device’s `omega-skills`, `omega/dropbox`, and Gemini CLI skill locations. |

The library includes text documents, Python modules, shell scripts, and archive formats. Text resources can be viewed and used as active Lorna2 model context. Archive files remain stored in the library and are reported by the console as binary resources.

## Lorna2 commands

```text
/skills
/skill <id>
/skill use <id>
/skill off
```

The `/skills` command lists the original four built-in Drive skills and every collected library resource. A library ID begins with `library:` and uses a lower-case path relative to `agents/skill_library/`.

```text
/skill use library:github/omega-skills/manus-api/skill.md
/skill use library:termux/gemini-cli/.gemini/skills/docs-writer/skill.md
/skill use library:omnipc/population_intelligence_model.py
```

When a text resource is active, its exact stored text is supplied to the selected local model along with the next user request. `/skill off` removes that active context.

## Updating the library

The Drive, recursive Drive-folder, and OmniPC source manifests preserve Drive IDs and paths for source tracking. The public GitHub source is tracked as a repository snapshot. The Termux source preserves the original source-directory layout below `termux/`.
