"""
File Manager Skill
Allows the agent to read, write, and list files.
"""

import os
from pathlib import Path
from typing import Dict, Any, List


def skill(action: str, path: str = "", content: str = "") -> Dict[str, Any]:
    """
    Manage files on the local system.

    Args:
        action: One of 'read', 'write', 'list', 'delete'
        path: File or directory path
        content: Content to write (for 'write' action)

    Returns:
        Dictionary with operation result
    """
    try:
        path_obj = Path(path).expanduser()

        if action == "read":
            if not path_obj.exists():
                return {"error": f"File not found: {path}"}
            if not path_obj.is_file():
                return {"error": f"Not a file: {path}"}

            with open(path_obj, "r", encoding="utf-8") as f:
                content = f.read()
            return {"action": "read", "path": str(path_obj), "content": content}

        elif action == "write":
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            with open(path_obj, "w", encoding="utf-8") as f:
                f.write(content)
            return {
                "action": "write",
                "path": str(path_obj),
                "status": "success",
                "size": len(content),
            }

        elif action == "list":
            if not path_obj.exists():
                return {"error": f"Path not found: {path}"}
            if not path_obj.is_dir():
                return {"error": f"Not a directory: {path}"}

            items = []
            for item in sorted(path_obj.iterdir()):
                items.append(
                    {
                        "name": item.name,
                        "type": "dir" if item.is_dir() else "file",
                        "size": item.stat().st_size if item.is_file() else None,
                    }
                )
            return {"action": "list", "path": str(path_obj), "items": items}

        elif action == "delete":
            if not path_obj.exists():
                return {"error": f"Path not found: {path}"}

            if path_obj.is_file():
                path_obj.unlink()
            elif path_obj.is_dir():
                import shutil

                shutil.rmtree(path_obj)

            return {"action": "delete", "path": str(path_obj), "status": "success"}

        else:
            return {"error": f"Unknown action: {action}"}

    except Exception as e:
        return {"error": f"File operation failed: {str(e)}"}
