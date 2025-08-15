from typing import Any, Dict, List, Iterable, Optional
from pydantic import BaseModel

ALLOWED_PREFIXES = ("/data/", "/view/")


class UIPatch(BaseModel):
    type: str = "ui.patch"
    patch: List[Dict[str, Any]]
    patchId: Optional[str] = None
    baseVersion: Optional[str] = None


def validate_patch_scope(ops: Iterable[Dict[str, Any]]) -> None:
    for op in ops:
        path = op.get("path", "")
        if not any(path.startswith(pfx) or path in ("/data", "/view") for pfx in ALLOWED_PREFIXES):
            raise ValueError(f"Patch path not allowed: {path}")


def make_patch(ops: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    validate_patch_scope(ops)
    return ops 