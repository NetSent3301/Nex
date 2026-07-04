import os
import re
from pathlib import Path
from typing import Any

from tools.tool import Tool
from tools.errors import ToolError, validate_path_safety


class SkillsTool(Tool):
    name = "skills"
    description = "Manage and use reusable skills (instructions written in Markdown). Load, list, or execute skills for specific tasks."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action: 'list' (list all skills), 'load' (load a skill's content), 'run' (execute a skill's instructions).",
                    "enum": ["list", "load", "run"],
                },
                "name": {
                    "type": "string",
                    "description": "Skill name (for load and run actions).",
                },
                "skill_dirs": {
                    "type": "string",
                    "description": "Comma-separated directories to search for skills. Defaults to '.opencode/skills' in workspace and '~/.config/opencode/skills'.",
                },
            },
            "required": ["action"],
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        action: str = kwargs["action"]
        name: str = kwargs.get("name", "")
        workspace: str = kwargs.get("workspace_root", os.getcwd())
        skill_dirs_str: str = kwargs.get("skill_dirs", "")

        skill_dirs = self._resolve_skill_dirs(skill_dirs_str, workspace)
        skills = self._discover_skills(skill_dirs)

        if action == "list":
            return {
                "success": True,
                "skills": [
                    {
                        "name": s["name"],
                        "description": s.get("description", ""),
                        "source": s["source"],
                    }
                    for s in skills
                ],
                "skill_directories": skill_dirs,
            }

        if action in ("load", "run"):
            if not name:
                raise ToolError("skill name is required for load/run actions")

            skill = next((s for s in skills if s["name"] == name), None)
            if not skill:
                available = [s["name"] for s in skills]
                raise ToolError(f"Skill '{name}' not found. Available skills: {', '.join(available) or 'none'}")

            content = Path(skill["path"]).read_text(encoding="utf-8")
            result = {
                "success": True,
                "skill": {
                    "name": skill["name"],
                    "description": skill.get("description", ""),
                    "source": skill["source"],
                },
                "content": content if action == "load" else None,
            }

            if action == "load":
                return result

            instructions = self._parse_instructions(content)
            result["instructions"] = instructions
            result["message"] = f"Skill '{name}' loaded. Follow these instructions carefully."
            return result

        raise ToolError(f"Unknown action: {action}")

    def _resolve_skill_dirs(self, dirs_str: str, workspace: str) -> list[str]:
        dirs = []
        if dirs_str:
            for d in dirs_str.split(","):
                d = d.strip()
                if d:
                    dirs.append(os.path.abspath(os.path.join(workspace, d)))
        dirs.append(os.path.join(workspace, ".opencode", "skills"))
        dirs.append(os.path.join(os.path.expanduser("~"), ".config", "opencode", "skills"))
        return [d for d in dirs if os.path.isdir(d)]

    def _discover_skills(self, skill_dirs: list[str]) -> list[dict[str, Any]]:
        skills = []
        for skill_dir in skill_dirs:
            d = Path(skill_dir)
            if not d.is_dir():
                continue
            for file in d.glob("*.md"):
                name = file.stem
                description = ""
                try:
                    text = file.read_text(encoding="utf-8", errors="replace")
                    match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
                    if match:
                        name = match.group(1).strip()
                    desc_match = re.search(
                        r"^##\s*Description\s*\n+(.+?)(?:\n##|\Z)",
                        text, re.DOTALL | re.IGNORECASE,
                    )
                    if desc_match:
                        description = desc_match.group(1).strip()
                except Exception:
                    pass
                skills.append({
                    "name": name,
                    "description": description,
                    "source": str(d),
                    "path": str(file),
                })
        return skills

    def _parse_instructions(self, content: str) -> list[str]:
        sections = re.split(r"^##\s+", content, flags=re.MULTILINE)
        instructions = []
        for section in sections[1:]:
            lines = section.strip().split("\n")
            heading = lines[0].strip()
            body = "\n".join(lines[1:]).strip()
            if body:
                instructions.append(f"[{heading}]\n{body}")
            else:
                instructions.append(f"[{heading}]")
        return instructions
