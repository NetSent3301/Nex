class Memory:
    def __init__(self, max_tokens: int = 128_000) -> None:
        self.max_tokens = max_tokens
        self.messages: list[dict] = []

    def add(self, message: dict) -> None:
        self.messages.append(message)

    def recent(self, n: int = 10) -> list[dict]:
        return self.messages[-n:]
