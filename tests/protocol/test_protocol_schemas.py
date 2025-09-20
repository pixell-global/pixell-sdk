import pytest

from pixell.protocol import validate_envelope


def test_ui_event_valid():
    envelope = {
        "type": "ui.event",
        "intent": "post_comment",
        "params": {"draftId": "abc123"},
        "trace_id": "uuid-1",
    }
    validate_envelope(envelope)


def test_ui_event_invalid_missing_intent():
    envelope = {
        "type": "ui.event",
        "params": {},
        "trace_id": "uuid-1",
    }
    with pytest.raises(Exception):
        validate_envelope(envelope)


def test_action_result_valid():
    envelope = {
        "type": "action.result",
        "intent": "post_comment",
        "status": "ok",
        "message": "Posted",
        "details": {"id": 1},
        "trace_id": "uuid-1",
    }
    validate_envelope(envelope)


def test_action_result_invalid_status():
    envelope = {
        "type": "action.result",
        "status": "unknown",
    }
    with pytest.raises(Exception):
        validate_envelope(envelope)


def test_ui_patch_valid():
    envelope = {
        "type": "ui.patch",
        "patch": [
            {"op": "replace", "path": "/data/foo", "value": 1},
            {"op": "add", "path": "/view/children/0", "value": {}},
        ],
    }
    validate_envelope(envelope)


def test_ui_patch_invalid_missing_op():
    envelope = {
        "type": "ui.patch",
        "patch": [
            {"path": "/data/foo", "value": 1},
        ],
    }
    with pytest.raises(Exception):
        validate_envelope(envelope)
