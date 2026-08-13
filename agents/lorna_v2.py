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
    global CWD
    parts = user_input.strip().split(maxsplit=1)
    cmd = parts[0].lower() if parts else ""
    arg = parts[1] if len(parts) > 1 else ""

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
        resp = ollama.chat(model=model, messages=[{"role": "user", "content": user_input}])
        return resp['message']['content']
    except Exception as e:
        return f"Error: {e}"

# ===== Main =====
def main():
    global CURRENT_NODE, CWD
    print("[Ω] LORNA v2.0 — Tri-Node + Agent")
    print("    Commands: /quit, /node <fast|deep|code|agent>, /tools, /clear")
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
            print("  ls, cd, pwd, cat, write, cp, mv, rm --force, run, fetch, find, grep, df, free, ps, help")
            print("Type any of these to use them. Everything else goes to the model.")
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
