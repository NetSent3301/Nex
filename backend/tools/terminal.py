import subprocess
import shlex
from typing import Any

from tools.tool import Tool
from tools.errors import ToolError


class RunCommand(Tool):
    name = "run_command"
    description = "Execute a shell command on the system and return stdout + stderr."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to execute (e.g. 'ls -la').",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Maximum execution time in seconds (default 30).",
                },
            },
            "required": ["command"],
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        command: str = kwargs["command"]
        timeout: int = kwargs.get("timeout", 30)
        workspace: str = kwargs.get("workspace_root", ".")

        if not command or not command.strip():
            raise ToolError("Empty command.")

        try:
            result = subprocess.run(
                command,
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
                "output": f"Command timed out after {timeout}s.",
            }
        except FileNotFoundError:
            return {
                "success": False,
                "exit_code": -1,
                "output": f"Command not found: {command}",
            }
        except Exception as e:
            raise ToolError(f"Failed to execute command: {e}")
