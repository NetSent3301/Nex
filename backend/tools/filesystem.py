import os
import shutil
import stat
import time
from pathlib import Path
from typing import Any

from tools.tool import Tool
from tools.errors import validate_path_safety, ToolError


class ReadFileTool(Tool):
    name = "read_file"
    description = "Read the contents of a file from the workspace."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path from the workspace root.",
                },
                "offset": {
                    "type": "integer",
                    "description": "Line number to start reading from (1-indexed).",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of lines to read.",
                },
            },
            "required": ["path"],
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        path = kwargs["path"]
        offset = kwargs.get("offset")
        limit = kwargs.get("limit")
        workspace = kwargs.get("workspace_root", os.getcwd())

        safe_path = Path(validate_path_safety(path, workspace))

        if not safe_path.exists():
            raise ToolError(f"File not found: {path}")

        if not safe_path.is_file():
            raise ToolError(f"Not a file: {path}")

        try:
            text = safe_path.read_text(encoding="utf-8")

            if offset is not None or limit is not None:
                lines = text.splitlines(keepends=True)
                start = (offset - 1) if offset else 0
                end = start + limit if limit else None
                text = "".join(lines[start:end])

            return {"success": True, "content": text}

        except PermissionError:
            raise ToolError(f"Permission denied: {path}")
        except UnicodeDecodeError:
            raise ToolError(f"Cannot decode file as UTF-8: {path}")


class WriteFileTool(Tool):
    name = "write_file"
    description = "Create or overwrite a file in the workspace."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path from the workspace root.",
                },
                "content": {
                    "type": "string",
                    "description": "The full content to write to the file.",
                },
            },
            "required": ["path", "content"],
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        path = kwargs["path"]
        content = kwargs["content"]
        workspace = kwargs.get("workspace_root", os.getcwd())

        safe_path = Path(validate_path_safety(path, workspace))

        try:
            safe_path.parent.mkdir(parents=True, exist_ok=True)
            safe_path.write_text(content, encoding="utf-8")
            return {"success": True, "path": str(safe_path)}

        except PermissionError:
            raise ToolError(f"Permission denied: {path}")
        except IsADirectoryError:
            raise ToolError(f"Cannot overwrite directory: {path}")
        except OSError as e:
            raise ToolError(f"Failed to write file: {e}")


class ListFilesTool(Tool):
    name = "list_files"
    description = "List files and directories inside a workspace path."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative directory path from the workspace root.",
                },
                "recursive": {
                    "type": "boolean",
                    "description": "List recursively.",
                },
            },
            "required": ["path"],
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        path = kwargs["path"]
        recursive = kwargs.get("recursive", False)
        workspace = kwargs.get("workspace_root", os.getcwd())

        safe_path = Path(validate_path_safety(path, workspace))

        if not safe_path.exists():
            raise ToolError(f"Path not found: {path}")
        if not safe_path.is_dir():
            raise ToolError(f"Not a directory: {path}")

        pattern = "**/*" if recursive else "*"
        entries = []
        for entry in sorted(safe_path.glob(pattern)):
            entry_type = "dir" if entry.is_dir() else "file"
            entries.append({"name": entry.name, "type": entry_type, "path": str(entry)})

        return {"success": True, "entries": entries}


class CreateDirectoryTool(Tool):
    name = "create_directory"
    description = "Create one or more directories (like mkdir -p). No error if they already exist."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative directory path from the workspace root.",
                },
            },
            "required": ["path"],
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        path = kwargs["path"]
        workspace = kwargs.get("workspace_root", os.getcwd())

        safe_path = Path(validate_path_safety(path, workspace))

        try:
            safe_path.mkdir(parents=True, exist_ok=True)
            return {"success": True, "path": str(safe_path)}
        except PermissionError:
            raise ToolError(f"Permission denied: {path}")
        except OSError as e:
            raise ToolError(f"Failed to create directory: {e}")


