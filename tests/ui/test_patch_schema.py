import pytest

from pixell.protocol import validate_envelope


def test_patch_schema_valid():
    env = {
        "type": "ui.patch",
        "patch": [
            {"op": "replace", "path": "/data/x", "value": 1},
            {"op": "add", "path": "/view/title", "value": "New"},
        ],
    }
    validate_envelope(env)


def test_patch_schema_invalid_missing_path():
    env = {"type": "ui.patch", "patch": [{"op": "add", "value": 1}]}
    with pytest.raises(Exception):
        validate_envelope(env)
