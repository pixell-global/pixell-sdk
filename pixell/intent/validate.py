from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from jsonschema import Draft7Validator


def _load_json(path: Path) -> Dict[str, Any]:
    import json

    with path.open("r", encoding="utf-8") as f:
        data: Dict[str, Any] = json.load(f)
        return data


def resolve_intent_schema_path(intent_name: str, schema_path: str | None = None) -> Path:
    """Resolve a schema file for a given intent name.
    If schema_path is provided and points to a file, use it.
    Otherwise look under default location: pixell/intent/schemas/{intent}.schema.json
    """
    if schema_path:
        p = Path(schema_path).expanduser().resolve()
        if not p.exists():
            raise FileNotFoundError(f"Intent schema not found: {p}")
        return p
    # Default location inside package
    default = Path(__file__).parent / "schemas" / f"{intent_name}.schema.json"
    if not default.exists():
        raise FileNotFoundError(
            f"Intent schema not found for '{intent_name}'. Provide --intent-schema or add {default}"
        )
    return default


def validate_intent_params(
    intent_name: str, params: Dict[str, Any], schema_path: str | None = None
) -> None:
    """Validate per-intent params against JSON Schema for that intent.
    Raises jsonschema.ValidationError on failure.
    """
    schema_file = resolve_intent_schema_path(intent_name, schema_path)
    schema = _load_json(schema_file)
    Draft7Validator(schema).validate(params)
