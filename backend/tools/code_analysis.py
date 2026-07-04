import os
import re
from pathlib import Path
from typing import Any

from tools.tool import Tool
from tools.errors import ToolError, validate_path_safety


class CodeAnalysisTool(Tool):
    name = "analyze_code"
    description = "Analyze code structure in a project: find imports, trace dependencies, identify classes and functions, understand project layout."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to a file or directory from the workspace root.",
                },
                "analysis_type": {
                    "type": "string",
                    "description": "Type of analysis: 'dependencies' (trace imports), 'structure' (classes/functions), 'summary' (project overview).",
                    "enum": ["dependencies", "structure", "summary"],
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum depth for recursive dependency analysis (default 2).",
                },
            },
            "required": ["path", "analysis_type"],
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        path: str = kwargs["path"]
        analysis_type: str = kwargs["analysis_type"]
        max_depth: int = kwargs.get("max_depth", 2)
        workspace: str = kwargs.get("workspace_root", os.getcwd())

        safe_path = Path(validate_path_safety(path, workspace))

        if not safe_path.exists():
            raise ToolError(f"Path not found: {path}")

        if analysis_type == "summary":
            result = self._summarize_project(safe_path, workspace)
            result["success"] = True
            return result
        elif analysis_type == "structure":
            result = self._analyze_structure(safe_path, workspace)
            result["success"] = True
            return result
        elif analysis_type == "dependencies":
            result = self._trace_dependencies(safe_path, workspace, max_depth)
            result["success"] = True
            return result
        else:
            raise ToolError(f"Unknown analysis type: {analysis_type}")

    def _summarize_project(self, path: Path, workspace: str) -> dict[str, Any]:
        summary = {
            "files": 0,
            "directories": 0,
            "languages": {},
            "total_lines": 0,
        }

        lang_extensions = {
            "py": "Python",
            "js": "JavaScript",
            "ts": "TypeScript",
            "tsx": "TypeScript React",
            "jsx": "JavaScript React",
            "rs": "Rust",
            "go": "Go",
            "java": "Java",
            "c": "C",
            "cpp": "C++",
            "h": "C Header",
            "hpp": "C++ Header",
            "css": "CSS",
            "html": "HTML",
            "json": "JSON",
            "toml": "TOML",
            "yaml": "YAML",
            "yml": "YAML",
            "md": "Markdown",
            "sh": "Shell",
            "ts": "TypeScript",
        }

        if path.is_file():
            ext = path.suffix.lstrip(".").lower()
            lang = lang_extensions.get(ext, ext.upper())
            lines = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
            return {
                "type": "file",
                "path": str(path),
                "language": lang,
                "lines": lines,
                "size_bytes": path.stat().st_size,
            }

        for entry in path.rglob("*"):
            if entry.is_dir():
                if not any(p.startswith(".") for p in entry.parts):
                    summary["directories"] += 1
                continue
            if entry.is_file():
                rel = entry.relative_to(path)
                if any(p.startswith(".") for p in rel.parts):
                    continue
                summary["files"] += 1
                ext = entry.suffix.lstrip(".").lower()
                if ext:
                    lang = lang_extensions.get(ext, ext.upper())
                    summary["languages"][lang] = summary["languages"].get(lang, 0) + 1
                try:
                    text = entry.read_text(encoding="utf-8", errors="replace")
                    summary["total_lines"] += len(text.splitlines())
                except Exception:
                    pass

        return {
            "type": "project",
            "path": str(path),
            "summary": summary,
        }

    def _analyze_structure(self, path: Path, workspace: str) -> dict[str, Any]:
        if path.is_file():
            return self._parse_file_structure(path, workspace)

        structure = []
        for entry in sorted(path.iterdir()):
            if entry.name.startswith("."):
                continue
            info = {"name": entry.name, "type": "dir" if entry.is_dir() else "file"}
            if entry.is_file() and entry.suffix == ".py":
                info["structure"] = self._parse_python_structure(entry)
            structure.append(info)

        return {"path": str(path), "structure": structure}

    def _parse_file_structure(self, path: Path, workspace: str) -> dict[str, Any]:
        text = path.read_text(encoding="utf-8", errors="replace")
        ext = path.suffix.lower()

        if ext == ".py":
            return {"path": str(path), "structure": self._parse_python_structure(path)}
        elif ext in (".ts", ".tsx", ".js", ".jsx"):
            return {"path": str(path), "structure": self._parse_ts_js_structure(text)}
        else:
            lines = len(text.splitlines())
            return {"path": str(path), "lines": lines, "language": ext.lstrip(".")}

    def _parse_python_structure(self, path: Path) -> list[dict[str, Any]]:
        text = path.read_text(encoding="utf-8", errors="replace")
        items = []

        for match in re.finditer(r"^class\s+(\w+)", text, re.MULTILINE):
            items.append({"type": "class", "name": match.group(1)})

        for match in re.finditer(r"^(?:async\s+)?def\s+(\w+)", text, re.MULTILINE):
            name = match.group(1)
            full = match.group(0)
            if full.startswith("async"):
                name = "async " + name
            items.append({"type": "function", "name": name})

        imports = []
        for match in re.finditer(r"^import\s+(\S+)|^from\s+(\S+)\s+import", text, re.MULTILINE):
            name = match.group(1) or match.group(2)
            imports.append(name)

        return {"symbols": items, "imports": imports}

    def _parse_ts_js_structure(self, text: str) -> list[dict[str, Any]]:
        items = []
        patterns = [
            (r"(?:export\s+)?(?:class|interface)\s+(\w+)", "class/interface"),
            (r"(?:export\s+)?(?:async\s+)?function\s+(\w+)", "function"),
            (r"(?:export\s+)?const\s+(\w+)\s*[:=]\s*(?:async\s*)?\(?", "const function"),
            (r"(?:export\s+)?default\s+(?:async\s+)?function\s+(\w+)", "default function"),
        ]
        for pattern, kind in patterns:
            for match in re.finditer(pattern, text):
                items.append({"type": kind, "name": match.group(1)})
        return items

    def _trace_dependencies(self, path: Path, workspace: str, max_depth: int) -> dict[str, Any]:
        visited: set[str] = set()
        deps: dict[str, list[str]] = {}
        stack = [(str(path), 0)]

        ws_path = Path(workspace)

        while stack and len(visited) < 50:
            current_path, depth = stack.pop(0)
            if current_path in visited:
                continue
            if depth > max_depth:
                continue

            visited.add(current_path)
            current_file = Path(current_path)
            if not current_file.is_file():
                continue

            try:
                text = current_file.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            rel = str(current_file.relative_to(ws_path)) if ws_path in current_file.parents else current_path
            deps[rel] = []
            ext = current_file.suffix.lower()

            if ext == ".py":
                for m in re.finditer(r"^(?:from\s+(\S+)\s+import|import\s+(\S+))", text, re.MULTILINE):
                    mod = m.group(1) or m.group(2)
                    deps[rel].append(mod)
                    if ws_path in current_file.parents:
                        dep_path = ws_path / mod.replace(".", "/")
                        for candidate in [dep_path.with_suffix(".py"), dep_path / "__init__.py"]:
                            if candidate.exists():
                                stack.append((str(candidate), depth + 1))
            elif ext in (".ts", ".tsx", ".js", ".jsx"):
                for m in re.finditer( r"""from\s+['"]([^'"]+)['"]""", text):
                    mod = m.group(1)
                    deps[rel].append(mod)
                    if mod.startswith(".") and ws_path in current_file.parents:
                        base = current_file.parent
                        dep_path = (base / mod).resolve()
                        for candidate in [dep_path.with_suffix(".ts"), dep_path.with_suffix(".tsx"),
                                          dep_path.with_suffix(".js"), dep_path.with_suffix(".jsx"),
                                          dep_path / "index.ts", dep_path / "index.tsx"]:
                            if candidate.exists():
                                stack.append((str(candidate), depth + 1))

        return {"dependencies": deps, "files_analyzed": len(visited)}
