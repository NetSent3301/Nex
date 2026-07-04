import os
from tools.errors import validate_path_safety


class Workspace:
    def __init__(self, root: str) -> None:
        self.root = os.path.normpath(os.path.abspath(root))

    def resolve(self, path: str) -> str:
        return validate_path_safety(path, self.root)
