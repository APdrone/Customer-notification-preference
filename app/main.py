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

from app.health import HealthProbe

SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-secret-key')

app = FastAPI(title='Customer Notification Preferences API')


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


def _default_preferences() -> Preferences:
    return Preferences(email=False, sms=False, push_notification=False)


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


def _get_customer_id_from_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith('Bearer '):
        raise ProblemDetailException(
            status=401,
            title='Unauthorized',
            detail='Authentication credentials were not provided or are invalid.',
            instance='/customers/me/preferences',
        )

    token = authorization.replace('Bearer ', '', 1)
    try:
        header_segment, payload_segment, signature_segment = token.split('.')
    except ValueError as exc:  # pragma: no cover - defensive validation
        raise ProblemDetailException(
            status=401,
            title='Unauthorized',
            detail='Authentication credentials were not provided or are invalid.',
            instance='/customers/me/preferences',
        ) from exc

    signing_input = f'{header_segment}.{payload_segment}'.encode('utf-8')
    expected_signature = hmac.new(SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256).digest()
    expected_segment = base64.urlsafe_b64encode(expected_signature).rstrip(b'=').decode('utf-8')

    if not hmac.compare_digest(expected_segment, signature_segment):
        raise ProblemDetailException(
            status=401,
            title='Unauthorized',
            detail='Authentication credentials were not provided or are invalid.',
            instance='/customers/me/preferences',
        )

    try:
        payload = _decode_segment(payload_segment)
    except (ValueError, TypeError) as exc:  # pragma: no cover - defensive validation
        raise ProblemDetailException(
            status=401,
            title='Unauthorized',
            detail='Authentication credentials were not provided or are invalid.',
            instance='/customers/me/preferences',
        ) from exc

    exp = payload.get('exp')
    if exp is not None and int(time.time()) > int(exp):
        raise ProblemDetailException(
            status=401,
            title='Unauthorized',
            detail='Authentication credentials were not provided or are invalid.',
            instance='/customers/me/preferences',
        )

    customer_id = payload.get('sub')
    if not customer_id:
        raise ProblemDetailException(
            status=401,
            title='Unauthorized',
            detail='Authentication credentials were not provided or are invalid.',
            instance='/customers/me/preferences',
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
