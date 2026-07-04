class WorkspaceService:
    def __init__(self) -> None:
        self.current: str | None = None

    def open(self, path: str) -> None:
        self.current = path
