from dataclasses import dataclass
from enum import Enum
from typing import Any


class EventType(Enum):
    MESSAGE = "message"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    DONE = "done"


@dataclass
class StreamEvent:
    type: EventType
    data: Any
