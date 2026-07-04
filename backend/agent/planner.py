from typing import Any


class Planner:
    def __init__(self) -> None:
        self.context: dict[str, Any] = {}

    def decompose(self, prompt: str) -> list[str]:
        if not prompt or not prompt.strip():
            return []

        prompt_lower = prompt.lower()

        analysis_triggers = ["analiza", "entiende", "explora", "comprende", "investiga",
                              "analyz", "understand", "explore", "research"]
        creation_triggers = ["crea", "escribe", "genera", "haz", "implementa",
                              "create", "write", "generate", "make", "implement"]
        refactor_triggers = ["refactoriza", "mejora", "optimiza", "limpia",
                              "refactor", "improve", "optimize", "clean"]
        debug_triggers = ["debug", "depura", "arregla", "corrige", "error",
                           "bug", "fix", "repair", "issue"]
        search_triggers = ["busca", "encuentra", "search", "find", "grep", "look for"]
        web_triggers = ["busca en internet", "web search", "search the web", "look up",
                         "investiga en", "research on"]

        if any(word in prompt_lower for word in web_triggers):
            return [
                f"Search the web for information about: {prompt}",
                f"Analyze and summarize the search results.",
            ]
        elif any(word in prompt_lower for word in analysis_triggers):
            return [
                f"First, understand the project structure and context.",
                f"Analyze the specific aspects mentioned: {prompt}",
                f"Provide a comprehensive summary of findings.",
            ]
        elif any(word in prompt_lower for word in debug_triggers):
            return [
                f"Identify the error or bug described in: {prompt}",
                f"Analyze relevant code and logs to find root cause.",
                f"Implement the fix and verify it works.",
            ]
        elif any(word in prompt_lower for word in creation_triggers):
            return [
                f"Plan the implementation based on: {prompt}",
                f"Create or modify the necessary files.",
                f"Verify the implementation works correctly.",
            ]
        elif any(word in prompt_lower for word in refactor_triggers):
            return [
                f"Analyze the code that needs refactoring: {prompt}",
                f"Plan the refactoring changes while maintaining existing style.",
                f"Apply the refactoring changes.",
                f"Verify the refactored code works correctly.",
            ]
        elif any(word in prompt_lower for word in search_triggers):
            return [
                f"Search the codebase for: {prompt}",
                f"Present the findings clearly.",
            ]
        else:
            return [prompt]

    def set_context(self, key: str, value: Any) -> None:
        self.context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        return self.context.get(key, default)
