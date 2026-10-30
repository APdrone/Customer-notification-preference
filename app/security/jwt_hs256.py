"""Minimal, dependency-free HS256 JWT validation (hmac/hashlib, constant-time compare).

Only HS256 is accepted; any other alg (including none) is rejected. The shared
secret is read from the JWT_SECRET_KEY environment variable at call time and there
is deliberately no default. Tokens and secrets are never logged or echoed.
"""
import base64
import binascii
import hashlib
import hmac
import json
import logging
import math
import os
import time
from typing import Any, Dict, Optional

from app.security.problem import ProblemDetailException

logger = logging.getLogger(__name__)

SECRET_ENV_VAR = "JWT_SECRET_KEY"
MAX_TOKEN_LENGTH = 8192
_UNAUTHORIZED_DETAIL = "Authentication credentials were not provided or are invalid."
_WWW_AUTHENTICATE = {"WWW-Authenticate": "Bearer"}


def _unauthorized(reason: str) -> ProblemDetailException:
    # reason is a fixed internal category (never token content); clients get a generic detail.
    logger.info("JWT authentication failed: %s", reason)
    return ProblemDetailException(401, "Unauthorized", _UNAUTHORIZED_DETAIL, headers=_WWW_AUTHENTICATE)


def _b64url_decode(segment: str) -> bytes:
    try:
        raw = segment.encode("ascii")
        return base64.urlsafe_b64decode(raw + b"=" * (-len(raw) % 4))
    except (UnicodeEncodeError, binascii.Error, ValueError):
        raise ValueError("bad base64url") from None


def _json_object(segment: str) -> Dict[str, Any]:
    try:
        value = json.loads(_b64url_decode(segment).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise ValueError("bad json segment") from None
    if not isinstance(value, dict):
        raise ValueError("segment is not an object")
    return value


def _secret() -> bytes:
    secret = os.environ.get(SECRET_ENV_VAR, "")
    if not secret:
        # Fail closed on misconfiguration; do not reveal details to the client.
        logger.error("%s is not configured; rejecting all authenticated requests", SECRET_ENV_VAR)
        raise ProblemDetailException(500, "Internal Server Error", "The server could not process the request.")
    return secret.encode("utf-8")


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def extract_bearer_token(authorization: Optional[str]) -> str:
    if not authorization:
        raise _unauthorized("missing authorization header")
    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1]:
        raise _unauthorized("malformed authorization header")
    return parts[1]


def validate_token(token: str, now: Optional[float] = None) -> Dict[str, Any]:
    """Validate an HS256 JWT and return its claims, or raise a 401 ProblemDetailException."""
    secret = _secret()
    if len(token) > MAX_TOKEN_LENGTH:
        raise _unauthorized("token too long")
    segments = token.split(".")
    if len(segments) != 3:
        raise _unauthorized("malformed token")
    header_seg, payload_seg, signature_seg = segments

    try:
        header = _json_object(header_seg)
        signature = _b64url_decode(signature_seg)
    except ValueError:
        raise _unauthorized("malformed token") from None
    if header.get("alg") != "HS256":
        raise _unauthorized("unsupported algorithm")

    try:
        signing_input = f"{header_seg}.{payload_seg}".encode("ascii")
    except UnicodeEncodeError:
        raise _unauthorized("malformed token") from None
    expected = hmac.new(secret, signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, signature):
        raise _unauthorized("invalid signature")

    try:
        claims = _json_object(payload_seg)
    except ValueError:
        raise _unauthorized("malformed token") from None

    current = time.time() if now is None else now
    exp = claims.get("exp")
    if not _is_number(exp):
        raise _unauthorized("missing or invalid exp")
    if current >= exp:
        raise _unauthorized("token expired")
    nbf = claims.get("nbf")
    if nbf is not None and (not _is_number(nbf) or current < nbf):
        raise _unauthorized("token not yet valid")
    sub = claims.get("sub")
    if not isinstance(sub, str) or not sub:
        raise _unauthorized("missing sub")
    return claims


def _as_tokens(value: Any) -> set:
    if isinstance(value, str):
        return set(value.split())
    if isinstance(value, (list, tuple)):
        return {v for v in value if isinstance(v, str)}
    return set()


def require_audit_access(claims: Dict[str, Any]) -> None:
    """ADR-02: allow role admin/compliance, or scope preferences:audit; otherwise 403."""
    roles = _as_tokens(claims.get("role"))
    scopes = _as_tokens(claims.get("scope"))
    if roles & {"admin", "compliance"} or "preferences:audit" in scopes:
        return
    logger.info("JWT authorization failed: insufficient audit permission")
    raise ProblemDetailException(403, "Forbidden", "The authenticated principal may not perform this action.")
