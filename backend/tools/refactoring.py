import os
import re
from pathlib import Path
from typing import Any

from tools.tool import Tool
from tools.errors import ToolError, validate_path_safety


class RefactorTool(Tool):
    name = "refactor"
    description = "Apply refactoring operations on code: rename symbols, extract code, replace patterns, reformat files."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "Refactoring operation to perform.",
                    "enum": ["rename_symbol", "replace_pattern", "reformat"],
                },
                "path": {
                    "type": "string",
                    "description": "Relative path to the file or directory from the workspace root.",
                },
                "old_name": {
                    "type": "string",
                    "description": "Current symbol name or text pattern to replace (for rename_symbol/replace_pattern).",
                },
                "new_name": {
                    "type": "string",
                    "description": "New symbol name or replacement text (for rename_symbol/replace_pattern).",
                },
                "file_pattern": {
                    "type": "string",
                    "description": "Optional glob pattern to filter files (e.g. '**/*.py', '**/*.ts'). Defaults to all files.",
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, show what would change without making changes (default true).",
                },
            },
            "required": ["operation", "path"],
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        operation: str = kwargs["operation"]
        path: str = kwargs["path"]
        workspace: str = kwargs.get("workspace_root", os.getcwd())
        dry_run: bool = kwargs.get("dry_run", True)
        file_pattern: str = kwargs.get("file_pattern", "**/*")

        safe_path = Path(validate_path_safety(path, workspace))

        if not safe_path.exists():
            raise ToolError(f"Path not found: {path}")

        if operation == "rename_symbol":
            old_name = kwargs.get("old_name", "")
            new_name = kwargs.get("new_name", "")
            if not old_name or not new_name:
                raise ToolError("old_name and new_name are required for rename_symbol")
            return self._rename_symbol(safe_path, old_name, new_name, file_pattern, dry_run, workspace)

        elif operation == "replace_pattern":
            old_name = kwargs.get("old_name", "")
            new_name = kwargs.get("new_name", "")
            if not old_name or not new_name:
                raise ToolError("old_name and new_name are required for replace_pattern")
            return self._replace_pattern(safe_path, old_name, new_name, file_pattern, dry_run, workspace)

        elif operation == "reformat":
            return self._reformat(safe_path, dry_run, workspace)

        raise ToolError(f"Unknown operation: {operation}")

    def _rename_symbol(
        self, path: Path, old_name: str, new_name: str,
        file_pattern: str, dry_run: bool, workspace: str
    ) -> dict[str, Any]:
        return self._replace_pattern(
            path,
            rf'\b{re.escape(old_name)}\b',
            new_name,
            file_pattern,
            dry_run,
            workspace,
        )

    def _replace_pattern(
        self, path: Path, pattern: str, replacement: str,
        file_pattern: str, dry_run: bool, workspace: str
    ) -> dict[str, Any]:
        import fnmatch

        if path.is_file():
            files_to_process = [path]
        else:
            files_to_process = []
            for entry in path.rglob("*"):
                if not entry.is_file():
                    continue
                rel = str(entry.relative_to(path))
                if entry.name.startswith(".") or "/." in rel:
                    continue
                if fnmatch.fnmatch(entry.name, file_pattern) or fnmatch.fnmatch(rel, file_pattern):
                    files_to_process.append(entry)

        changes = []
        try:
            regex = re.compile(pattern)
        except re.error as e:
            raise ToolError(f"Invalid regex pattern: {e}")

        for file_path in files_to_process:
            try:
                text = file_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            new_text, count = regex.subn(replacement, text)
            if count > 0:
                ws_path = Path(workspace)
                rel = str(file_path.relative_to(ws_path)) if ws_path in file_path.parents else str(file_path)
                changes.append({
                    "file": rel,
                    "matches": count,
                })
                if not dry_run:
                    file_path.write_text(new_text, encoding="utf-8")

        return {
            "success": True,
            "operation": "replace_pattern",
            "dry_run": dry_run,
            "changes": changes,
            "total_files_changed": len(changes),
        }

    def _reformat(self, path: Path, dry_run: bool, workspace: str) -> dict[str, Any]:
        if path.is_file():
            files = [path]
        else:
            files = [p for p in path.rglob("*.py") if not p.name.startswith(".")]

        results = []
        for file_path in files:
            try:
                text = file_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            import ast
            try:
                ast.parse(text)
                results.append({
                    "file": str(file_path),
                    "status": "valid_syntax",
                })
                continue
            except SyntaxError:
                pass

            lines = text.splitlines()
            cleaned = []
            for line in lines:
                cleaned.append(line.rstrip())

            while cleaned and not cleaned[-1].strip():
                cleaned.pop()

            new_text = "\n".join(cleaned)
            if not new_text.endswith("\n"):
                new_text += "\n"

            if new_text != text:
                ws_path = Path(workspace)
                rel = str(file_path.relative_to(ws_path)) if ws_path in file_path.parents else str(file_path)
                results.append({
                    "file": rel,
                    "status": "cleaned",
                })
                if not dry_run:
                    file_path.write_text(new_text, encoding="utf-8")
            else:
                results.append({
                    "file": str(file_path),
                    "status": "already_clean",
                })

        return {
            "success": True,
            "operation": "reformat",
            "dry_run": dry_run,
            "files": results,
        }
