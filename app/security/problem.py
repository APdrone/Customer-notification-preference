"""RFC 7807 Problem Details (ADR-01) for API errors."""
from typing import Dict, Optional

from fastapi import Request
from fastapi.responses import JSONResponse

PROBLEM_MEDIA_TYPE = "application/problem+json"


class ProblemDetailException(Exception):
    """Raised to produce an RFC 7807 response. The detail must be safe to return to clients."""

    def __init__(
        self,
        status: int,
        title: str,
        detail: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(f"{status} {title}")
        self.status = status
        self.title = title
        self.detail = detail
        self.headers = headers


def problem_response(exc: ProblemDetailException, instance: str) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status,
        media_type=PROBLEM_MEDIA_TYPE,
        headers=exc.headers,
        content={
            "type": "about:blank",
            "title": exc.title,
            "status": exc.status,
            "detail": exc.detail,
            "instance": instance,
        },
    )


async def problem_detail_exception_handler(request: Request, exc: ProblemDetailException) -> JSONResponse:
    return problem_response(exc, request.url.path)
