"""
GitHub Skill
Allows the agent to interact with GitHub repositories using the gh CLI.
"""

import subprocess
import json
from typing import Dict, Any


def skill(
    action: str,
    repo: str = "",
    file_path: str = "",
    content: str = "",
    commit_message: str = "Update via agent",
    branch: str = "main",
    **kwargs,
) -> Dict[str, Any]:
    """
    Interact with GitHub repositories.

    Args:
        action: 'list_repos', 'clone', 'read_file', 'write_file', 'push', 'list_files'
        repo: Repository in format 'owner/name'
        file_path: Path to file in repo
        content: Content to write
        commit_message: Commit message for push
        branch: Branch name
    """
    try:
        if action == "list_repos":
            # List user's repositories
            result = subprocess.run(
                ["gh", "repo", "list", "--limit", "50"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return {"error": "Failed to list repos"}

            repos = []
            for line in result.stdout.strip().split("\n")[1:]:  # Skip header
                if line.strip():
                    parts = line.split()
                    repos.append(parts[0] if parts else "")

            return {"status": "success", "repos": repos[:20], "count": len(repos)}

        elif action == "clone":
            # Clone a repository
            result = subprocess.run(
                ["gh", "repo", "clone", repo, "/tmp/gh_clone"],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                return {"error": f"Failed to clone {repo}"}

            return {"status": "success", "repo": repo, "path": "/tmp/gh_clone"}

        elif action == "read_file":
            # Read a file from a repo
            result = subprocess.run(
                ["gh", "api", f"repos/{repo}/contents/{file_path}"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return {"error": f"Failed to read {file_path} from {repo}"}

            try:
                data = json.loads(result.stdout)
                import base64

                file_content = base64.b64decode(data.get("content", "")).decode(
                    "utf-8"
                )
                return {
                    "status": "success",
                    "repo": repo,
                    "file": file_path,
                    "content": file_content,
                }
            except Exception as e:
                return {"error": f"Failed to parse file content: {str(e)}"}

        elif action == "write_file":
            # Write a file to a repo (requires push access)
            result = subprocess.run(
                [
                    "gh",
                    "api",
                    f"repos/{repo}/contents/{file_path}",
                    "-X",
                    "PUT",
                    "-f",
                    f"message={commit_message}",
                    "-f",
                    f"content={content}",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return {"error": f"Failed to write {file_path} to {repo}"}

            return {
                "status": "success",
                "repo": repo,
                "file": file_path,
                "message": commit_message,
            }

        elif action == "list_files":
            # List files in a repo directory
            result = subprocess.run(
                ["gh", "api", f"repos/{repo}/contents/{file_path}"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return {"error": f"Failed to list files in {repo}/{file_path}"}

            try:
                data = json.loads(result.stdout)
                if isinstance(data, list):
                    files = [
                        {"name": item["name"], "type": item["type"]} for item in data
                    ]
                    return {
                        "status": "success",
                        "repo": repo,
                        "path": file_path,
                        "files": files,
                    }
                else:
                    return {"error": "Not a directory"}
            except Exception as e:
                return {"error": f"Failed to parse response: {str(e)}"}

        else:
            return {"error": f"Unknown action: {action}"}

    except subprocess.TimeoutExpired:
        return {"error": "GitHub operation timeout"}
    except Exception as e:
        return {"error": f"GitHub skill failed: {str(e)}"}
