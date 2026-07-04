class ChatService:
    def __init__(self) -> None:
        self.sessions: dict[str, list[dict]] = {}

    def create_session(self) -> str:
        import uuid
        sid = str(uuid.uuid4())
        self.sessions[sid] = []
        return sid

    def add_message(self, session_id: str, message: dict) -> None:
        self.sessions[session_id].append(message)
