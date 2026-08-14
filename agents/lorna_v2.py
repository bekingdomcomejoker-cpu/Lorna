#!/usr/bin/env python3
# LORNA v2.0 — Tri-Node + Agent

import os
import sys
import subprocess
import json
import shutil
import ollama
import readline
from datetime import datetime
from pathlib import Path
try:
    from .benchmark_manager import command as benchmark_command
    from .vision_to_code import command as visual_code_command
    from .vision_bridge import command as vision_bridge_command
    from .moondream_image import command as moondream_image_command
except ImportError:
    from benchmark_manager import command as benchmark_command
    from vision_to_code import command as visual_code_command
    from vision_bridge import command as vision_bridge_command
    from moondream_image import command as moondream_image_command

# ===== Configuration =====
MODELS = {
    "fast": "smollm-fast",      # fast chat
    "deep": "deepseek-r1:1.5b", # reasoning
    "code": "tool-model",       # code/tool capable
    "agent": "tool-model"       # same as code but with tools
}

CURRENT_NODE = "fast"
CWD = "/sdcard"
if not os.path.exists(CWD):
    CWD = os.path.expanduser("~")

# ===== Integrated Drive Skills =====
SKILL_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "drive_skills")
INTEGRATED_SKILLS = {
    "manus-api": {
        "title": "Manus API Integration Guide",
        "path": "SKILL_1_manus_api.md",
    },
    "manus-config": {
        "title": "Manus Connector and Schedule Guide",
        "path": "SKILL_2_manus_config.md",
    },
    "mikrotik-hotspot-branding": {
        "title": "MikroTik Hotspot Branding",
        "path": "SKILL_3_mikrotik_hotspot_branding.md",
    },
    "skill-registry": {
        "title": "Repo 120 Skill Registry Source",
        "path": "skill_registry.py",
    },
}
ACTIVE_SKILL = None
SKILL_LIBRARY_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "skill_library")
TEXT_SKILL_SUFFIXES = {".md", ".py", ".json", ".txt", ".sh", ".yaml", ".yml"}

def library_skill_map():
    root = Path(SKILL_LIBRARY_DIRECTORY)
    entries = {}
    if not root.is_dir():
        return entries
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "manifest.json":
            continue
        relative_path = path.relative_to(root).as_posix()
        entries[f"library:{relative_path.lower()}"] = path
    return entries

def skill_file_path(skill_id):
    normalized_id = skill_id.lower()
    item = INTEGRATED_SKILLS.get(normalized_id)
    if item is not None:
        return Path(SKILL_DIRECTORY) / item["path"]
    return library_skill_map().get(normalized_id)

def list_integrated_skills():
    lines = ["Integrated Drive skills:"]
    for skill_id, item in INTEGRATED_SKILLS.items():
        marker = " [ACTIVE]" if skill_id == ACTIVE_SKILL else ""
        lines.append(f"  {skill_id:<28} {item['title']}{marker}")

    library_entries = library_skill_map()
    lines.append(f"\nCollected skill library ({len(library_entries)} resources):")
    for skill_id in library_entries:
        marker = " [ACTIVE]" if skill_id == ACTIVE_SKILL else ""
        lines.append(f"  {skill_id}{marker}")
    lines.append("Use /skill <id> to view text sources, /skill use <id> to activate, or /skill off to clear.")
    return "\n".join(lines)

def read_integrated_skill(skill_id):
    path = skill_file_path(skill_id)
    if path is None:
        return f"Unknown skill: {skill_id}. Use /skills to list available skills."
    if path.suffix.lower() not in TEXT_SKILL_SUFFIXES:
        return f"Stored binary skill archive: {path.name} ({path.stat().st_size} bytes). It is available in the skill library but is not rendered as prompt text."
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return f"Error reading skill {skill_id}: {exc}"

# ===== Tool Functions =====
def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout + result.stderr
    except Exception as e:
        return f"Error: {e}"

def expand_path(path):
    if path.startswith("/"):
        return path
    return os.path.join(CWD, path)

