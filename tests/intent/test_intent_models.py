from pixell.intent.models import IntentResult, ProgressEvent, PatchEvent, ResultEvent


def test_intent_result_round_trip():
    res = IntentResult(status="ok", message="done", details={"a": 1}, patch=[], trace_id="t1")
    data = res.model_dump(mode="json")
    res2 = IntentResult.model_validate(data)
    assert res2 == res


def test_stream_events_union():
    p = ProgressEvent(percent=50.0, note="half")
    assert p.type == "progress"

    patch = PatchEvent(ops=[{"op": "replace", "path": "/data/x", "value": 2}])
    assert patch.type == "patch"

    rr = ResultEvent(result=IntentResult(status="ok", trace_id="t2"))
    assert rr.type == "result" 