from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from jsonschema import Draft7Validator, validate


_SCHEMAS: Dict[str, Dict[str, Any]] | None = None


def _load_schemas() -> Dict[str, Dict[str, Any]]:
    global _SCHEMAS
    if _SCHEMAS is not None:
        return _SCHEMAS
    base = Path(__file__).parent / "schemas"
    with (base / "ui.event.schema.json").open("r", encoding="utf-8") as f:
        ui_event = __import__("json").load(f)
    with (base / "action.result.schema.json").open("r", encoding="utf-8") as f:
        action_result = __import__("json").load(f)
    with (base / "ui.patch.schema.json").open("r", encoding="utf-8") as f:
        ui_patch = __import__("json").load(f)
    _SCHEMAS = {
        "ui.event": ui_event,
        "action.result": action_result,
        "ui.patch": ui_patch,
    }
    return _SCHEMAS


def validate_envelope(envelope: Dict[str, Any]) -> None:
    """Validate a protocol envelope against its JSON Schema. Raises jsonschema.ValidationError on failure."""
    schemas = _load_schemas()
    msg_type = envelope.get("type")
    if msg_type not in schemas:
        raise ValueError(f"Unknown protocol message type: {msg_type}")
    Draft7Validator(schemas[msg_type]).validate(envelope)


def validate_outbound_if_dev(envelope: Dict[str, Any]) -> None:
    """Validate outbound envelopes in development mode (no-op in production)."""
    import os
    if os.getenv("PIXELL_ENV", "development").lower() in ("development", "dev", "local"):
        validate_envelope(envelope) 