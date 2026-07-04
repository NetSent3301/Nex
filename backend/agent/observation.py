from typing import Any


class Observation:
    @staticmethod
    def format(result: dict) -> str:
        if not isinstance(result, dict):
            return str(result)

        if result.get("success"):
            if "content" in result:
                content = result["content"]
                if isinstance(content, str) and len(content) > 500:
                    return f"Success: {content[:500]}... (truncated, {len(content)} chars)"
                return f"Success: {content}"
            if "output" in result:
                output = result["output"]
                if len(output) > 1000:
                    return f"Success: {output[:1000]}... (truncated, {len(output)} chars)"
                return f"Success: {output}"
            if "matches" in result:
                return f"Found {len(result['matches'])} matches"
            if "results" in result:
                return f"Found {len(result['results'])} results"
            if "entries" in result:
                return f"Found {len(result['entries'])} entries"
            if "changes" in result:
                return f"Changed {len(result['changes'])} files"
            if "sessions" in result:
                return f"Found {result.get('total_sessions', len(result['sessions']))} sessions"
            if "skills" in result:
                return f"Found {len(result['skills'])} skills"
            return "Success"
        else:
            error = result.get("error", result.get("message", "Unknown error"))
            return f"Error: {error}"

    @staticmethod
    def summarize(tool_name: str, result: dict) -> str:
        brief = Observation.format(result)
        return f"[{tool_name}] {brief}"
