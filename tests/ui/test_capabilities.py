from pixell.ui import (
    UISpec,
    Manifest,
    View,
    Component,
    ClientCapabilities,
    adapt_view_for_capabilities,
)


def build_table_spec() -> UISpec:
    return UISpec(
        manifest=Manifest(id="ex.v1", name="Ex", version="1.0.0"),
        data={"rows": [{"title": "A"}]},
        actions={},
        view=View(
            type="page",
            title="Cap Test",
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


def test_table_to_list_fallback() -> None:
    spec = build_table_spec()
    caps = ClientCapabilities(components=["page", "list"])  # no table
    adapted = adapt_view_for_capabilities(spec, caps)
    assert adapted.view.children[0].type == "list"


def test_no_change_when_supported() -> None:
    spec = build_table_spec()
    caps = ClientCapabilities(components=["page", "table", "list"])  # has table
    adapted = adapt_view_for_capabilities(spec, caps)
    assert adapted.view.children[0].type == "table"
