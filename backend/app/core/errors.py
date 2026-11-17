"""Global error handling and exception handlers."""

import logging
from typing import Any
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import (
    ConflictError,
    GameError,
    GameStateError,
    NotFoundError,
    ValidationError,
)

logger = logging.getLogger("isekai.api")

HTTP_STATUS_CODE_NAMES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "UNPROCESSABLE_ENTITY",
    500: "INTERNAL_SERVER_ERROR",
}


def build_error_envelope(
    error_code: str,
    message: str,
    details: dict[str, Any] | None = None,
    detail_override: Any = None,
) -> dict[str, Any]:
    """Build standardized error envelope with top-level fields and detail compatibility."""
    details_dict = details if details is not None else {}
    inner_detail = (
        detail_override
        if detail_override is not None
        else {
            "error": error_code,
            "message": message,
            "details": details_dict,
        }
    )
    return {
        "error": error_code,
        "message": message,
        "details": details_dict,
        "detail": inner_detail,
    }


async def game_error_handler(request: Request, exc: GameError) -> JSONResponse:
    """Handle GameError and all domain subclasses."""
    if isinstance(exc, NotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, ValidationError):
        status_code = status.HTTP_400_BAD_REQUEST
    elif isinstance(exc, (ConflictError, GameStateError)):
        status_code = status.HTTP_409_CONFLICT
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    content = build_error_envelope(
        error_code=exc.code,
        message=exc.message,
        details=exc.details,
    )
    return JSONResponse(status_code=status_code, content=content)


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle FastAPI and Starlette HTTPException."""
    if isinstance(exc.detail, dict):
        error_code = exc.detail.get(
            "error",
            HTTP_STATUS_CODE_NAMES.get(exc.status_code, "HTTP_ERROR"),
        )
        message = exc.detail.get("message", "An HTTP error occurred.")
        details = exc.detail.get("details", {})
        content = build_error_envelope(
            error_code=error_code,
            message=message,
            details=details,
            detail_override=exc.detail,
        )
    else:
        error_code = HTTP_STATUS_CODE_NAMES.get(exc.status_code, "HTTP_ERROR")
        message = str(exc.detail) if exc.detail else "An HTTP error occurred."
        content = build_error_envelope(
            error_code=error_code,
            message=message,
            details={},
        )

    return JSONResponse(status_code=exc.status_code, content=content)


async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic request validation errors."""
    errors = exc.errors()
    content = build_error_envelope(
        error_code="VALIDATION_ERROR",
        message="Request validation failed.",
        details={"errors": errors},
        detail_override=errors,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=content,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle any uncaught unexpected exception."""
    logger.exception(
        "Unhandled server exception on %s %s: %s",
        request.method,
        request.url.path,
        exc,
    )
    content = build_error_envelope(
        error_code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred.",
        details={"type": type(exc).__name__},
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=content,
    )


def register_error_handlers(app: Any) -> None:
    """Register all global exception handlers on FastAPI app."""
    app.add_exception_handler(GameError, game_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(
        RequestValidationError, request_validation_exception_handler
    )
    app.add_exception_handler(Exception, unhandled_exception_handler)
    app.add_exception_handler(500, unhandled_exception_handler)
