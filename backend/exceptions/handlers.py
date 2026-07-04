from fastapi import Request
from fastapi.responses import JSONResponse
from exceptions.exceptions import NexBaseException


async def nex_exception_handler(request: Request, exc: NexBaseException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "code": exc.code},
    )
