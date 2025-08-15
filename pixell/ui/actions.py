from __future__ import annotations
from typing import Any, Dict, Literal, Optional, Annotated, Union
from pydantic import BaseModel, Field


class Action(BaseModel):
    kind: Literal["open_url", "http", "state.set", "emit"]


class OpenUrlAction(Action):
    kind: Literal["open_url"] = "open_url"
    url: str


class HttpAction(Action):
    kind: Literal["http"] = "http"
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    url: str
    body: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None
    stream: bool = False
    result: Optional[Dict[str, Any]] = None
    rateLimit: Optional[Dict[str, Any]] = None
    debounceMs: Optional[int] = None
    policy: Optional[Dict[str, Any]] = None


class StateSetOperation(BaseModel):
    path: str
    value: Any


class StateSetAction(Action):
    kind: Literal["state.set"] = "state.set"
    operations: list[StateSetOperation]


class EmitAction(Action):
    kind: Literal["emit"] = "emit"
    event: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None


# Discriminated union for actions by `kind`
ActionUnion = Annotated[
    Union[OpenUrlAction, HttpAction, StateSetAction, EmitAction],
    Field(discriminator="kind"),
] 