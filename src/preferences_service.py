import json
from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException, status
from src.models import NotificationPreferences
from src.database import get_preferences_from_db, update_preferences_in_db, audit_preferences_change, publish_event
from src.errors import RFC7807ValidationError

router = APIRouter()

@router.put("/preferences", response_model=NotificationPreferences)
def update_preferences(request: Request, prefs: NotificationPreferences):
    customer_id = request.headers.get("X-Customer-ID")
    if not customer_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing customer ID")
    try:
        # Validate preferences (raise RFC7807ValidationError if invalid)
        prefs.validate()
    except RFC7807ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.to_rfc7807_dict()
        )
    existing = get_preferences_from_db(customer_id)
    if existing == prefs.dict():
        # Idempotent: nothing changed. Do not audit/event. Return 200 or 204.
        return {"detail": "No changes", "preferences": existing}
    # Genuine update: persist, audit, event
    update_preferences_in_db(customer_id, prefs.dict())
    audit_preferences_change(customer_id, prefs.dict())
    publish_event("preference_changed", customer_id, prefs.dict())
    return prefs.dict()