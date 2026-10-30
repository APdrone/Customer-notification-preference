"""Shared constants for the KAN-100 QA tests."""
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "web" / "export" / "exportPreferences.js"
DRIVER = Path(__file__).with_name("driver.mjs")
SCHEMA_PATH = ROOT / "docs" / "schemas" / "notification-preferences-export.schema.json"
DOC_PATH = ROOT / "docs" / "notification-preferences-export.md"
KEY_ORDER = ["customerId", "email", "sms", "push_notification", "exportedAt"]

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
