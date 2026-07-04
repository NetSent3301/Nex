class HistoryStore:
    def save(self, conversation_id: str, messages: list[dict]) -> None:
        pass

    def load(self, conversation_id: str) -> list[dict]:
        return []
