"""In-memory preference store, read via lookup by the audit API.

Mirrors the design PREFERENCE_STORE keyed by customer id. lookup never
mutates the store (no setdefault), so reads are idempotent.
"""
from typing import Dict, Optional

from pydantic import BaseModel


class Preferences(BaseModel):
    email: bool = False
    sms: bool = False
    push_notification: bool = False


PREFERENCE_STORE: Dict[str, Preferences] = {}


def lookup(customer_id: str) -> Optional[Preferences]:
    return PREFERENCE_STORE.get(customer_id)
