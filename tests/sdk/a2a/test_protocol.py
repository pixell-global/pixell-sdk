"""Tests for A2A Protocol types."""

import uuid
from pixell.sdk.a2a.protocol import (
    A2AMessage,
    TextPart,
    DataPart,
    FilePart,
    TaskState,
    TaskStatus,
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCError,
    SendMessageParams,
    RespondParams,
)


class TestTextPart:
    """Tests for TextPart."""

    def test_create_text_part(self):
        part = TextPart(text="Hello, world!")
        assert part.text == "Hello, world!"

    def test_to_dict(self):
        part = TextPart(text="Test message")
        assert part.to_dict() == {"text": "Test message"}

    def test_empty_text(self):
        part = TextPart(text="")
        assert part.text == ""
        assert part.to_dict() == {"text": ""}


class TestDataPart:
    """Tests for DataPart."""

    def test_create_data_part(self):
        part = DataPart(data={"key": "value"})
        assert part.data == {"key": "value"}
        assert part.mimeType == "application/json"

    def test_custom_mime_type(self):
        part = DataPart(data={"x": 1}, mimeType="application/custom+json")
        assert part.mimeType == "application/custom+json"

    def test_to_dict(self):
        part = DataPart(data={"nested": {"key": [1, 2, 3]}})
        result = part.to_dict()
        assert result["data"] == {"nested": {"key": [1, 2, 3]}}
        assert result["mimeType"] == "application/json"

    def test_complex_data(self):
        data = {
            "results": [
                {"id": 1, "name": "Test"},
                {"id": 2, "name": "Test2"},
            ],
            "meta": {"count": 2, "page": 1},
        }
        part = DataPart(data=data)
        assert part.to_dict()["data"]["results"][0]["id"] == 1


class TestFilePart:
    """Tests for FilePart."""

    def test_create_file_part(self):
        part = FilePart(file={"name": "test.txt", "mimeType": "text/plain", "uri": "file://test"})
        assert part.file["name"] == "test.txt"

    def test_to_dict(self):
        part = FilePart(
            file={"name": "doc.pdf", "mimeType": "application/pdf", "bytes": "base64data"}
        )
        result = part.to_dict()
        assert result["file"]["name"] == "doc.pdf"


class TestA2AMessage:
    """Tests for A2AMessage."""

    def test_create_user_message(self):
        msg = A2AMessage.user("Hello")
        assert msg.role == "user"
        assert msg.text == "Hello"
        assert len(msg.parts) == 1
        assert isinstance(msg.parts[0], TextPart)

    def test_create_agent_message(self):
        msg = A2AMessage.agent("Response")
        assert msg.role == "agent"
        assert msg.text == "Response"

    def test_create_agent_with_data(self):
        msg = A2AMessage.agent_with_data("Found results", {"count": 10})
        assert msg.role == "agent"
        assert msg.text == "Found results"
        assert len(msg.parts) == 2
        assert isinstance(msg.parts[0], TextPart)
        assert isinstance(msg.parts[1], DataPart)
        assert msg.parts[1].data == {"count": 10}

    def test_message_id_auto_generated(self):
        msg1 = A2AMessage.user("Test1")
        msg2 = A2AMessage.user("Test2")
        assert msg1.messageId != msg2.messageId
        # Should be valid UUIDs
        uuid.UUID(msg1.messageId)
        uuid.UUID(msg2.messageId)

    def test_custom_message_id(self):
        msg = A2AMessage(role="user", parts=[TextPart(text="Hi")], messageId="custom-id-123")
        assert msg.messageId == "custom-id-123"

    def test_text_property_concatenates(self):
        msg = A2AMessage(
            role="agent",
            parts=[
                TextPart(text="Part 1. "),
                DataPart(data={"x": 1}),
                TextPart(text="Part 2."),
            ],
        )
        assert msg.text == "Part 1. Part 2."

    def test_to_dict(self):
        msg = A2AMessage.user("Test message")
        result = msg.to_dict()
        assert result["role"] == "user"
        assert result["messageId"] is not None
        assert len(result["parts"]) == 1
        assert result["parts"][0]["text"] == "Test message"

    def test_to_dict_with_data(self):
        msg = A2AMessage.agent_with_data("Results", {"items": [1, 2, 3]})
        result = msg.to_dict()
        assert result["parts"][0]["text"] == "Results"
        assert result["parts"][1]["data"] == {"items": [1, 2, 3]}


