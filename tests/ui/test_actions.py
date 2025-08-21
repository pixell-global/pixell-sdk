from pixell.ui import UISpec, Manifest, View, Component


def test_actions_union_and_fields() -> None:
    spec = UISpec(
        manifest=Manifest(id="ex.v1", name="Ex", version="1.0.0"),
        data={},
        actions={
            "open": {"kind": "open_url", "url": "https://example.com"},
            "api": {"kind": "http", "method": "POST", "url": "https://api.example.com", "stream": True,
                     "rateLimit": {"key": "k", "windowMs": 1000, "max": 5}, "debounceMs": 200,
                     "policy": {"tag": "safe"}},
            "set": {"kind": "state.set", "operations": [{"path": "items[0].x", "value": 1}]},
            "emit": {"kind": "emit", "event": "changed", "payload": {"x": 1}},
        },
        view=View(type="page", children=[Component(type="text", props={"text": "hi"})]),
    )
    data = spec.model_dump(mode="json")
    assert data["actions"]["open"]["kind"] == "open_url"
    assert data["actions"]["api"]["stream"] is True
    assert data["actions"]["set"]["operations"][0]["path"].startswith("items")
    assert data["actions"]["emit"]["event"] == "changed" 