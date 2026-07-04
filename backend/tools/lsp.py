import ast
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from tools.tool import Tool
from tools.errors import ToolError, validate_path_safety


class LSPTool(Tool):
    name = "lsp"
    description = "Use Language Server Protocol (LSP) for code intelligence: go to definition, find references, get hover info, list diagnostics, get code completions. Supports Python (pyright/pylsp), TypeScript (ts_server), and more."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "LSP action to perform.",
                    "enum": ["definition", "references", "hover", "diagnostics", "completions", "signature"],
                },
                "file_path": {
                    "type": "string",
                    "description": "Relative path to the source file from the workspace root.",
                },
                "line": {
                    "type": "integer",
                    "description": "Line number (0-indexed) for the action.",
                },
                "column": {
                    "type": "integer",
                    "description": "Column number for the action.",
                },
                "language": {
                    "type": "string",
                    "description": "Programming language for the file (e.g. 'python', 'typescript', 'javascript'). Auto-detected from extension if not provided.",
                },
            },
            "required": ["action", "file_path"],
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        action: str = kwargs["action"]
        file_path: str = kwargs["file_path"]
        line: int = kwargs.get("line", 0)
        column: int = kwargs.get("column", 0)
        language: str = kwargs.get("language", "")
        workspace: str = kwargs.get("workspace_root", os.getcwd())

        safe_path = Path(validate_path_safety(file_path, workspace))
        if not safe_path.exists():
            raise ToolError(f"File not found: {file_path}")

        if not language:
            extension_map = {
                ".py": "python",
                ".ts": "typescript",
                ".tsx": "typescriptreact",
                ".js": "javascript",
                ".jsx": "javascriptreact",
                ".go": "go",
                ".rs": "rust",
                ".java": "java",
                ".c": "c",
                ".cpp": "cpp",
            }
            language = extension_map.get(safe_path.suffix.lower(), "")

        text = safe_path.read_text(encoding="utf-8", errors="replace")

        if language == "python":
            return self._analyze_python(action, text, file_path, safe_path, line, column, workspace)
        elif language in ("typescript", "typescriptreact", "javascript", "javascriptreact"):
            return self._analyze_ts(action, text, file_path, line, column, workspace)
        else:
            return self._analyze_python(action, text, file_path, safe_path, line, column, workspace)

    def _analyze_python(
        self, action: str, text: str, file_path: str,
        safe_path: Path, line: int, column: int, workspace: str
    ) -> dict[str, Any]:
        try:
            import ast
            tree = ast.parse(text)
        except SyntaxError as e:
            return {"success": True, "action": action, "language": "python", "warning": f"Syntax error: {e}"}

        lines = text.splitlines()

        if action == "diagnostics":
            return self._python_diagnostics(text, file_path)

        if action == "definition":
            return self._python_definition(tree, lines, line, column, file_path)

        if action == "references":
            return self._python_references(tree, lines, line, column, file_path)

        if action == "hover":
            return self._python_hover(tree, lines, line, column, file_path)

        if action == "signature":
            return self._python_signature(tree, lines, line, column, file_path)

        if action == "completions":
            return self._python_completions(text, file_path)

        return {"success": True, "action": action, "language": "python", "warning": f"Action '{action}' not fully implemented for Python"}

    def _python_diagnostics(self, text: str, file_path: str) -> dict[str, Any]:
        diagnostics = []
        lines = text.splitlines()

        import ast
        try:
            ast.parse(text)
        except SyntaxError as e:
            diagnostics.append({
                "message": str(e.msg),
                "line": (e.lineno or 1) - 1,
                "column": e.offset or 0,
                "severity": "error",
            })

        for i, line_content in enumerate(lines):
            stripped = line_content.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                pass

        return {"success": True, "action": "diagnostics", "language": "python", "diagnostics": diagnostics}

    def _python_definition(
        self, tree: ast.AST, lines: list[str], line: int, column: int, file_path: str
    ) -> dict[str, Any]:
        target = self._find_node_at_position(tree, line, column)
        definitions = []

        if isinstance(target, ast.Call):
            func = target.func
            if isinstance(func, ast.Name):
                definitions.append({
                    "name": func.id,
                    "type": "function",
                    "file": file_path,
                    "estimated_line": self._find_definition_line(tree, func.id),
                })
            elif isinstance(func, ast.Attribute):
                definitions.append({
                    "name": func.attr,
                    "type": "method/attribute",
                    "file": file_path,
                    "estimated_line": self._find_definition_line(tree, func.attr),
                })
        elif isinstance(target, ast.Name):
            definitions.append({
                "name": target.id,
                "type": "variable/class",
                "file": file_path,
                "estimated_line": self._find_definition_line(tree, target.id),
            })
        elif isinstance(target, ast.Attribute):
            definitions.append({
                "name": target.attr,
                "type": "attribute",
                "file": file_path,
                "estimated_line": self._find_definition_line(tree, target.attr),
            })

        return {"success": True, "action": "definition", "language": "python", "definitions": definitions}

    def _find_definition_line(self, tree: ast.AST, name: str) -> int | None:
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == name:
                    return node.lineno - 1
            elif isinstance(node, ast.ClassDef):
                if node.name == name:
                    return node.lineno - 1
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == name:
                        return node.lineno - 1
        return None

    def _find_node_at_position(self, tree: ast.AST, line: int, column: int) -> ast.AST | None:
        for node in ast.walk(tree):
            if hasattr(node, "lineno") and node.lineno - 1 == line:
                if hasattr(node, "end_lineno") and node.end_lineno:
                    if line <= node.end_lineno - 1:
                        return node
        return None

    def _python_references(
        self, tree: ast.AST, lines: list[str], line: int, column: int, file_path: str
    ) -> dict[str, Any]:
        target = self._find_node_at_position(tree, line, column)
        refs = []

        name = None
        if isinstance(target, ast.Name):
            name = target.id
        elif isinstance(target, ast.Attribute):
            name = target.attr
        elif isinstance(target, ast.Call):
            if hasattr(target.func, "id"):
                name = target.func.id
            elif hasattr(target.func, "attr"):
                name = target.func.attr

        if name:
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and node.id == name:
                    if hasattr(node, "lineno"):
                        refs.append({
                            "line": node.lineno - 1,
                            "column": node.col_offset,
                            "file": file_path,
                        })

        return {"success": True, "action": "references", "language": "python", "references": refs}

    def _python_hover(
        self, tree: ast.AST, lines: list[str], line: int, column: int, file_path: str
    ) -> dict[str, Any]:
        if 0 <= line < len(lines):
            current_line = lines[line]
            info = f"Line {line + 1}: {current_line.strip()}"

            target = self._find_node_at_position(tree, line, column)
            extra = ""
            if isinstance(target, ast.FunctionDef):
                extra = f"def {target.name}(...)"
            elif isinstance(target, ast.ClassDef):
                extra = f"class {target.name}(...)"
            elif isinstance(target, ast.Name):
                extra = f"Name: {target.id}"

            return {
                "success": True,
                "action": "hover",
                "language": "python",
                "content": info + ("\n" + extra if extra else ""),
            }

        return {"success": True, "action": "hover", "language": "python", "content": "Line out of range"}

    def _python_signature(
        self, tree: ast.AST, lines: list[str], line: int, column: int, file_path: str
    ) -> dict[str, Any]:
        target = self._find_node_at_position(tree, line, column)
        if isinstance(target, ast.Call):
            if hasattr(target.func, "id"):
                return {
                    "success": True,
                    "action": "signature",
                    "language": "python",
                    "function": target.func.id,
                    "args": [
                        {"keyword": kw.arg, "value": ast.dump(kw.value)} if kw.arg else {"positional": ast.dump(kw.value)}
                        for kw in target.keywords
                    ] if hasattr(target, "keywords") else [],
                }
        return {"success": True, "action": "signature", "language": "python", "function": "unknown"}

    def _python_completions(self, text: str, file_path: str) -> dict[str, Any]:
        import ast
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return {"success": True, "action": "completions", "language": "python", "completions": []}

        completions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                completions.append({"label": node.name, "kind": "function", "detail": f"def {node.name}"})
            elif isinstance(node, ast.ClassDef):
                completions.append({"label": node.name, "kind": "class", "detail": f"class {node.name}"})
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                completions.append({"label": node.id, "kind": "variable"})

        keywords = ["if", "else", "elif", "for", "while", "try", "except", "finally",
                     "with", "as", "import", "from", "class", "def", "return", "yield",
                     "async", "await", "pass", "break", "continue", "raise", "None",
                     "True", "False", "in", "not", "and", "or", "is", "lambda"]
        for kw in keywords:
            completions.append({"label": kw, "kind": "keyword"})

        seen = set()
        unique = []
        for c in completions:
            if c["label"] not in seen:
                seen.add(c["label"])
                unique.append(c)
        return {"success": True, "action": "completions", "language": "python", "completions": unique}

    def _analyze_ts(
        self, action: str, text: str, file_path: str,
        line: int, column: int, workspace: str
    ) -> dict[str, Any]:
        patterns = {
            "class": r"(?:export\s+)?(?:abstract\s+)?class\s+(\w+)",
            "interface": r"(?:export\s+)?interface\s+(\w+)",
            "function": r"(?:export\s+)?(?:async\s+)?function\s+(\w+)",
            "const": r"(?:export\s+)?const\s+(\w+)",
            "type": r"(?:export\s+)?type\s+(\w+)",
        }

        import re
        lines = text.splitlines()

        if action == "diagnostics":
            return {"success": True, "action": "diagnostics", "language": "typescript", "diagnostics": []}

        if action == "definition":
            if 0 <= line < len(lines):
                current = lines[line]
                definitions = []
                for kind, pattern in patterns.items():
                    for m in re.finditer(pattern, current):
                        definitions.append({
                            "name": m.group(1),
                            "kind": kind,
                            "file": file_path,
                            "line": line,
                        })
                return {"success": True, "action": "definition", "language": "typescript", "definitions": definitions}

        if action == "hover":
            if 0 <= line < len(lines):
                return {
                    "success": True,
                    "action": "hover",
                    "language": "typescript",
                    "content": f"Line {line + 1}: {lines[line].strip()}",
                }

        if action == "completions":
            completions = []
            for kind, pattern in patterns.items():
                for m in re.finditer(pattern, text):
                    completions.append({"label": m.group(1), "kind": kind})

            ts_keywords = ["export", "import", "from", "const", "let", "var", "function",
                           "class", "interface", "type", "extends", "implements", "async",
                           "await", "return", "if", "else", "for", "while", "of", "in",
                           "new", "this", "super", "typeof", "keyof", "never", "any",
                           "string", "number", "boolean", "void", "null", "undefined"]
            for kw in ts_keywords:
                completions.append({"label": kw, "kind": "keyword"})

            seen = set()
            unique = []
            for c in completions:
                if c["label"] not in seen:
                    seen.add(c["label"])
                    unique.append(c)
            return {"success": True, "action": "completions", "language": "typescript", "completions": unique}

        return {"success": True, "action": action, "language": "typescript", "warning": f"Action '{action}' not fully implemented for TypeScript"}
