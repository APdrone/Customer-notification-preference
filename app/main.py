import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict

from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app import config as app_config
from app.health import HealthProbe

SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-secret-key')

app = FastAPI(title='Customer Notification Preferences API')


def _get_application_version() -> str:
    """Return the configured application version, or an empty string if unavailable."""
    value = getattr(app_config, 'APP_VERSION', '')
    if value is None:
        return ''
    return str(value).strip()


# ============================================================================
# Version Endpoint
# ============================================================================

@app.get('/version')
async def version_check():
    """Return the configured application version as JSON.

    Returns:
        dict: {"version": "<value>"} with HTTP 200 if configured
        JSONResponse: {"detail": "Version configuration unavailable"} with HTTP 503 otherwise
    """
    version = _get_application_version()
    if not version:
        return JSONResponse(
            status_code=503,
            content={'detail': 'Version configuration unavailable'}
        )
    return {'version': version}


# ============================================================================
# Health Check Endpoint
# ============================================================================

@app.get('/health')
async def health_check():
    """Health check endpoint for monitoring and orchestration.
    
    This endpoint is public (no authentication required) and returns the
    application health status. It is used by monitoring systems, load
    balancers, and container orchestrators to verify application readiness.
    
    Returns:
        dict: {"status": "healthy"} with HTTP 200 if app is healthy
        dict: {"status": "unhealthy"} with HTTP 503 if app is unhealthy
    
    Example:
        $ curl http://localhost:8000/health
        {"status":"healthy"}
        
        $ curl -i http://localhost:8000/health
        HTTP/1.1 200 OK
        content-type: application/json
        {"status":"healthy"}
    """
    try:
        is_healthy, _ = HealthProbe.check()
        if is_healthy:
            return {"status": "healthy"}
        else:
            return JSONResponse(
                status_code=503,
                content={"status": "unhealthy"}
            )
    except Exception as e:
        # Ensure health endpoint never crashes; return 503 on any error
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Health check endpoint error: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy"}
        )


# ============================================================================
# Preferences API Routes
# ============================================================================


class Preferences(BaseModel):
    email: bool = False
    sms: bool = False
    push_notification: bool = False


class Address(BaseModel):
    """Customer address model for profile and form workflows"""
    street: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = ""


class ProblemDetailException(Exception):
    def __init__(self, status: int, title: str, detail: str, instance: str = '') -> None:
        self.status = status
        self.title = title
        self.detail = detail
        self.instance = instance


def _problem_payload(status: int, title: str, detail: str, instance: str) -> Dict[str, Any]:
    return {
        'type': 'https://example.com/problems/' + title.lower().replace(' ', '-'),
        'title': title,
        'status': status,
        'detail': detail,
        'instance': instance,
    }


@app.exception_handler(ProblemDetailException)
async def problem_detail_exception_handler(_, exc: ProblemDetailException):
    return JSONResponse(
        status_code=exc.status,
        content=_problem_payload(exc.status, exc.title, exc.detail, exc.instance),
    )


PREFERENCE_STORE: Dict[str, Preferences] = {}
ADDRESS_STORE: Dict[str, Address] = {}
DRAFT_FORM_STORE: Dict[str, Dict[str, Any]] = {}


def _default_preferences() -> Preferences:
    return Preferences(email=False, sms=False, push_notification=False)


def _default_address() -> Address:
    """Return default empty address"""
    return Address(street="", city="", state="", postal_code="", country="")


def _encode_segment(value: Any) -> str:
    return base64.urlsafe_b64encode(
        json.dumps(value, separators=(',', ':'), sort_keys=True).encode('utf-8')
    ).rstrip(b'=').decode('utf-8')


def _decode_segment(segment: str) -> Any:
    padding = '=' * ((4 - len(segment) % 4) % 4)
    return json.loads(base64.urlsafe_b64decode((segment + padding).encode('utf-8')).decode('utf-8'))


def create_token(customer_id: str) -> str:
    header = {'alg': 'HS256', 'typ': 'JWT'}
    payload = {'sub': customer_id, 'exp': int(time.time()) + 3600}
    signing_input = f"{_encode_segment(header)}.{_encode_segment(payload)}".encode('utf-8')
    signature = hmac.new(SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256).digest()
    signature_segment = base64.urlsafe_b64encode(signature).rstrip(b'=').decode('utf-8')
    return f"{_encode_segment(header)}.{_encode_segment(payload)}.{signature_segment}"


