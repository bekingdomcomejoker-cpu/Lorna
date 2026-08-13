"""
Google Drive Skill
Allows the agent to interact with Google Drive using rclone.
"""

import subprocess
import json
from typing import Dict, Any


def skill(
    action: str,
    path: str = "",
    local_path: str = "",
    remote_path: str = "",
    **kwargs,
) -> Dict[str, Any]:
    """
    Interact with Google Drive using rclone.

    Args:
        action: 'list', 'download', 'upload', 'delete', 'mkdir'
        path: Drive path (for list/delete)
        local_path: Local file path (for upload/download)
        remote_path: Remote file path (for upload/download)
    """
    try:
        config_file = "/home/ubuntu/.gdrive-rclone.ini"
        remote_name = "manus_google_drive"

        if action == "list":
            # List files in a Drive directory
            result = subprocess.run(
                [
                    "rclone",
                    "ls",
                    f"{remote_name}:{path}",
                    "--config",
                    config_file,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return {"error": f"Failed to list {path}"}

            files = []
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        files.append({"size": parts[0], "name": " ".join(parts[1:])})

            return {"status": "success", "path": path, "files": files}

        elif action == "download":
            # Download a file from Drive
            result = subprocess.run(
                [
                    "rclone",
                    "copy",
                    f"{remote_name}:{remote_path}",
                    local_path,
                    "--config",
                    config_file,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                return {"error": f"Failed to download {remote_path}"}

            return {
                "status": "success",
                "action": "download",
                "remote": remote_path,
                "local": local_path,
            }

        elif action == "upload":
            # Upload a file to Drive
            result = subprocess.run(
                [
                    "rclone",
                    "copy",
                    local_path,
                    f"{remote_name}:{remote_path}",
                    "--config",
                    config_file,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                return {"error": f"Failed to upload to {remote_path}"}

            return {
                "status": "success",
                "action": "upload",
                "local": local_path,
                "remote": remote_path,
            }

        elif action == "delete":
            # Delete a file or folder from Drive
            result = subprocess.run(
                [
                    "rclone",
                    "purge",
                    f"{remote_name}:{path}",
                    "--config",
                    config_file,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return {"error": f"Failed to delete {path}"}

            return {"status": "success", "action": "delete", "path": path}

        elif action == "mkdir":
            # Create a directory on Drive
            result = subprocess.run(
                [
                    "rclone",
                    "mkdir",
                    f"{remote_name}:{path}",
                    "--config",
                    config_file,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return {"error": f"Failed to create directory {path}"}

            return {"status": "success", "action": "mkdir", "path": path}

        else:
            return {"error": f"Unknown action: {action}"}

    except subprocess.TimeoutExpired:
        return {"error": "Google Drive operation timeout"}
    except Exception as e:
        return {"error": f"Google Drive skill failed: {str(e)}"}
