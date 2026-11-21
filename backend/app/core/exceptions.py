"""Handler global: o cliente recebe apenas um trace_id; o detalhe fica só no log do servidor."""

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.errors import AppError

logger = logging.getLogger("app.errors")


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    trace_id = str(uuid.uuid4())
    logger.exception("Erro não tratado trace_id=%s path=%s", trace_id, request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno. Informe o trace_id ao suporte.", "trace_id": trace_id},
    )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=headers)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)
