import pytest
from pixell.ui import make_patch, validate_patch_scope


def test_make_patch_shape() -> None:
    ops = [{"op": "replace", "path": "/data/ui/selected", "value": [1, 2, 3]}]
    validate_patch_scope(ops)  # should not raise
    patch = make_patch(ops)
    assert isinstance(patch, list)
    assert patch[0]["path"].startswith("/data/")


def test_patch_scope_rejects_outside_paths() -> None:
    with pytest.raises(ValueError):
        validate_patch_scope([{"op": "replace", "path": "/theme/tokens/x", "value": 1}])