class TestTaskState:
    """Tests for TaskState enum."""

    def test_all_states_exist(self):
        assert TaskState.WORKING.value == "working"
        assert TaskState.INPUT_REQUIRED.value == "input-required"
        assert TaskState.COMPLETED.value == "completed"
        assert TaskState.FAILED.value == "failed"
        assert TaskState.CANCELED.value == "canceled"

    def test_state_values_are_strings(self):
        for state in TaskState:
            assert isinstance(state.value, str)


class TestTaskStatus:
    """Tests for TaskStatus."""

    def test_create_status(self):
        status = TaskStatus(state=TaskState.WORKING)
        assert status.state == TaskState.WORKING
        assert status.message is None

    def test_status_with_message(self):
        msg = A2AMessage.agent("Processing...")
        status = TaskStatus(state=TaskState.WORKING, message=msg)
        assert status.message is not None
        assert status.message.text == "Processing..."

    def test_to_dict(self):
        status = TaskStatus(state=TaskState.COMPLETED)
        result = status.to_dict()
        assert result["state"] == "completed"
        assert "timestamp" in result

    def test_to_dict_with_message(self):
        msg = A2AMessage.agent("Done!")
        status = TaskStatus(state=TaskState.COMPLETED, message=msg)
        result = status.to_dict()
        assert result["message"]["parts"][0]["text"] == "Done!"


class TestJSONRPCError:
    """Tests for JSONRPCError."""

    def test_standard_error_codes(self):
        assert JSONRPCError.PARSE_ERROR == -32700
        assert JSONRPCError.INVALID_REQUEST == -32600
        assert JSONRPCError.METHOD_NOT_FOUND == -32601
        assert JSONRPCError.INVALID_PARAMS == -32602
        assert JSONRPCError.INTERNAL_ERROR == -32603

    def test_custom_error_codes(self):
        assert JSONRPCError.TASK_NOT_FOUND == -32000
        assert JSONRPCError.TASK_CANCELED == -32001
        assert JSONRPCError.INPUT_REQUIRED == -32002

    def test_create_error(self):
        error = JSONRPCError(code=-32600, message="Invalid request")
        assert error.code == -32600
        assert error.message == "Invalid request"
        assert error.data is None

    def test_error_with_data(self):
        error = JSONRPCError(
            code=-32602,
            message="Invalid params",
            data={"field": "name", "reason": "required"},
        )
        assert error.data["field"] == "name"

    def test_to_dict(self):
        error = JSONRPCError(code=-32603, message="Internal error")
        result = error.to_dict()
        assert result == {"code": -32603, "message": "Internal error"}

    def test_to_dict_with_data(self):
        error = JSONRPCError(code=-32000, message="Not found", data={"id": "123"})
        result = error.to_dict()
        assert result["data"] == {"id": "123"}


class TestJSONRPCRequest:
    """Tests for JSONRPCRequest."""

    def test_create_request(self):
        req = JSONRPCRequest(method="message/send", params={"message": {}})
        assert req.method == "message/send"
        assert req.jsonrpc == "2.0"

    def test_auto_generated_id(self):
        req1 = JSONRPCRequest(method="test", params={})
        req2 = JSONRPCRequest(method="test", params={})
        assert req1.id != req2.id

    def test_from_dict(self):
        data = {
            "jsonrpc": "2.0",
            "method": "message/stream",
            "params": {"sessionId": "abc"},
            "id": "req-123",
        }
        req = JSONRPCRequest.from_dict(data)
        assert req.method == "message/stream"
        assert req.params["sessionId"] == "abc"
        assert req.id == "req-123"

    def test_from_dict_minimal(self):
        data = {"method": "test"}
        req = JSONRPCRequest.from_dict(data)
        assert req.method == "test"
        assert req.params == {}

    def test_to_dict(self):
        req = JSONRPCRequest(method="respond", params={"answers": {}}, id="r1")
        result = req.to_dict()
        assert result["jsonrpc"] == "2.0"
        assert result["method"] == "respond"
        assert result["id"] == "r1"


