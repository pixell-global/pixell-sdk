import json
import pytest

from pixell.intent.validate import validate_intent_params


def test_validate_intent_params_ok(tmp_path):
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {"draftId": {"type": "string"}},
        "required": ["draftId"],
        "additionalProperties": False,
    }
    schema_path = tmp_path / "post_comment.schema.json"
    schema_path.write_text(json.dumps(schema))

    validate_intent_params("post_comment", {"draftId": "abc"}, str(schema_path))


def test_validate_intent_params_fail(tmp_path):
    # Schema requires a number type for draftId, but we pass a string
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {"draftId": {"type": "number"}},
        "required": ["draftId"],
        "additionalProperties": False,
    }
    schema_path = tmp_path / "post_comment.schema.json"
    schema_path.write_text(json.dumps(schema))

    with pytest.raises(Exception):
        validate_intent_params("post_comment", {"draftId": "abc"}, str(schema_path)) 