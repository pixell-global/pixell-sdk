import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pixell.ui import UISpec, Manifest, View, Component


def build_spec() -> UISpec:
    manifest = Manifest(
        id="reddit.commenter.v1",
        name="Reddit Commenter",
        version="1.0.0",
        capabilities=["page", "table", "modal", "form", "button", "link"],
    )

    data = {
        "posts": [
            {
                "id": "t3_abc123",
                "title": "Post title",
                "content": "Body…",
                "comment": "",
                "source": "skincareaddiction",
                "score": 120,
                "commentCount": 34,
            }
        ],
        "ui": {"showTranslations": False, "selected": []},
    }

    actions = {
        "openPost": {
            "kind": "open_url",
            "url": "https://www.reddit.com/comments/{{ row.id | strip_prefix:'t3_' }}/",
        },
        "genComment": {
            "kind": "http",
            "method": "POST",
            "url": "http://localhost:18000/api/v1/reddit-commenter/gen-comment",
            "body": {"post_id": "{{ row.id }}"},
        },
        "approve": {
            "kind": "http",
            "method": "POST",
            "url": "http://localhost:8000/api/chat/stream",
            "stream": True,
            "body": {"items": "{{ map @ui.selected to @posts }}"},
        },
        "editComment": {
            "kind": "state.set",
            "operations": [{"path": "posts[{{ rowIndex }}].comment", "value": "{{ event.value }}"}],
        },
    }

    view = View(
        type="page",
        title="Reddit Posts",
        children=[
            Component(type="switch", props={"label": "번역 보기", "bind": "@ui.showTranslations"}),
            Component(
                type="table",
                props={
                    "data": "@posts",
                    "selection": {"mode": "multi", "bind": "@ui.selected"},
                    "columns": [
                        {
                            "header": "Title",
                            "cell": {
                                "type": "link",
                                "props": {"text": "{{ title }}", "onPress": {"action": "openPost"}},
                            },
                        },
                        {
                            "header": "Content",
                            "cell": {
                                "type": "text",
                                "props": {"text": "{{ content }}", "truncate": 50},
                            },
                        },
                        {
                            "header": "Comment",
                            "cell": {
                                "type": "textarea",
                                "props": {
                                    "text": "{{ comment }}",
                                    "onChange": {"action": "editComment"},
                                },
                            },
                        },
                        {
                            "header": "Subreddit",
                            "cell": {
                                "type": "link",
                                "props": {
                                    "text": "r/{{ source }}",
                                    "url": "https://www.reddit.com/r/{{ source }}/",
                                },
                            },
                        },
                        {
                            "header": "Upvotes",
                            "cell": {"type": "text", "props": {"text": "{{ score }}"}},
                        },
                        {
                            "header": "Comments",
                            "cell": {"type": "text", "props": {"text": "{{ commentCount }}"}},
                        },
                    ],
                },
            ),
            Component(
                type="button",
                props={
                    "text": "댓글 승인",
                    "onPress": {"action": "approve"},
                    "disabled": "{{ length(@ui.selected) == 0 }}",
                },
            ),
        ],
    )

    return UISpec(manifest=manifest, data=data, actions=actions, view=view)


if __name__ == "__main__":
    spec = build_spec()
    print(json.dumps(spec.model_dump(mode="json"), indent=2))