def execute_tool(user_input):
    global CWD, ACTIVE_SKILL
    parts = user_input.strip().split(maxsplit=1)
    cmd = parts[0].lower() if parts else ""
    arg = parts[1] if len(parts) > 1 else ""

    # Durable benchmark orchestration
    if cmd == "benchmark":
        return benchmark_command(arg)
    if cmd in {"visual-code", "vision-code"}:
        return visual_code_command(arg)
    if cmd in {"vision-bridge", "smol-moondream"}:
        return vision_bridge_command(arg)
    if cmd in {"moondream-image", "moon-image"}:
        return moondream_image_command(arg)

    # Integrated Drive skills
    if cmd == "skills":
        return list_integrated_skills()
    elif cmd == "skill":
        if not arg:
            return "Usage: skill <id> | skill use <id> | skill off"
        args = arg.split(maxsplit=1)
        if args[0].lower() == "use":
            if len(args) < 2:
                return "Usage: skill use <id>"
            skill_id = args[1].strip().lower()
            if skill_file_path(skill_id) is None:
                return f"Unknown skill: {skill_id}. Use skills to list available skills."
            ACTIVE_SKILL = skill_id
            return f"Activated skill: {skill_id}"
        if args[0].lower() == "off":
            ACTIVE_SKILL = None
            return "Cleared active skill."
        return read_integrated_skill(args[0].lower())

    # Navigation
    if cmd == "ls":
        target = arg if arg else CWD
        return run_cmd(f"ls -la {target}")
    elif cmd == "cd":
        new_path = expand_path(arg) if arg else os.path.expanduser("~")
        if os.path.isdir(new_path):
            CWD = new_path
            return f"Changed to {CWD}"
        else:
            return f"Directory not found: {new_path}"
    elif cmd == "pwd":
        return CWD

    # File ops
    elif cmd == "cat":
        if not arg:
            return "Usage: cat <file>"
        filepath = expand_path(arg)
        try:
            with open(filepath, 'r') as f:
                return f.read()
        except Exception as e:
            return f"Error: {e}"
    elif cmd == "write":
        if not arg:
            return "Usage: write <filename> <content>"
        parts = arg.split(maxsplit=1)
        if len(parts) < 2:
            return "Usage: write <filename> <content>"
        filename, content = parts[0], parts[1]
        filepath = expand_path(filename)
        try:
            with open(filepath, 'w') as f:
                f.write(content)
            return f"Written to {filepath}"
        except Exception as e:
            return f"Error: {e}"
    elif cmd == "cp":
        args = arg.split()
        if len(args) != 2:
            return "Usage: cp <source> <dest>"
        src, dst = expand_path(args[0]), expand_path(args[1])
        try:
            shutil.copy2(src, dst)
            return f"Copied {src} to {dst}"
        except Exception as e:
            return f"Error: {e}"
    elif cmd == "mv":
        args = arg.split()
        if len(args) != 2:
            return "Usage: mv <source> <dest>"
        src, dst = expand_path(args[0]), expand_path(args[1])
        try:
            shutil.move(src, dst)
            return f"Moved {src} to {dst}"
        except Exception as e:
            return f"Error: {e}"
    elif cmd == "rm":
        if not arg:
            return "Usage: rm --force <file>"
        if arg == "--force":
            return "Usage: rm --force <file>"
        target = arg.replace("--force", "").strip()
        if not target:
            return "Usage: rm --force <file>"
        filepath = expand_path(target)
        try:
            if os.path.isdir(filepath):
                shutil.rmtree(filepath)
            else:
                os.remove(filepath)
            return f"Removed {filepath}"
        except Exception as e:
            return f"Error: {e}"

    # Shell
    elif cmd == "run":
        return run_cmd(arg)
    # Web
    elif cmd == "fetch":
        if not arg:
            return "Usage: fetch <url>"
        try:
            import requests
            r = requests.get(arg, timeout=10)
            return r.text[:5000]
        except:
            return run_cmd(f"curl -sL {arg}")
    # Search
    elif cmd == "find":
        if not arg:
            return "Usage: find <pattern>"
        return run_cmd(f"find {CWD} -name '*{arg}*' -type f 2>/dev/null | head -50")
    elif cmd == "grep":
        if not arg:
            return "Usage: grep <pattern> [file]"
        parts = arg.split(maxsplit=1)
        if len(parts) == 1:
            return run_cmd(f"grep -r '{parts[0]}' {CWD} 2>/dev/null | head -50")
        else:
            pattern, filepath = parts[0], expand_path(parts[1])
            return run_cmd(f"grep '{pattern}' {filepath} 2>/dev/null")
    # System
    elif cmd == "df":
        return run_cmd("df -h")
    elif cmd == "free":
        return run_cmd("free -h")
    elif cmd == "ps":
        return run_cmd("ps aux | head -30")
    # Help
    elif cmd == "help":
        return """Available tools:
  ls [path]          list directory
  cd <path>          change directory
  pwd                show current directory
  cat <file>         show file content
  write <file> <text>  write text to file
  cp <src> <dst>     copy
  mv <src> <dst>     move/rename
  rm --force <file>  remove (careful)
  run <command>      execute shell command
  fetch <url>        get web page content
  find <pattern>     find files by name
  grep <pattern> [file]  search inside files
  df                 disk usage
  free               memory info
  ps                 process list
  help               show this help
"""
    else:
        return None  # not a tool command