class TestJSONRPCResponse:
    """Tests for JSONRPCResponse."""

    def test_success_response(self):
        resp = JSONRPCResponse.success("req-1", {"status": "ok"})
        assert resp.result == {"status": "ok"}
        assert resp.error is None
        assert resp.id == "req-1"

    def test_failure_response(self):
        error = JSONRPCError(code=-32600, message="Bad request")
        resp = JSONRPCResponse.failure("req-2", error)
        assert resp.result is None
        assert resp.error.code == -32600
        assert resp.id == "req-2"

    def test_to_dict_success(self):
        resp = JSONRPCResponse.success("r1", {"data": [1, 2, 3]})
        result = resp.to_dict()
        assert result["jsonrpc"] == "2.0"
        assert result["id"] == "r1"
        assert result["result"] == {"data": [1, 2, 3]}
        assert "error" not in result

    def test_to_dict_failure(self):
        error = JSONRPCError(code=-32603, message="Error")
        resp = JSONRPCResponse.failure("r2", error)
        result = resp.to_dict()
        assert result["error"]["code"] == -32603
        # Failure responses may include "result" key (as None) or omit it
        # depending on implementation. Check that error is present.
        assert "error" in result


class TestSendMessageParams:
    """Tests for SendMessageParams."""

    def test_from_dict_simple(self):
        data = {
            "message": {
                "messageId": "msg-1",
                "role": "user",
                "parts": [{"text": "Hello"}],
            }
        }
        params = SendMessageParams.from_dict(data)
        assert params.message.messageId == "msg-1"
        assert params.message.role == "user"
        assert params.message.text == "Hello"

    def test_from_dict_with_metadata(self):
        data = {
            "message": {
                "role": "user",
                "parts": [{"text": "Hi"}],
            },
            "sessionId": "sess-123",
            "metadata": {"language": "ko", "timezone": "Asia/Seoul"},
        }
        params = SendMessageParams.from_dict(data)
        assert params.sessionId == "sess-123"
        assert params.metadata["language"] == "ko"

    def test_from_dict_with_data_part(self):
        data = {
            "message": {
                "role": "user",
                "parts": [
                    {"text": "Here's the data"},
                    {"data": {"x": 1}, "mimeType": "application/json"},
                ],
            }
        }
        params = SendMessageParams.from_dict(data)
        assert len(params.message.parts) == 2
        assert isinstance(params.message.parts[1], DataPart)

    def test_from_dict_with_file_part(self):
        data = {
            "message": {
                "role": "user",
                "parts": [
                    {"file": {"name": "test.txt", "mimeType": "text/plain", "uri": "file://"}},
                ],
            }
        }
        params = SendMessageParams.from_dict(data)
        assert isinstance(params.message.parts[0], FilePart)


class TestRespondParams:
    """Tests for RespondParams."""

    def test_from_dict_clarification(self):
        data = {
            "clarificationId": "clarify-1",
            "answers": {"topic": "gaming", "depth": "moderate"},
        }
        params = RespondParams.from_dict(data)
        assert params.clarificationId == "clarify-1"
        assert params.answers["topic"] == "gaming"

    def test_from_dict_selection(self):
        data = {
            "selectionId": "select-1",
            "selectedIds": ["item-1", "item-2", "item-3"],
        }
        params = RespondParams.from_dict(data)
        assert params.selectionId == "select-1"
        assert len(params.selectedIds) == 3

    def test_from_dict_plan_approval(self):
        data = {
            "planId": "plan-1",
            "approved": True,
        }
        params = RespondParams.from_dict(data)
        assert params.planId == "plan-1"
        assert params.approved is True

    def test_from_dict_plan_rejection(self):
        data = {
            "planId": "plan-2",
            "approved": False,
        }
        params = RespondParams.from_dict(data)
        assert params.approved is False
