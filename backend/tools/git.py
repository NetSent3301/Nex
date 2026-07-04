import subprocess
from typing import Any

from tools.tool import Tool
from tools.errors import ToolError


class GitTool(Tool):
    name = "git"
    description = "Run git commands (clone, add, commit, push, pull, status, log, diff, branch, checkout, etc.)"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "args": {
                    "type": "string",
                    "description": "Git arguments/command to execute (e.g. 'status', 'log --oneline -5', 'add .').",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Maximum execution time in seconds (default 60).",
                },
            },
            "required": ["args"],
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        args: str = kwargs["args"]
        timeout: int = kwargs.get("timeout", 60)
        workspace: str = kwargs.get("workspace_root", ".")

        if not args or not args.strip():
            raise ToolError("Empty git command.")

        cmd = f"git {args.strip()}"

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=workspace,
            )

            output_parts: list[str] = []
            if result.stdout:
                output_parts.append(result.stdout.rstrip("\n"))
            if result.stderr:
                output_parts.append(f"[stderr]\n{result.stderr.rstrip(chr(10))}")

            return {
                "success": result.returncode == 0,
                "exit_code": result.returncode,
                "output": "\n".join(output_parts),
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "exit_code": -1,
                "output": f"Git command timed out after {timeout}s.",
            }
        except FileNotFoundError:
            return {
                "success": False,
                "exit_code": -1,
                "output": "Git not found. Is git installed?",
            }
        except Exception as e:
            raise ToolError(f"Failed to execute git command: {e}")
