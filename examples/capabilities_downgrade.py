import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pixell.ui import (
    UISpec,
    Manifest,
    View,
    Component,
    ClientCapabilities,
    adapt_view_for_capabilities,
)


def build_spec() -> UISpec:
    return UISpec(
        manifest=Manifest(
            id="ex.v1", name="Ex", version="1.0.0", capabilities=["page", "table", "list"]
        ),
        data={"rows": [{"title": "A"}, {"title": "B"}]},
        actions={},
        view=View(
            type="page",
            title="Cap Downgrade",
            children=[
                Component(
                    type="table",
                    props={
                        "data": "@rows",
                        "columns": [
                            {
                                "header": "Title",
                                "cell": {"type": "text", "props": {"text": "{{ title }}"}},
                            }
                        ],
                    },
                )
            ],
        ),
    )


def main() -> None:
    spec = build_spec()
    caps = ClientCapabilities(components=["page", "list"], streaming=False, specVersion="1.0.0")
    adapted = adapt_view_for_capabilities(spec, caps)
    print(json.dumps(adapted.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
