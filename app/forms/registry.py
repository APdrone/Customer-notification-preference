"""Registry mapping formKey -> form metadata builder."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.forms.models import FormMeta
from app.forms.providers.pydantic_provider import build_fields


class Preferences(BaseModel):
    """Customer notification preferences (all optional, default to off)."""

    email: bool = Field(False, description="Receive notifications via email")
    sms: bool = Field(False, description="Receive notifications via SMS")
    push_notification: bool = Field(False, description="Receive push notifications")


@dataclass(frozen=True)
class FormDefinition:
    form_key: str
    title: str
    model: type
    labels: Dict[str, str] = field(default_factory=dict)
    help_texts: Dict[str, str] = field(default_factory=dict)
    # UI-only: fields to display as required even if the model has defaults.
    required_overrides: tuple = ()

    def build(self) -> FormMeta:
        return FormMeta(
            formKey=self.form_key,
            title=self.title,
            fields=build_fields(
                self.model, self.labels, self.help_texts, self.required_overrides
            ),
        )


class FormRegistry:
    def __init__(self) -> None:
        self._forms: Dict[str, FormDefinition] = {}

    def register(self, definition: FormDefinition) -> None:
        self._forms[definition.form_key] = definition

    def get(self, form_key: str) -> Optional[FormMeta]:
        definition = self._forms.get(form_key)
        return definition.build() if definition else None

    def keys(self) -> List[str]:
        return sorted(self._forms)


def default_registry() -> FormRegistry:
    reg = FormRegistry()
    reg.register(
        FormDefinition(
            form_key="customer-preferences",
            title="Notification Preferences",
            model=Preferences,
            labels={"email": "Email", "sms": "SMS", "push_notification": "Push notification"},
        )
    )
    return reg


registry = default_registry()
