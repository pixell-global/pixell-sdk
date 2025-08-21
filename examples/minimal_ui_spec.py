import json
import sys
from pathlib import Path

# Allow running from repo without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pixell.ui import UISpec, Manifest, View, Component


def build_spec() -> UISpec:
    return UISpec(
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
                Component(
                    type="list",
                    props={"data": "@items", "item": {"type": "text", "props": {"text": "{{ title }}"}}},
                ),
                Component(
                    type="button",
                    props={"text": "Open", "onPress": {"action": "open"}},
                ),
            ],
        ),
    )


if __name__ == "__main__":
    spec = build_spec()
    print(json.dumps(spec.model_dump(mode="json"), indent=2)) 