def _get_customer_id_from_token(authorization: str | None, instance: str = '/customers/me/preferences') -> str:
    if not authorization or not authorization.startswith('Bearer '):
        raise ProblemDetailException(
            status=401,
            title='Unauthorized',
            detail='Authentication credentials were not provided or are invalid.',
            instance=instance,
        )

    token = authorization.replace('Bearer ', '', 1)
    try:
        header_segment, payload_segment, signature_segment = token.split('.')
    except ValueError as exc:  # pragma: no cover - defensive validation
        raise ProblemDetailException(
            status=401,
            title='Unauthorized',
            detail='Authentication credentials were not provided or are invalid.',
            instance=instance,
        ) from exc

    signing_input = f'{header_segment}.{payload_segment}'.encode('utf-8')
    expected_signature = hmac.new(SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256).digest()
    expected_segment = base64.urlsafe_b64encode(expected_signature).rstrip(b'=').decode('utf-8')

    if not hmac.compare_digest(expected_segment, signature_segment):
        raise ProblemDetailException(
            status=401,
            title='Unauthorized',
            detail='Authentication credentials were not provided or are invalid.',
            instance=instance,
        )

    try:
        payload = _decode_segment(payload_segment)
    except (ValueError, TypeError) as exc:  # pragma: no cover - defensive validation
        raise ProblemDetailException(
            status=401,
            title='Unauthorized',
            detail='Authentication credentials were not provided or are invalid.',
            instance=instance,
        ) from exc

    exp = payload.get('exp')
    if exp is not None and int(time.time()) > int(exp):
        raise ProblemDetailException(
            status=401,
            title='Unauthorized',
            detail='Authentication credentials were not provided or are invalid.',
            instance=instance,
        )

    customer_id = payload.get('sub')
    if not customer_id:
        raise ProblemDetailException(
            status=401,
            title='Unauthorized',
            detail='Authentication credentials were not provided or are invalid.',
            instance=instance,
        )

    return str(customer_id)


@app.get('/customers/me/preferences')
async def get_preferences(authorization: str | None = Header(default=None, alias='Authorization')):
    customer_id = _get_customer_id_from_token(authorization)
    preferences = PREFERENCE_STORE.setdefault(customer_id, _default_preferences())
    return preferences.model_dump()


@app.put('/customers/me/preferences')
async def update_preferences(
    payload: Preferences,
    authorization: str | None = Header(default=None, alias='Authorization'),
):
    customer_id = _get_customer_id_from_token(authorization)
    PREFERENCE_STORE[customer_id] = payload
    return payload.model_dump()
# ============================================================================
# Address API Routes (KAN-95)
# ============================================================================

@app.get('/customers/me/address')
async def get_customer_address(authorization: str | None = Header(default=None, alias='Authorization')):
    """Get the authenticated customer address from their profile.
    
    Returns the customer stored address or default empty address if none exists.
    
    Returns:
        dict: Address data with street, city, state, postal_code, country
        
    Raises:
        ProblemDetailException: 401 if authentication fails
    """
    customer_id = _get_customer_id_from_token(authorization, instance='/customers/me/address')
    address = ADDRESS_STORE.setdefault(customer_id, _default_address())
    return address.model_dump()


@app.post('/forms/{draft_id}/address:copyFromProfile')
async def copy_address_from_profile(
    draft_id: str,
    authorization: str | None = Header(default=None, alias='Authorization')
):
    """Copy customer profile address into a form draft.
    
    This endpoint implements the copy user address data into form workflow.
    It retrieves the authenticated customer address and copies it to the
    specified draft form.
    
    Args:
        draft_id: Unique identifier for the draft form
        authorization: Bearer token for authentication
        
    Returns:
        dict: Response containing draft_id, copied address data, and status
        
    Raises:
        ProblemDetailException: 401 if authentication fails
    """
    customer_id = _get_customer_id_from_token(
        authorization, 
        instance=f'/forms/{draft_id}/address:copyFromProfile'
    )
    
    # Get customer address from profile
    address = ADDRESS_STORE.setdefault(customer_id, _default_address())
    
    # Initialize draft form if it does not exist
    if draft_id not in DRAFT_FORM_STORE:
        DRAFT_FORM_STORE[draft_id] = {}
    
    # Copy address to form draft
    DRAFT_FORM_STORE[draft_id]['address'] = address.model_dump()
    DRAFT_FORM_STORE[draft_id]['customer_id'] = customer_id
    
    return {
        'draft_id': draft_id,
        'address': address.model_dump(),
        'status': 'copied'
    }
