from typing import Any

from tools.tool import Tool
from tools.filesystem import (
    ReadFileTool,
    WriteFileTool,
    ListFilesTool,
    CreateDirectoryTool,
    DeletePathTool,
    MovePathTool,
    CopyPathTool,
    AppendFileTool,
    SearchFilesTool,
    FindFilesTool,
    FileInfoTool,
)
from tools.terminal import RunCommand
from tools.git import GitTool
from tools.web import WebFetchTool, WebSearchTool
from tools.code_analysis import CodeAnalysisTool
from tools.refactoring import RefactorTool
from tools.mcp import MCPTool
from tools.skills import SkillsTool
from tools.lsp import LSPTool
from tools.sessions import SessionTool
from tools.errors import ToolError


class Registry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def register_all(self, *tools: Tool) -> None:
        for tool in tools:
            self.register(tool)

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise ToolError(f"Unknown tool: {name}")
        return self._tools[name]

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())

    def execute(self, name: str, **kwargs: Any) -> dict[str, Any]:
        tool = self.get(name)
        return tool.execute(**kwargs)

 
    def gemini_declarations(self) -> list[dict[str, Any]]:
        declarations = []
        for name in sorted(self._tools):
            tool = self._tools[name]
            declarations.append({
                "name": name,
                "description": tool.description,
                "parameters": tool.parameters,
            })
        return declarations

    # Cambiamos o añadimos este método para que retorne el nombre estándar que espera el loop
    def get_all_tools_metadata(self) -> list[dict[str, Any]]:
        return [
            {
                "function_declarations": self.gemini_declarations(),
            }
        ]


def create_default_registry() -> Registry:
    registry = Registry()
    registry.register_all(
        ReadFileTool(),
        WriteFileTool(),
        ListFilesTool(),
        CreateDirectoryTool(),
        DeletePathTool(),
        MovePathTool(),
        CopyPathTool(),
        AppendFileTool(),
        SearchFilesTool(),
        FindFilesTool(),
        FileInfoTool(),
        RunCommand(),
        GitTool(),
        WebFetchTool(),
        WebSearchTool(),
        CodeAnalysisTool(),
        RefactorTool(),
        MCPTool(),
        SkillsTool(),
        LSPTool(),
        SessionTool(),
    )
    return registry