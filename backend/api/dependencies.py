from fastapi import Request


def get_config(request: Request) -> dict:
    return request.app.state.config
