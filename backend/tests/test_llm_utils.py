
from llm.utils import (
    convert_content_to_openai_messages,
    get_temperature,
    convert_tools_to_openai,
    convert_tools_to_anthropic,
    schema_to_dict,
)


class FakePart:
    def __init__(self, text=None, function_call=None, function_response=None):
        self.text = text
        self.function_call = function_call
        self.function_response = function_response


class FakeFunctionCall:
    def __init__(self, name, args=None):
        self.name = name
        self.args = args or {}


class FakeFunctionResponse:
    def __init__(self, response=None):
        self.response = response or {}


class FakeContent:
    def __init__(self, role="user", parts=None):
        self.role = role
        self.parts = parts or []


class FakeConfig:
    def __init__(self, temperature=None, system_instruction=None, tools=None):
        self.temperature = temperature
        self.system_instruction = system_instruction
        self.tools = tools


def test_convert_content_to_openai_messages_empty():
    result = convert_content_to_openai_messages([])
    assert result == [{"role": "user", "content": "Hello"}]


def test_convert_content_to_openai_messages_basic():
    content = FakeContent(role="user", parts=[FakePart(text="Hello")])
    result = convert_content_to_openai_messages([content])
    assert len(result) == 1
    assert result[0]["role"] == "user"
    assert result[0]["content"] == "Hello"


def test_convert_content_to_openai_messages_with_system():
    content = FakeContent(role="user", parts=[FakePart(text="Hi")])
    result = convert_content_to_openai_messages([content], system_instruction="Be nice")
    assert len(result) == 2
    assert result[0]["role"] == "system"
    assert result[0]["content"] == "Be nice"
    assert result[1]["role"] == "user"
    assert result[1]["content"] == "Hi"


def test_convert_content_to_openai_messages_model_role():
    content = FakeContent(role="model", parts=[FakePart(text="Response")])
    result = convert_content_to_openai_messages([content])
    assert result[0]["role"] == "assistant"


def test_convert_content_to_openai_messages_with_tool_call():
    fc = FakeFunctionCall("get_weather", {"city": "Tokyo"})
    content = FakeContent(role="model", parts=[FakePart(function_call=fc)])
    result = convert_content_to_openai_messages([content])
    assert result[0]["role"] == "assistant"
    assert "tool_calls" in result[0]
    assert result[0]["tool_calls"][0]["function"]["name"] == "get_weather"


def test_convert_content_to_openai_messages_with_tool_response():
    fr = FakeFunctionResponse({"temperature": 25})
    content = FakeContent(role="user", parts=[FakePart(function_response=fr)])
    result = convert_content_to_openai_messages([content])
    assert result[0]["role"] == "tool"


def test_get_temperature_from_config():
    config = FakeConfig(temperature=0.5)
    assert get_temperature(config) == 0.5


def test_get_temperature_default():
    assert get_temperature(None) == 0.7


def test_convert_tools_to_openai():
    tools = [{"function_declarations": [{"name": "test_tool", "description": "A test", "parameters": {}}]}]
    result = convert_tools_to_openai(tools)
    assert len(result) == 1
    assert result[0]["type"] == "function"
    assert result[0]["function"]["name"] == "test_tool"


def test_convert_tools_to_anthropic():
    tools = [{"function_declarations": [{"name": "test_tool", "description": "A test", "parameters": {}}]}]
    result = convert_tools_to_anthropic(tools)
    assert len(result) == 1
    assert result[0]["name"] == "test_tool"


class _Enum:
    def __init__(self, name):
        self.name = name


class FakeSchema:
    def __init__(self, type="OBJECT"):
        self.type = _Enum(type)
        is_obj = type == "OBJECT"
        self.properties = (
            {
                "city": FakeSchema(type="STRING"),
                "count": FakeSchema(type="INTEGER"),
            }
            if is_obj
            else None
        )
        self.required = ["city"] if is_obj else None
        self.items = None
        self.description = "A fake schema"
        self.enum = ["a", "b"]


class FakeFunctionDeclaration:
    def __init__(self, name, parameters):
        self.name = name
        self.parameters = parameters


class FakeTool:
    def __init__(self, fds):
        self.function_declarations = fds


def test_schema_to_dict_object():
    result = schema_to_dict(FakeSchema())
    assert result["type"] == "object"
    assert result["properties"]["city"]["type"] == "string"
    assert result["required"] == ["city"]
    assert result["enum"] == ["a", "b"]
    import json

    json.dumps(result)  # debe ser serializable


def test_schema_to_dict_passthrough_dict():
    schema = {"type": "object", "properties": {"x": {"type": "string"}}}
    assert schema_to_dict(schema) == schema


def test_convert_tools_to_openai_with_schema_objects():
    fd = FakeFunctionDeclaration("search", FakeSchema())
    result = convert_tools_to_openai([FakeTool([fd])])
    assert result[0]["function"]["name"] == "search"
    assert result[0]["function"]["parameters"]["type"] == "object"
    import json

    json.dumps(result)


def test_convert_tools_to_anthropic_with_schema_objects():
    fd = FakeFunctionDeclaration("search", FakeSchema())
    result = convert_tools_to_anthropic([FakeTool([fd])])
    assert result[0]["name"] == "search"
    assert result[0]["input_schema"]["type"] == "object"
