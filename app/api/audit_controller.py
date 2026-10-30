"""Bulk customer notification preferences audit (KAN-102).

POST /api/v1/customers/audit/preferences
Read-only. JWT bearer auth (ADR-02), RFC 7807 errors (ADR-01), 1-100 sanitized IDs (ADR-03).
Authentication and authorization run before the body is parsed or any lookup happens.
"""
import re
from typing import Annotated, List, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field, StrictStr, StringConstraints, ValidationError, field_validator

from app.preferences.store import Preferences, lookup
from app.security.jwt_hs256 import extract_bearer_token, require_audit_access, validate_token
from app.security.problem import ProblemDetailException

router = APIRouter(prefix="/api/v1/customers", tags=["audit"])

MAX_BATCH_SIZE = 100
_CUSTOMER_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")

CustomerId = Annotated[StrictStr, StringConstraints(strip_whitespace=True, pattern=_CUSTOMER_ID.pattern)]


class BulkPreferencesAuditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customerIds: List[CustomerId] = Field(min_length=1, max_length=MAX_BATCH_SIZE)

    @field_validator("customerIds")
    @classmethod
    def _no_duplicates(cls, ids: List[str]) -> List[str]:
        if len(set(ids)) != len(ids):
            raise ValueError("customerIds must not contain duplicates")
        return ids


class AuditResult(BaseModel):
    customerId: str
    missing: bool
    preferences: Optional[Preferences] = None


class BulkPreferencesAuditResponse(BaseModel):
    results: List[AuditResult]


def _bad_request(exc: ValidationError) -> ProblemDetailException:
    # Build the detail from field locations and messages only; never echo submitted values.
    parts = []
    for err in exc.errors()[:5]:
        if err.get("type") == "extra_forbidden":
            parts.append("body: unexpected field")  # key name is client-controlled; do not echo it
            continue
        loc = ".".join(str(p) for p in err.get("loc", ()))
        parts.append(f"{loc or 'body'}: {err.get('msg', 'invalid')}")
    return ProblemDetailException(400, "Bad Request", "Invalid request: " + "; ".join(parts))


@router.post(
    "/audit/preferences",
    response_model=BulkPreferencesAuditResponse,
    response_model_exclude_none=True,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": BulkPreferencesAuditRequest.model_json_schema()}},
        }
    },
    responses={400: {}, 401: {}, 403: {}, 500: {}},
)
async def audit_preferences(request: Request) -> BulkPreferencesAuditResponse:
    claims = validate_token(extract_bearer_token(request.headers.get("authorization")))
    require_audit_access(claims)

    try:
        payload = BulkPreferencesAuditRequest.model_validate_json(await request.body())
    except ValidationError as exc:
        raise _bad_request(exc) from None

    results: List[AuditResult] = []
    for customer_id in payload.customerIds:
        prefs = lookup(customer_id)
        if prefs is None:
            results.append(AuditResult(customerId=customer_id, missing=True))
        else:
            results.append(AuditResult(customerId=customer_id, missing=False, preferences=prefs.model_copy()))
    return BulkPreferencesAuditResponse(results=results)
