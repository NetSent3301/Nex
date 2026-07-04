import time
from dataclasses import dataclass, field


@dataclass
class TraceStep:
    action: str
    duration: float
    result: str = ""


class Tracer:
    def __init__(self) -> None:
        self.steps: list[TraceStep] = []

    def begin(self, action: str) -> None:
        self._start = time.monotonic()
        self._current = action

    def end(self, result: str = "") -> None:
        duration = time.monotonic() - self._start
        self.steps.append(TraceStep(self._current, duration, result))
