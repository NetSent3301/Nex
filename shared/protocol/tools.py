from typing import Any


ToolSchema = dict[str, Any]
ToolParameters = dict[str, Any]


class ToolSpec:
    name: str
    description: str
    parameters: ToolSchema
