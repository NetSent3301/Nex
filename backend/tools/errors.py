import os


class ToolError(Exception):
    def __init__(self, message: str, code: int = -1) -> None:
        self.code = code
        super().__init__(message)


class SecurityError(ToolError):
    def __init__(self, message: str = "Security violation") -> None:
        super().__init__(message, code=1001)


class PathTraversalError(SecurityError):
    def __init__(self, path: str, resolved: str, workspace: str) -> None:
        msg = (
            f"Path traversal blocked: '{path}' resolved to '{resolved}' "
            f"which is outside the workspace '{workspace}'"
        )
        super().__init__(msg)
        self.path = path
        self.resolved = resolved
        self.workspace = workspace


class ToolTimeoutError(ToolError):
    def __init__(self, timeout_ms: int) -> None:
        super().__init__(f"Tool timed out after {timeout_ms}ms", code=1002)


def validate_path_safety(path: str, workspace_root: str) -> str:
    resolved = os.path.normpath(os.path.join(workspace_root, path))
    workspace_root = os.path.normpath(workspace_root)

    if os.path.commonpath([resolved, workspace_root]) != workspace_root:
        raise PathTraversalError(path, resolved, workspace_root)

    return resolved
