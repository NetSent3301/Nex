import json
import os
import subprocess
from typing import Any

from tools.tool import Tool
from tools.errors import ToolError


class MCPTool(Tool):
    name = "mcp"
    description = "Connect to MCP (Model Context Protocol) servers to access external tools, databases, APIs, and services. Supports stdio-based MCP servers."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action to perform: 'list_servers' (show configured servers), 'call' (call an MCP tool), 'list_tools' (list tools from a server).",
                    "enum": ["list_servers", "list_tools", "call"],
                },
                "server": {
                    "type": "string",
                    "description": "Server name (for list_tools and call actions).",
                },
                "tool": {
                    "type": "string",
                    "description": "Tool name to call (for call action).",
                },
                "arguments": {
                    "type": "object",
                    "description": "Arguments to pass to the tool (for call action).",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds for the MCP operation (default 30).",
                },
            },
            "required": ["action"],
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        action: str = kwargs["action"]
        workspace: str = kwargs.get("workspace_root", os.getcwd())

        if action == "list_servers":
            return self._list_servers(workspace)
        elif action == "list_tools":
            server = kwargs.get("server", "")
            if not server:
                raise ToolError("server name is required for list_tools")
            return self._list_tools(server, workspace)
        elif action == "call":
            server = kwargs.get("server", "")
            tool = kwargs.get("tool", "")
            arguments = kwargs.get("arguments", {})
            timeout = kwargs.get("timeout", 30)
            if not server or not tool:
                raise ToolError("server and tool are required for call")
            return self._call_tool(server, tool, arguments, timeout, workspace)
        else:
            raise ToolError(f"Unknown action: {action}")

    def _get_config_path(self, workspace: str) -> str:
        return os.path.join(workspace, ".opencode", "mcp.json")

    def _load_config(self, workspace: str) -> dict[str, Any]:
        config_path = self._get_config_path(workspace)
        alt_path = os.path.join(os.path.expanduser("~"), ".config", "opencode", "mcp.json")

        for path in [config_path, alt_path]:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    continue
        return {}

    def _list_servers(self, workspace: str) -> dict[str, Any]:
        config = self._load_config(workspace)
        servers = []
        for name, cfg in config.items():
            servers.append({
                "name": name,
                "command": cfg.get("command", ""),
                "args": cfg.get("args", []),
            })
        return {
            "success": True,
            "servers": servers,
            "config_paths": [
                self._get_config_path(workspace),
                os.path.join(os.path.expanduser("~"), ".config", "opencode", "mcp.json"),
            ],
        }

    def _list_tools(self, server: str, workspace: str) -> dict[str, Any]:
        config = self._load_config(workspace)
        if server not in config:
            raise ToolError(f"MCP server '{server}' not found in config. Use 'list_servers' to see available servers.")

        cfg = config[server]
        cmd = cfg.get("command", "")
        args = cfg.get("args", [])

        try:
            payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
            result = subprocess.run(
                [cmd] + args,
                input=payload + "\n",
                capture_output=True,
                text=True,
                timeout=10,
                cwd=workspace,
            )
            response = json.loads(result.stdout.strip().split("\n")[0])
            tools = response.get("result", {}).get("tools", [])
            return {
                "success": True,
                "server": server,
                "tools": [
                    {"name": t["name"], "description": t.get("description", "")}
                    for t in tools
                ],
            }
        except subprocess.TimeoutExpired:
            raise ToolError(f"MCP server '{server}' timed out")
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            raise ToolError(f"Failed to list tools from MCP server '{server}': {e}")
        except FileNotFoundError:
            raise ToolError(f"MCP server command not found: {cmd}")
        except Exception as e:
            raise ToolError(f"MCP error: {e}")

    def _call_tool(
        self, server: str, tool: str,
        arguments: dict[str, Any], timeout: int, workspace: str
    ) -> dict[str, Any]:
        config = self._load_config(workspace)
        if server not in config:
            raise ToolError(f"MCP server '{server}' not found in config.")

        cfg = config[server]
        cmd = cfg.get("command", "")
        args = cfg.get("args", [])

        try:
            payload = json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": tool, "arguments": arguments},
            })
            result = subprocess.run(
                [cmd] + args,
                input=payload + "\n",
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=workspace,
            )
            response = json.loads(result.stdout.strip().split("\n")[0])
            content = response.get("result", {}).get("content", [])
            is_error = response.get("result", {}).get("isError", False)

            return {
                "success": not is_error,
                "server": server,
                "tool": tool,
                "content": content,
            }
        except subprocess.TimeoutExpired:
            raise ToolError(f"MCP tool '{tool}' on server '{server}' timed out after {timeout}s")
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            raise ToolError(f"Failed to call MCP tool '{tool}' on '{server}': {e}")
        except FileNotFoundError:
            raise ToolError(f"MCP server command not found: {cmd}")
        except Exception as e:
            raise ToolError(f"MCP error: {e}")
