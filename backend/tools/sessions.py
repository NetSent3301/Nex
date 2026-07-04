import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.tool import Tool
from tools.errors import ToolError


class SessionTool(Tool):
    name = "session"
    description = "Manage chat sessions: list, export, import, or clear sessions. Sessions contain conversation history with the AI."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action to perform.",
                    "enum": ["list", "export", "import", "clear", "rename"],
                },
                "session_id": {
                    "type": "string",
                    "description": "Session identifier (for export, import, clear, rename).",
                },
                "export_path": {
                    "type": "string",
                    "description": "File path to export to or import from (for export/import actions). Relative to workspace.",
                },
                "new_name": {
                    "type": "string",
                    "description": "New session ID/name (for rename action).",
                },
            },
            "required": ["action"],
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        action: str = kwargs["action"]
        session_id: str = kwargs.get("session_id", "")
        export_path: str = kwargs.get("export_path", "")
        new_name: str = kwargs.get("new_name", "")
        workspace: str = kwargs.get("workspace_root", os.getcwd())

        storage_dir = self._get_storage_dir(workspace)

        if action == "list":
            return self._list_sessions(storage_dir)
        elif action == "export":
            if not session_id:
                raise ToolError("session_id is required for export")
            return self._export_session(session_id, export_path, storage_dir, workspace)
        elif action == "import":
            if not export_path:
                raise ToolError("export_path is required for import")
            return self._import_session(export_path, session_id, storage_dir, workspace)
        elif action == "clear":
            if not session_id:
                raise ToolError("session_id is required for clear")
            return self._clear_session(session_id, storage_dir)
        elif action == "rename":
            if not session_id or not new_name:
                raise ToolError("session_id and new_name are required for rename")
            return self._rename_session(session_id, new_name, storage_dir)
        else:
            raise ToolError(f"Unknown action: {action}")

    def _get_storage_dir(self, workspace: str) -> str:
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        storage_dir = os.path.join(backend_dir, "storage")
        if os.path.isdir(storage_dir):
            return storage_dir
        alt = os.path.join(workspace, ".nex", "storage")
        os.makedirs(alt, exist_ok=True)
        return alt

    def _find_session_files(self, storage_dir: str) -> list[dict[str, Any]]:
        sessions = []
        for file in sorted(Path(storage_dir).glob(".nex_history*.json")):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                sid = file.stem.replace(".nex_history", "").lstrip("_") or "default"
                if sid == "default" and file.name == ".nex_history.json":
                    sid = "default"

                msg_count = len(data.get("messages", []))
                created = data.get("created_at", "unknown")
                updated = data.get("updated_at", "unknown")

                sessions.append({
                    "session_id": sid,
                    "file": file.name,
                    "messages": msg_count,
                    "created_at": created,
                    "updated_at": updated,
                })
            except (json.JSONDecodeError, KeyError):
                sessions.append({
                    "session_id": file.stem,
                    "file": file.name,
                    "messages": 0,
                    "created_at": "corrupted",
                    "updated_at": "corrupted",
                })

        return sessions

    def _list_sessions(self, storage_dir: str) -> dict[str, Any]:
        sessions = self._find_session_files(storage_dir)
        total = len(sessions)
        total_messages = sum(s["messages"] for s in sessions)
        return {
            "success": True,
            "sessions": sessions,
            "total_sessions": total,
            "total_messages": total_messages,
            "storage_dir": storage_dir,
        }

    def _export_session(
        self, session_id: str, export_path: str,
        storage_dir: str, workspace: str
    ) -> dict[str, Any]:
        from storage.memory import load_chat_history, _get_history_file

        try:
            history_file = _get_history_file(session_id) if session_id != "default" else os.path.join(storage_dir, ".nex_history.json")
        except Exception:
            history_file = os.path.join(storage_dir, f".nex_history_{session_id}.json") if session_id != "default" else os.path.join(storage_dir, ".nex_history.json")

        if not os.path.exists(history_file):
            raise ToolError(f"Session '{session_id}' not found. Use 'list' to see available sessions.")

        try:
            with open(history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            raise ToolError(f"Failed to read session: {e}")

        if export_path:
            dest = Path(validate_path_safety(export_path, workspace))
            if dest.is_dir():
                dest = dest / f"nex_session_{session_id}.json"
        else:
            dest = Path(workspace) / f"nex_session_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        from tools.errors import validate_path_safety
        validate_path_safety(str(dest), workspace)

        data["exported_at"] = datetime.now(timezone.utc).isoformat()
        data["session_id"] = session_id

        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return {
            "success": True,
            "session_id": session_id,
            "exported_to": str(dest),
            "messages": len(data.get("messages", [])),
        }

    def _import_session(
        self, import_path: str, new_session_id: str,
        storage_dir: str, workspace: str
    ) -> dict[str, Any]:
        from tools.errors import validate_path_safety

        safe_import = Path(validate_path_safety(import_path, workspace))
        if not safe_import.exists():
            raise ToolError(f"Import file not found: {import_path}")

        try:
            data = json.loads(safe_import.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError) as e:
            raise ToolError(f"Failed to read import file: {e}")

        messages = data.get("messages", [])
        if not messages:
            raise ToolError("No messages found in import file.")

        sid = new_session_id or data.get("session_id", "imported")
        dest_file = os.path.join(storage_dir, f".nex_history_{sid}.json")

        import_data = {
            "created_at": data.get("created_at", datetime.now(timezone.utc).isoformat()),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "imported_at": datetime.now(timezone.utc).isoformat(),
            "messages": messages,
        }

        with open(dest_file, "w", encoding="utf-8") as f:
            json.dump(import_data, f, indent=2, ensure_ascii=False)

        return {
            "success": True,
            "session_id": sid,
            "imported_from": str(safe_import),
            "messages_imported": len(messages),
        }

    def _clear_session(self, session_id: str, storage_dir: str) -> dict[str, Any]:
        from storage.memory import clear_history

        clear_history(session_id)
        return {
            "success": True,
            "session_id": session_id,
            "message": f"Session '{session_id}' cleared.",
        }

    def _rename_session(
        self, session_id: str, new_name: str, storage_dir: str
    ) -> dict[str, Any]:
        old_file = None
        for f in Path(storage_dir).glob(f".nex_history*{session_id}*.json"):
            old_file = f
            break

        if not old_file or not old_file.exists():
            raise ToolError(f"Session '{session_id}' not found.")

        new_file = old_file.parent / f".nex_history_{new_name}.json"
        shutil.move(str(old_file), str(new_file))

        return {
            "success": True,
            "old_session_id": session_id,
            "new_session_id": new_name,
        }

    def validate_path_safety(self, path: str, workspace: str) -> str:
        from tools.errors import validate_path_safety as vps
        return vps(path, workspace)
