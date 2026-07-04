from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Message:
    role: str
    content: str
    tool_calls: Optional[list[dict]] = None
    tool_call_id: Optional[str] = None


@dataclass
class Conversation:
    messages: list[Message] = field(default_factory=list)
    system_prompt: Optional[str] = None

    def add(self, message: Message) -> None:
        self.messages.append(message)

    def to_openai(self) -> list[dict]:
        return [{"role": m.role, "content": m.content} for m in self.messages]
