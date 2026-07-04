from dataclasses import dataclass


@dataclass
class ModelConfig:
    provider: str
    model: str
    temperature: float = 0.0
    max_tokens: int = 8192
