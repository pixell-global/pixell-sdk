from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class UiRender(BaseModel):
    """Envelope for initial render payload from agent to client."""

    type: Literal["ui.render"] = "ui.render"
    manifest: Dict[str, Any]
    data: Dict[str, Any]
    view: Dict[str, Any]
    actions: Optional[Dict[str, Any]] = None
    theme: Optional[Dict[str, Any]] = None


class UiPatch(BaseModel):
    """Envelope for JSON Patch updates from agent to client."""

    type: Literal["ui.patch"] = "ui.patch"
    patch: List[Dict[str, Any]]
    patchId: Optional[str] = None
    baseVersion: Optional[str] = None


class UiEvent(BaseModel):
    """Envelope for UI interaction from client to agent (intent invocation)."""

    type: Literal["ui.event"] = "ui.event"
    intent: str
    params: Dict[str, Any] = Field(default_factory=dict)
    trace_id: Optional[str] = None


class ActionResult(BaseModel):
    """Normalized result envelope from intent execution."""

    type: Literal["action.result"] = "action.result"
    action: Optional[str] = None
    intent: Optional[str] = None
    status: Literal["ok", "error", "cancelled"]
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    patch: Optional[List[Dict[str, Any]]] = None
    trace_id: Optional[str] = None


__all__ = [
    "UiRender",
    "UiPatch",
    "UiEvent",
    "ActionResult",
]