class DeletePathTool(Tool):
    name = "delete_path"
    description = "Delete a file or empty directory from the workspace."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path from the workspace root.",
                },
            },
            "required": ["path"],
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        path = kwargs["path"]
        workspace = kwargs.get("workspace_root", os.getcwd())

        safe_path = Path(validate_path_safety(path, workspace))

        if not safe_path.exists():
            raise ToolError(f"Path not found: {path}")

        try:
            if safe_path.is_dir():
                safe_path.rmdir()
            else:
                safe_path.unlink()
            return {"success": True, "path": str(safe_path)}
        except OSError as e:
            raise ToolError(f"Failed to delete: {e}")


class MovePathTool(Tool):
    name = "move_path"
    description = "Move or rename a file or directory."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Relative source path from the workspace root.",
                },
                "destination": {
                    "type": "string",
                    "description": "Relative destination path from the workspace root.",
                },
            },
            "required": ["source", "destination"],
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        source = kwargs["source"]
        destination = kwargs["destination"]
        workspace = kwargs.get("workspace_root", os.getcwd())

        safe_source = Path(validate_path_safety(source, workspace))
        safe_dest = Path(validate_path_safety(destination, workspace))

        if not safe_source.exists():
            raise ToolError(f"Source not found: {source}")

        try:
            safe_dest.parent.mkdir(parents=True, exist_ok=True)
            safe_source.rename(safe_dest)
            return {"success": True, "source": str(safe_source), "destination": str(safe_dest)}
        except OSError as e:
            raise ToolError(f"Failed to move: {e}")


class CopyPathTool(Tool):
    name = "copy_path"
    description = "Copy a file or directory to a new location."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Relative source path from the workspace root.",
                },
                "destination": {
                    "type": "string",
                    "description": "Relative destination path from the workspace root.",
                },
            },
            "required": ["source", "destination"],
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        source = kwargs["source"]
        destination = kwargs["destination"]
        workspace = kwargs.get("workspace_root", os.getcwd())

        safe_source = Path(validate_path_safety(source, workspace))
        safe_dest = Path(validate_path_safety(destination, workspace))

        if not safe_source.exists():
            raise ToolError(f"Source not found: {source}")

        try:
            safe_dest.parent.mkdir(parents=True, exist_ok=True)
            if safe_source.is_dir():
                shutil.copytree(safe_source, safe_dest)
            else:
                shutil.copy2(safe_source, safe_dest)
            return {"success": True, "source": str(safe_source), "destination": str(safe_dest)}
        except OSError as e:
            raise ToolError(f"Failed to copy: {e}")


class AppendFileTool(Tool):
    name = "append_file"
    description = "Append content to the end of an existing file."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path from the workspace root.",
                },
                "content": {
                    "type": "string",
                    "description": "Content to append to the file.",
                },
            },
            "required": ["path", "content"],
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        path = kwargs["path"]
        content = kwargs["content"]
        workspace = kwargs.get("workspace_root", os.getcwd())

        safe_path = Path(validate_path_safety(path, workspace))

        if not safe_path.exists():
            raise ToolError(f"File not found: {path}")
        if not safe_path.is_file():
            raise ToolError(f"Not a file: {path}")

        try:
            with safe_path.open("a", encoding="utf-8") as f:
                f.write(content)
            size = safe_path.stat().st_size
            return {"success": True, "path": str(safe_path), "size": size}
        except PermissionError:
            raise ToolError(f"Permission denied: {path}")
        except OSError as e:
            raise ToolError(f"Failed to append: {e}")


