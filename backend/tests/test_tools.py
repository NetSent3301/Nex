
from tools.tool import Tool
from tools.errors import ToolError


class DummyTool(Tool):
    name = "dummy"
    description = "A dummy tool for testing"

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}, "required": []}

    def execute(self, **kwargs):
        return {"success": True}


def test_tool_registration():
    from tools.registry import Registry
    registry = Registry()
    dummy = DummyTool()
    registry.register(dummy)
    assert registry.get("dummy") is dummy


def test_tool_registry_get_all():
    from tools.registry import Registry
    registry = Registry()
    dummy = DummyTool()
    registry.register(dummy)
    metadata = registry.get_all_tools_metadata()
    assert len(metadata) > 0
    declarations = metadata[0].get("function_declarations", [])
    found = any(d.get("name") == "dummy" for d in declarations)
    assert found


def test_create_default_registry():
    from tools.registry import create_default_registry
    registry = create_default_registry()
    assert registry.get("run_command") is not None
    assert registry.get("read_file") is not None
    assert registry.get("write_file") is not None
    assert registry.get("git") is not None
    assert registry.get("web_fetch") is not None
    assert registry.get("web_search") is not None


def test_tool_error():
    error = ToolError("test error")
    assert str(error) == "test error"


def test_run_command_validation():
    from tools.terminal import RunCommand
    tool = RunCommand()

    import pytest
    with pytest.raises(ToolError, match="Empty command"):
        tool.execute(command="  ", timeout=5)

    result = tool.execute(command="echo hello", timeout=5)
    assert result["success"] is True
    assert "hello" in result["output"]


def test_git_tool_validation():
    from tools.git import GitTool
    tool = GitTool()

    import pytest
    with pytest.raises(ToolError, match="Empty git command"):
        tool.execute(args="  ", timeout=5)

    result = tool.execute(args="--version", timeout=5)
    assert result["success"] is True
