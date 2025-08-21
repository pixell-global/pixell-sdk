import json
import sys
from pathlib import Path
import urllib.request
import urllib.error

# Allow running from repo without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pixell.protocol import UiEvent, ActionResult, validate_envelope, validate_outbound_if_dev
from pixell.intent import IntentResult
from pixell.intent.policy import IntentPolicy
from pixell.intent.rate_limit import RateLimiter

# Persist limiter across calls for demo rate limiting
RATE_LIMITER = RateLimiter(max_calls=5, per_seconds=60)


def perform_http_get(url: str, timeout: float = 5.0) -> dict:
    """Make a simple GET request without external deps (urllib)."""
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            return {
                "status_code": resp.status,
                "headers": dict(resp.getheaders()),
                "length": len(body),
            }
    except urllib.error.HTTPError as e:
        return {"status_code": e.code, "error": str(e)}
    except Exception as e:
        return {"status_code": None, "error": str(e)}


def handle_ui_event(event_dict: dict) -> dict:
    """Simulate server-side intent handling: validate → policy → rate limit → execute → result."""
    # 1) Validate inbound envelope against schema
    validate_envelope(event_dict)

    # 2) Parse with Pydantic for typed access
    event = UiEvent.model_validate(event_dict)

    # 3) Policy check (allow-list)
    policy = IntentPolicy(allowed={"fetch_status"})
    if not policy.is_allowed(event.intent):
        result = ActionResult(
            status="error",
            intent=event.intent,
            message="Intent not allowed",
            details={"allowed": list(policy.allowed)},
        )
        envelope = result.model_dump(mode="json")
        envelope["type"] = "action.result"
        envelope["trace_id"] = event.trace_id
        validate_outbound_if_dev(envelope)
        return envelope

    # 4) Rate limiting (per session+intent). Using a static session id here for demo.
    session_id = "dev-session"
    if not RATE_LIMITER.allow(session_id, event.intent):
        result = ActionResult(
            status="error",
            intent=event.intent,
            message="Rate limit exceeded",
        )
        envelope = result.model_dump(mode="json")
        envelope["type"] = "action.result"
        envelope["trace_id"] = event.trace_id
        validate_outbound_if_dev(envelope)
        return envelope

    # 5) Execute business logic (server-side API call)
    url = event.params.get("url") or "https://httpbin.org/status/200"
    http_details = perform_http_get(url)

    status = "ok" if http_details.get("status_code") and http_details["status_code"] < 400 else "error"

    # 6) Build normalized result envelope
    result = IntentResult(
        status=status, message="Fetched URL", details=http_details, trace_id=event.trace_id or ""
    )

    action_result = ActionResult(
        status=result.status,
        intent=event.intent,
        message=result.message,
        details=result.details,
        trace_id=result.trace_id,
    )

    envelope = action_result.model_dump(mode="json")
    envelope["type"] = "action.result"

    # 7) Validate outbound in dev mode
    validate_outbound_if_dev(envelope)

    return envelope


def main() -> None:
    # Simulate a UI event invoking an intent with params
    event = {
        "type": "ui.event",
        "intent": "fetch_status",
        "params": {"url": "https://httpbin.org/status/204"},
        "trace_id": "uuid-demo-1234",
    }

    # Execute and print the action.result envelope
    result = handle_ui_event(event)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main() 