from typing import Any


class Orb:
    def __init__(self) -> None:
        pass

    def get_tool(self, name: str):
        from tools.registry import create_default_registry
        registry = create_default_registry()
        return registry.get(name)

    def list_tools(self) -> list[str]:
        from tools.registry import create_default_registry
        registry = create_default_registry()
        return registry.list_tools()

    def execute(self, name: str, **kwargs) -> dict[str, Any]:
        from tools.registry import create_default_registry
        registry = create_default_registry()
        return registry.execute(name, **kwargs)

    def gemini_declarations(self) -> list[dict[str, Any]]:
        from tools.registry import create_default_registry
        registry = create_default_registry()
        return registry.gemini_declarations()

    def get_all_tools_metadata(self) -> list[dict[str, Any]]:
        from tools.registry import create_default_registry
        registry = create_default_registry()
        return registry.get_all_tools_metadata()
