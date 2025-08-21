from typing import Any
from pydantic import ValidationError
from .spec import UISpec
from .errors import AgentUIValidationError


def validate_spec(spec: UISpec | dict[str, Any]) -> None:
    """Validate a UISpec instance or dict; raise AgentUIValidationError if invalid."""
    try:
        if isinstance(spec, dict):
            UISpec.model_validate(spec)
        else:
            # Pydantic validation on dump
            spec.model_dump()
    except ValidationError as exc:
        raise AgentUIValidationError("Invalid UISpec", {"errors": exc.errors()}) from exc
