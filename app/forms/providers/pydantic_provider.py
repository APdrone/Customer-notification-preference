"""Derive form field metadata from a Pydantic model.

Derived mode: a field is required when the model schema lists it in
``required``. Override mode: ``required_overrides`` forces fields to be shown
as required in the UI only; backend validation is never changed.
"""
from typing import Dict, Iterable, List, Optional, Type

from pydantic import BaseModel

from app.forms.models import FormFieldMeta

_JSON_TYPES = {"string", "number", "boolean", "object", "array"}


def _field_type(prop: dict) -> str:
    t = prop.get("type")
    if t == "integer":
        return "number"
    if t in _JSON_TYPES:
        return t
    for option in prop.get("anyOf", []):  # Optional[X] is anyOf [X, null]
        if option.get("type") not in (None, "null"):
            return _field_type(option)
    return "string"


def _default_label(key: str) -> str:
    return key.replace("_", " ").strip().capitalize()


def build_fields(
    model: Type[BaseModel],
    labels: Optional[Dict[str, str]] = None,
    help_texts: Optional[Dict[str, str]] = None,
    required_overrides: Iterable[str] = (),
) -> List[FormFieldMeta]:
    schema = model.model_json_schema()
    derived_required = set(schema.get("required", []))
    forced_required = set(required_overrides)
    labels = labels or {}
    help_texts = help_texts or {}

    unknown = forced_required - set(schema.get("properties", {}))
    if unknown:
        raise ValueError(f"required_overrides reference unknown fields: {sorted(unknown)}")

    return [
        FormFieldMeta(
            key=key,
            label=labels.get(key) or prop.get("title") or _default_label(key),
            type=_field_type(prop),
            required=key in derived_required or key in forced_required,
            helpText=help_texts.get(key) or prop.get("description"),
        )
        for key, prop in schema.get("properties", {}).items()
    ]
