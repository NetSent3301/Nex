import urllib.request
import urllib.error
import json
from typing import Any

from tools.tool import Tool
from tools.errors import ToolError


class WebFetchTool(Tool):
    name = "web_fetch"
    description = "Fetch the content of a URL and return it as text/markdown. Useful for reading documentation, API responses, or web pages."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch content from.",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Request timeout in seconds (default 30).",
                },
            },
            "required": ["url"],
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        url: str = kwargs["url"]
        timeout: int = kwargs.get("timeout", 30)

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Nex/1.0",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                content_type = response.headers.get("Content-Type", "")
                raw = response.read()

                if "application/json" in content_type:
                    data = json.loads(raw)
                    text = json.dumps(data, indent=2, ensure_ascii=False)
                else:
                    text = raw.decode("utf-8", errors="replace")

                return {
                    "success": True,
                    "content": text,
                    "url": url,
                    "status": response.status,
                    "content_type": content_type,
                }

        except urllib.error.HTTPError as e:
            return {
                "success": False,
                "error": f"HTTP {e.code}: {e.reason}",
                "url": url,
            }
        except urllib.error.URLError as e:
            return {
                "success": False,
                "error": f"URL error: {e.reason}",
                "url": url,
            }
        except ValueError as e:
            raise ToolError(f"Invalid URL: {e}")
        except Exception as e:
            raise ToolError(f"Failed to fetch URL: {e}")


class WebSearchTool(Tool):
    name = "web_search"
    description = "Search the internet for information. Returns relevant results with titles, snippets, and URLs. Requires SEARCHAPI_KEY or similar configured."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default 8).",
                },
            },
            "required": ["query"],
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        query: str = kwargs["query"]
        max_results: int = kwargs.get("max_results", 8)

        import os
        api_key = os.getenv("SEARCHAPI_KEY") or os.getenv("GOOGLE_API_KEY") or ""

        if api_key:
            return self._search_with_api(query, max_results, api_key)

        return self._search_fallback(query, max_results)

    def _search_with_api(self, query: str, max_results: int, api_key: str) -> dict[str, Any]:
        import urllib.parse
        params = urllib.parse.urlencode({
            "q": query,
            "num": min(max_results, 10),
            "api_key": api_key,
        })
        url = f"https://serpapi.com/search?{params}"

        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=15) as response:
                data = json.loads(response.read().decode())
                results = []
                for item in data.get("organic_results", [])[:max_results]:
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                    })
                return {"success": True, "results": results, "query": query}
        except Exception as e:
            return self._search_fallback(query, max_results)

    def _search_fallback(self, query: str, max_results: int) -> dict[str, Any]:
        import urllib.parse
        encoded = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded}"

        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Nex/1.0",
                },
            )
            with urllib.request.urlopen(req, timeout=15) as response:
                html = response.read().decode("utf-8", errors="replace")

                import re
                results = []
                for match in re.finditer(
                    r'<a rel="nofollow" class="result__a" href="([^"]+)".*?>(.*?)</a>.*?'
                    r'<a class="result__snippet"[^>]*>(.*?)</a>',
                    html,
                    re.DOTALL,
                ):
                    results.append({
                        "url": match.group(1),
                        "title": re.sub(r"<[^>]+>", "", match.group(2)).strip(),
                        "snippet": re.sub(r"<[^>]+>", "", match.group(3)).strip(),
                    })
                    if len(results) >= max_results:
                        break

                return {"success": True, "results": results, "query": query}

        except Exception as e:
            return {
                "success": False,
                "error": f"Web search unavailable: {e}",
                "query": query,
            }