def chat_with_node(user_input):
    model = MODELS[CURRENT_NODE]
    try:
        prompt = user_input
        if ACTIVE_SKILL:
            prompt = (
                f"Use the following active skill as your operating context. "
                f"Skill ID: {ACTIVE_SKILL}\n\n"
                f"{read_integrated_skill(ACTIVE_SKILL)}\n\n"
                f"User request: {user_input}"
            )
        resp = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}])
        return resp['message']['content']
    except Exception as e:
        return f"Error: {e}"

# ===== Main =====
def main():
    global CURRENT_NODE, CWD, ACTIVE_SKILL
    print("[Ω] LORNA v2.0 — Tri-Node + Agent")
    print("    Commands: /quit, /node <fast|deep|code|agent>, /tools, /skills, /skill, /benchmark, /visual-code, /vision-bridge, /moondream-image, /clear")
    print(f"    Current node: {CURRENT_NODE}")
    print(f"    Current directory: {CWD}")

    while True:
        try:
            user_input = input(f"\n{CWD}> ")
        except KeyboardInterrupt:
            print("\nExiting.")
            break

        if user_input.lower() in ["/quit", "/exit"]:
            break
        elif user_input.startswith("/node"):
            parts = user_input.split()
            if len(parts) > 1:
                node = parts[1].lower()
                if node in MODELS:
                    CURRENT_NODE = node
                    print(f"Switched to {CURRENT_NODE}")
                else:
                    print(f"Invalid node. Choose from: {', '.join(MODELS.keys())}")
            else:
                print(f"Current node: {CURRENT_NODE}")
        elif user_input == "/tools":
            print("Available tool commands:")
            print("  benchmark, visual-code, vision-bridge, moondream-image, skills, skill, ls, cd, pwd, cat, write, cp, mv, rm --force, run, fetch, find, grep, df, free, ps, help")
            print("  Benchmark: /benchmark status | profiles | sweep <model> [core|runtime|sampling] | apply <model> | optimize <model|all> | active <model> | rollback <model> | memory")
            print("  Moondream image: /moondream-image <image> [question] (prepared image, direct Moondream2 projector path; no HTML)")
            print("  Vision bridge: /vision-bridge <image> [question] (SmolVLM then text-only Moondream2, sequentially; no HTML)")
            print("  Vision-to-code: /visual-code <image> [output-file] (legacy SmolVLM then DeepSeek-Coder path)")
            print("  Skill IDs can be built-in names such as manus-api or library:<source>/<path>.")
            print("Type any of these to use them. Everything else goes to the model.")
        elif user_input == "/skills":
            print(list_integrated_skills())
        elif user_input.startswith("/skill"):
            parts = user_input.split(maxsplit=2)
            if len(parts) == 1:
                print("Usage: /skill <id> | /skill use <id> | /skill off")
            elif parts[1].lower() == "use":
                if len(parts) < 3:
                    print("Usage: /skill use <id>")
                else:
                    skill_id = parts[2].strip().lower()
                    if skill_file_path(skill_id) is None:
                        print(f"Unknown skill: {skill_id}. Use /skills to list available skills.")
                    else:
                        ACTIVE_SKILL = skill_id
                        print(f"Activated skill: {skill_id}")
            elif parts[1].lower() == "off":
                ACTIVE_SKILL = None
                print("Cleared active skill.")
            else:
                print(read_integrated_skill(parts[1].lower()))
        elif user_input.startswith("/benchmark"):
            print(benchmark_command(user_input[len("/benchmark"):].strip()))
        elif user_input.startswith("/visual-code") or user_input.startswith("/vision-code"):
            if user_input.startswith("/visual-code"):
                argument = user_input[len("/visual-code"):].strip()
            else:
                argument = user_input[len("/vision-code"):].strip()
            print(visual_code_command(argument))
        elif user_input.startswith("/vision-bridge") or user_input.startswith("/smol-moondream"):
            if user_input.startswith("/vision-bridge"):
                argument = user_input[len("/vision-bridge"):].strip()
            else:
                argument = user_input[len("/smol-moondream"):].strip()
            print(vision_bridge_command(argument))
        elif user_input.startswith("/moondream-image") or user_input.startswith("/moon-image"):
            if user_input.startswith("/moondream-image"):
                argument = user_input[len("/moondream-image"):].strip()
            else:
                argument = user_input[len("/moon-image"):].strip()
            print(moondream_image_command(argument))
        elif user_input == "/clear":
            os.system("clear")
        else:
            # Try to execute as a tool if in agent mode, else fallback to chat
            if CURRENT_NODE == "agent":
                tool_result = execute_tool(user_input)
                if tool_result is not None:
                    print(tool_result)
                    continue
            # If not a tool or not in agent mode, chat
            reply = chat_with_node(user_input)
            print(reply)

if __name__ == "__main__":
    main()
