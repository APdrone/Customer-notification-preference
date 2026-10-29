"""Response DTOs for the form metadata contract (KAN-97 / KAN-98)."""
from typing import List, Literal, Optional

from pydantic import BaseModel

# Single place that defines how a required field is marked in a label.
REQUIRED_INDICATOR = "*"

FieldType = Literal["string", "number", "boolean", "object", "array"]


def format_label(label: str, required: bool) -> str:
    """Return the label as it should be displayed (visual only)."""
    return f"{label} {REQUIRED_INDICATOR}" if required else label


class FormFieldMeta(BaseModel):
    key: str
    label: str
    type: FieldType
    required: bool = False
    displayLabel: str = ""
    helpText: Optional[str] = None

    def model_post_init(self, __context) -> None:
        # Derived automatically so no per-field logic is needed (KAN-98).
        self.displayLabel = format_label(self.label, self.required)


class FormMeta(BaseModel):
    formKey: str
    title: str
    requiredIndicator: str = REQUIRED_INDICATOR
    fields: List[FormFieldMeta]
