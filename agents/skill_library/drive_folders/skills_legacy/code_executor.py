"""
Code Executor Skill
Allows the agent to execute Python and Bash code safely with timeout protection.
"""

import subprocess
import tempfile
from typing import Dict, Any


def skill(
    language: str, code: str, timeout: int = 30, working_dir: str = "/tmp"
) -> Dict[str, Any]:
    """
    Execute code safely (Python or Bash).

    Args:
        language: 'python' or 'bash'
        code: Code to execute
        timeout: Execution timeout in seconds (default: 30)
        working_dir: Working directory for execution
    """
    try:
        if language == "python":
            result = subprocess.run(
                ["python3", "-c", code],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=working_dir,
            )

            return {
                "status": "success",
                "language": "python",
                "stdout": result.stdout[:2000],  # Limit output
                "stderr": result.stderr[:2000],
                "returncode": result.returncode,
            }

        elif language == "bash":
            result = subprocess.run(
                ["bash", "-c", code],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=working_dir,
            )

            return {
                "status": "success",
                "language": "bash",
                "stdout": result.stdout[:2000],  # Limit output
                "stderr": result.stderr[:2000],
                "returncode": result.returncode,
            }

        elif language == "shell":
            # Alias for bash
            result = subprocess.run(
                ["bash", "-c", code],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=working_dir,
            )

            return {
                "status": "success",
                "language": "shell",
                "stdout": result.stdout[:2000],
                "stderr": result.stderr[:2000],
                "returncode": result.returncode,
            }

        else:
            return {"error": f"Unsupported language: {language}"}

    except subprocess.TimeoutExpired:
        return {
            "error": f"Execution timeout after {timeout}s",
            "language": language,
        }
    except Exception as e:
        return {"error": f"Code execution failed: {str(e)}", "language": language}
