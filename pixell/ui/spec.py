from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from .actions import ActionUnion
from .theme import Theme


class Manifest(BaseModel):
    id: str
    name: str
    version: str
    capabilities: List[str] = Field(default_factory=list)


class Component(BaseModel):
    type: Literal[
        "page",
        "container",
        "text",
        "image",
        "link",
        "button",
        "switch",
        "textarea",
        "textfield",
        "radio",
        "checkbox",
        "select",
        "list",
        "table",
        "modal",
        "form",
    ]
    props: Dict[str, Any] = Field(default_factory=dict)
    children: Optional[List["Component"]] = None


class View(BaseModel):
    type: Literal["page"]
    title: Optional[str] = None
    children: List[Component] = Field(default_factory=list)


class UISpec(BaseModel):
    manifest: Manifest
    data: Dict[str, Any] = Field(default_factory=dict)
    view: View
    actions: Dict[str, ActionUnion] = Field(default_factory=dict)
    theme: Optional[Theme] = None


class UIPatch(BaseModel):
    type: Literal["ui.patch"] = "ui.patch"
    patch: List[Dict[str, Any]]
    patchId: Optional[str] = None
    baseVersion: Optional[str] = None
