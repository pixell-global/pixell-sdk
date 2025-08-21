import pytest
from pydantic import ValidationError

from pixell.ui import UISpec, Manifest, View, Component


def test_minimal_valid_uispec() -> None:
    spec = UISpec(
        manifest=Manifest(
            id="example.app.v1",
            name="Example App",
            version="1.0.0",
            capabilities=["page", "list", "button"],
        ),
        data={"items": [{"title": "Hello"}]},
        actions={
            "open": {"kind": "open_url", "url": "https://example.com"},
        },
        view=View(
            type="page",
            title="Items",
            children=[
                Component(type="list", props={"data": "@items", "item": {"type": "text", "props": {"text": "{{ title }}"}}}),
                Component(type="button", props={"text": "Open", "onPress": {"action": "open"}}),
            ],
        ),
    )
    data = spec.model_dump(mode="json")
    assert data["manifest"]["id"] == "example.app.v1"
    assert data["view"]["type"] == "page"


def test_table_view_example_like_prd() -> None:
    spec = UISpec(
        manifest=Manifest(id="reddit.commenter.v1", name="Reddit Commenter", version="1.0.0"),
        data={"posts": [{"title": "A"}], "ui": {"selected": []}},
        actions={
            "openPost": {"kind": "open_url", "url": "https://www.reddit.com/comments/{{ row.id }}/"},
            "approve": {"kind": "http", "method": "POST", "url": "http://localhost:8000/api/chat/stream", "stream": True},
        },
        view=View(
            type="page",
            title="Reddit Posts",
            children=[
                Component(
                    type="table",
                    props={
                        "data": "@posts",
                        "selection": {"mode": "multi", "bind": "@ui.selected"},
                        "columns": [
                            {"header": "Title", "cell": {"type": "text", "props": {"text": "{{ title }}"}}},
                        ],
                    },
                ),
                Component(type="button", props={"text": "Approve", "onPress": {"action": "approve"}}),
            ],
        ),
    )
    assert spec.view.children[0].type == "table"


def test_invalid_component_type_raises() -> None:
    with pytest.raises(ValidationError):
        Component(type="unknown", props={}) 