class SearchFilesTool(Tool):
    name = "search_files"
    description = "Search file contents using a regular expression (grep-like). Returns matching files and lines."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regular expression pattern to search for.",
                },
                "glob": {
                    "type": "string",
                    "description": "Optional file glob pattern to filter (e.g. '*.py', '*.{ts,tsx}'). Defaults to all files.",
                },
                "path": {
                    "type": "string",
                    "description": "Relative directory path from the workspace root to search in. Defaults to workspace root.",
                },
                "max_matches": {
                    "type": "integer",
                    "description": "Maximum number of matches to return (default 50).",
                },
            },
            "required": ["pattern"],
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        pattern = kwargs["pattern"]
        glob_pattern = kwargs.get("glob", "**/*")
        path = kwargs.get("path", ".")
        max_matches = kwargs.get("max_matches", 50)
        workspace = kwargs.get("workspace_root", os.getcwd())

        import re

        safe_path = Path(validate_path_safety(path, workspace))

        if not safe_path.exists():
            raise ToolError(f"Path not found: {path}")
        if not safe_path.is_dir():
            raise ToolError(f"Not a directory: {path}")

        try:
            regex = re.compile(pattern)
        except re.error as e:
            raise ToolError(f"Invalid regex pattern: {e}")

        matches = []
        try:
            for entry in safe_path.glob(glob_pattern):
                if not entry.is_file():
                    continue
                try:
                    text = entry.read_text(encoding="utf-8", errors="replace")
                    for i, line in enumerate(text.splitlines(), 1):
                        if regex.search(line):
                            rel_path = str(entry.relative_to(Path(workspace)))
                            matches.append({
                                "path": rel_path,
                                "line": i,
                                "content": line.strip(),
                            })
                            if len(matches) >= max_matches:
                                return {"success": True, "matches": matches, "truncated": True}
                except (PermissionError, OSError):
                    continue
        except OSError as e:
            raise ToolError(f"Failed to search: {e}")

        return {"success": True, "matches": matches, "truncated": False}


class FindFilesTool(Tool):
    name = "find_files"
    description = "Find files and directories matching a glob pattern."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to match (e.g. '**/*.py', 'src/**/*.ts').",
                },
                "path": {
                    "type": "string",
                    "description": "Relative directory path from the workspace root to search in. Defaults to workspace root.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default 100).",
                },
            },
            "required": ["pattern"],
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        pattern = kwargs["pattern"]
        path = kwargs.get("path", ".")
        max_results = kwargs.get("max_results", 100)
        workspace = kwargs.get("workspace_root", os.getcwd())

        safe_path = Path(validate_path_safety(path, workspace))

        if not safe_path.exists():
            raise ToolError(f"Path not found: {path}")
        if not safe_path.is_dir():
            raise ToolError(f"Not a directory: {path}")

        results = []
        try:
            for entry in safe_path.glob(pattern):
                rel_path = str(entry.relative_to(Path(workspace)))
                entry_type = "dir" if entry.is_dir() else "file"
                size = entry.stat().st_size if entry.is_file() else None
                results.append({"path": rel_path, "type": entry_type, "size": size})
                if len(results) >= max_results:
                    return {"success": True, "results": results, "truncated": True}
        except OSError as e:
            raise ToolError(f"Failed to find files: {e}")

        return {"success": True, "results": results, "truncated": False}


class FileInfoTool(Tool):
    name = "file_info"
    description = "Get metadata about a file or directory (size, permissions, modified time, type)."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path from the workspace root.",
                },
            },
            "required": ["path"],
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        path = kwargs["path"]
        workspace = kwargs.get("workspace_root", os.getcwd())

        safe_path = Path(validate_path_safety(path, workspace))

        if not safe_path.exists():
            raise ToolError(f"Path not found: {path}")

        try:
            st = safe_path.stat()
            entry_type = "dir" if safe_path.is_dir() else "file" if safe_path.is_file() else "other"
            perms = stat.filemode(st.st_mode)
            modified = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(st.st_mtime))
            created = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(st.st_ctime))

            return {
                "success": True,
                "path": path,
                "type": entry_type,
                "size": st.st_size,
                "permissions": perms,
                "modified": modified,
                "created": created,
                "owner": st.st_uid,
            }
        except PermissionError:
            raise ToolError(f"Permission denied: {path}")
        except OSError as e:
            raise ToolError(f"Failed to get file info: {e}")
