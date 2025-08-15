from typing import Any, Dict, List, Optional
from .spec import Component, View


def page(title: str, children: Optional[List[Component]] = None) -> View:
    return View(type="page", title=title, children=children or [], props={})


def table(data_path: str, columns: List[Dict[str, Any]], selection: Optional[Dict[str, Any]] = None) -> Component:
    props: Dict[str, Any] = {"data": data_path, "columns": columns}
    if selection:
        props["selection"] = selection
    return Component(type="table", props=props)


def button(text: str, action: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Component:
    props: Dict[str, Any] = {"text": text}
    if action:
        props["onPress"] = action
    props.update(kwargs)
    return Component(type="button", props=props) 