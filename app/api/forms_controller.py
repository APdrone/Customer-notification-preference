"""Form metadata endpoints for UI clients.

Public (read-only, no sensitive data). If the API later adopts a global auth
policy, add the shared auth dependency to this router.
"""
import re
from typing import Dict, List

from fastapi import APIRouter, HTTPException

from app.forms.models import FormMeta
from app.forms.registry import registry

router = APIRouter(prefix="/api/v1/forms", tags=["forms"])

_FORM_KEY = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


@router.get("", response_model=Dict[str, List[str]])
def list_forms() -> Dict[str, List[str]]:
    return {"forms": registry.keys()}


@router.get("/{form_key}", response_model=FormMeta)
def get_form(form_key: str) -> FormMeta:
    if not _FORM_KEY.match(form_key):
        raise HTTPException(status_code=400, detail="Invalid formKey format")
    meta = registry.get(form_key)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"Unknown form '{form_key}'")
    return meta
