from typing import Any, Dict, List, Optional, cast
from pydantic import BaseModel, Field
from .spec import UISpec, Component, View


class ClientCapabilities(BaseModel):
    components: List[str] = Field(default_factory=list)
    streaming: bool = False
    specVersion: Optional[str] = None
    features: List[str] = Field(default_factory=list)  # e.g., ["http.extended"]
    maxRows: Optional[int] = None
    maxColumns: Optional[int] = None
    maxPatchOps: Optional[int] = None


def is_supported(component_type: str, client_caps: Dict[str, Any]) -> bool:
    supported = set(client_caps.get("components", []))
    return component_type in supported or not supported  # allow if client didn't specify


SUPPORTED_FALLBACKS: Dict[str, str] = {
    "table": "list",
    "modal": "page",
}


def adapt_view_for_capabilities(spec: UISpec, caps: ClientCapabilities) -> UISpec:
    """Downgrade/adapt spec.view based on capabilities and limits."""
    view = spec.view
    if view.type == "page" and hasattr(view, "children") and view.children:
        new_children: List[Component] = []
        for child in view.children:
            child_type = child.type
            if child_type in SUPPORTED_FALLBACKS and child_type not in set(caps.components):
                fallback = SUPPORTED_FALLBACKS[child_type]
                if fallback == "list" and child_type == "table":
                    new_children.append(
                        Component(
                            type="list",
                            props={
                                "data": child.props.get("data", "@items"),
                                "item": {"type": "text", "props": {"text": "{{ title }}"}},
                            },
                        )
                    )
                else:
                    new_children.append(Component(type=cast(Any, fallback), props=child.props))
            else:
                new_children.append(child)
        spec.view = View(type=view.type, title=view.title, children=new_children)
    return spec


def http_method_allowed(method: str, caps: ClientCapabilities) -> bool:
    method = method.upper()
    if method in ("GET", "POST"):
        return True
    return "http.extended" in set(caps.features) 