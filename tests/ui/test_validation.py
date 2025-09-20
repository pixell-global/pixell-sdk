import pytest
from pixell.ui import UISpec, Manifest, View, Component, validate_spec


def test_validate_spec_with_model_passes() -> None:
    spec = UISpec(
        manifest=Manifest(id="ex.v1", name="Ex", version="1.0.0"),
        data={},
        actions={},
        view=View(type="page", title="T", children=[Component(type="text", props={"text": "hi"})]),
    )
    validate_spec(spec)


def test_validate_spec_with_dict_passes() -> None:
    payload = {
        "manifest": {"id": "ex.v1", "name": "Ex", "version": "1.0.0"},
        "data": {},
        "actions": {},
        "view": {"type": "page", "children": [{"type": "text", "props": {"text": "hi"}}]},
    }
    validate_spec(payload)


def test_validate_spec_invalid_raises() -> None:
    with pytest.raises(Exception):
        validate_spec({"manifest": {}, "view": {"type": "page"}})
