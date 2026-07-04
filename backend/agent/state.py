from enum import Enum


class AgentState(Enum):
    IDLE = "idle"
    THINKING = "thinking"
    WAITING_TOOL = "waiting_tool"
    DONE = "done"
    ERROR = "error"
