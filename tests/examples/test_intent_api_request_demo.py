import json
import sys
from pathlib import Path

# Allow importing from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from examples.intent_api_request_demo import handle_ui_event


def test_demo_happy_path():
    event = {
        "type": "ui.event",
        "intent": "fetch_status",
        "params": {"url": "https://httpbin.org/status/204"},
        "trace_id": "t-1",
    }
    result = handle_ui_event(event)
    assert result["type"] == "action.result"
    assert result["status"] in ("ok", "error")
    assert result.get("trace_id") == "t-1"


def test_demo_not_allowed():
    event = {"type": "ui.event", "intent": "not_allowed", "params": {}, "trace_id": "t-2"}
    result = handle_ui_event(event)
    assert result["type"] == "action.result"
    assert result["status"] == "error"
    assert result["message"] == "Intent not allowed"


def test_demo_rate_limit():
    event = {"type": "ui.event", "intent": "fetch_status", "params": {}, "trace_id": "t-3"}
    # Exceed limit of 5 per minute as configured in demo (we call 6 times)
    last = None
    for _ in range(6):
        last = handle_ui_event(event)
    assert last["status"] == "error"
    assert last["message"] == "Rate limit exceeded" 