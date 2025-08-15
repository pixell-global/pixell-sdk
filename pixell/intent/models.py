from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel


class IntentResult(BaseModel):
    status: Literal["ok", "error", "cancelled"]
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    patch: Optional[List[Dict[str, Any]]] = None
    trace_id: str


class ProgressEvent(BaseModel):
    type: Literal["progress"] = "progress"
    percent: Optional[float] = None
    note: Optional[str] = None


class PatchEvent(BaseModel):
    type: Literal["patch"] = "patch"
    ops: List[Dict[str, Any]]


class ResultEvent(BaseModel):
    type: Literal["result"] = "result"
    result: IntentResult


IntentStreamEvent = Union[ProgressEvent, PatchEvent, ResultEvent] 