"""Tests for A2A Handlers."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from pixell.sdk.a2a.handlers import (
    MessageContext,
    ResponseContext,
    A2AHandler,
)
from pixell.sdk.a2a.protocol import (
    A2AMessage,
    JSONRPCRequest,
    JSONRPCError,
)
from pixell.sdk.a2a.streaming import SSEStream


class TestMessageContext:
    """Tests for MessageContext."""

    @pytest.fixture
    def stream(self):
        return SSEStream()

    @pytest.fixture
    def message(self):
        return A2AMessage.user("Hello, agent!")

    def test_create_context(self, message, stream):
        ctx = MessageContext(
            message=message,
            session_id="sess-123",
            stream=stream,
        )
        assert ctx.message == message
        assert ctx.session_id == "sess-123"
        assert ctx.metadata == {}
        assert ctx.plan_mode is None
        assert ctx.translation is None

    def test_text_property(self, message, stream):
        ctx = MessageContext(message=message, session_id="s1", stream=stream)
        assert ctx.text == "Hello, agent!"

    def test_user_language_default(self, message, stream):
        ctx = MessageContext(message=message, session_id="s1", stream=stream)
        assert ctx.user_language == "en"

    def test_user_language_from_metadata(self, message, stream):
        ctx = MessageContext(
            message=message,
            session_id="s1",
            stream=stream,
            metadata={"language": "ko"},
        )
        assert ctx.user_language == "ko"

    @pytest.mark.asyncio
    async def test_emit_status(self, message, stream):
        ctx = MessageContext(message=message, session_id="s1", stream=stream)
        await ctx.emit_status("working", "Processing...")

        event = await asyncio.wait_for(stream._queue.get(), timeout=1.0)
        assert event.event == "status-update"
        assert event.data["state"] == "working"
        assert event.data["message"] == "Processing..."

    @pytest.mark.asyncio
    async def test_emit_status_with_extra(self, message, stream):
        ctx = MessageContext(message=message, session_id="s1", stream=stream)
        await ctx.emit_status("working", "Step 2", step=2, total=5)

        event = await asyncio.wait_for(stream._queue.get(), timeout=1.0)
        assert event.data["step"] == 2
        assert event.data["total"] == 5

    @pytest.mark.asyncio
    async def test_emit_progress(self, message, stream):
        ctx = MessageContext(message=message, session_id="s1", stream=stream)
        await ctx.emit_progress(50.0, "Halfway there")

        event = await asyncio.wait_for(stream._queue.get(), timeout=1.0)
        assert event.data["progress"] == 50.0
        assert event.data["message"] == "Halfway there"

    @pytest.mark.asyncio
    async def test_emit_result_text_only(self, message, stream):
        ctx = MessageContext(message=message, session_id="s1", stream=stream)
        await ctx.emit_result("Here are your results")

        event = await asyncio.wait_for(stream._queue.get(), timeout=1.0)
        assert event.event == "message"
        assert event.data["message"]["role"] == "agent"
        assert event.data["message"]["parts"][0]["text"] == "Here are your results"

    @pytest.mark.asyncio
    async def test_emit_result_with_data(self, message, stream):
        ctx = MessageContext(message=message, session_id="s1", stream=stream)
        await ctx.emit_result("Found 10 items", {"count": 10, "items": [1, 2, 3]})

        event = await asyncio.wait_for(stream._queue.get(), timeout=1.0)
        msg_data = event.data["message"]
        assert len(msg_data["parts"]) == 2
        assert msg_data["parts"][0]["text"] == "Found 10 items"
        assert msg_data["parts"][1]["data"]["count"] == 10


class TestResponseContext:
    """Tests for ResponseContext."""

    @pytest.fixture
    def stream(self):
        return SSEStream()

    def test_create_clarification_context(self, stream):
        ctx = ResponseContext(
            session_id="s1",
            stream=stream,
            clarification_id="c-123",
            answers={"topic": "gaming"},
        )
        assert ctx.response_type == "clarification"
        assert ctx.clarification_id == "c-123"
        assert ctx.answers == {"topic": "gaming"}

    def test_create_selection_context(self, stream):
        ctx = ResponseContext(
            session_id="s1",
            stream=stream,
            selection_id="sel-456",
            selected_ids=["item-1", "item-2"],
        )
        assert ctx.response_type == "selection"
        assert ctx.selection_id == "sel-456"
        assert ctx.selected_ids == ["item-1", "item-2"]

    def test_create_plan_context(self, stream):
        ctx = ResponseContext(
            session_id="s1",
            stream=stream,
            plan_id="plan-789",
            approved=True,
        )
        assert ctx.response_type == "plan"
        assert ctx.plan_id == "plan-789"
        assert ctx.approved is True

    def test_unknown_response_type(self, stream):
        ctx = ResponseContext(session_id="s1", stream=stream)
        assert ctx.response_type == "unknown"

    @pytest.mark.asyncio
    async def test_emit_status(self, stream):
        ctx = ResponseContext(session_id="s1", stream=stream)
        await ctx.emit_status("working", "Applying changes...")

        event = await asyncio.wait_for(stream._queue.get(), timeout=1.0)
        assert event.data["message"] == "Applying changes..."

    @pytest.mark.asyncio
    async def test_emit_result(self, stream):
        ctx = ResponseContext(session_id="s1", stream=stream)
        await ctx.emit_result("Selection processed")

        event = await asyncio.wait_for(stream._queue.get(), timeout=1.0)
        assert event.data["message"]["parts"][0]["text"] == "Selection processed"


class TestA2AHandler:
    """Tests for A2AHandler."""

    @pytest.fixture
    def handler(self):
        return A2AHandler()

    @pytest.fixture
    def stream(self):
        return SSEStream()

    def test_register_message_handler(self, handler):
        @handler.on_message
        async def handle(ctx: MessageContext):
            pass

        assert handler._message_handler is not None

    def test_register_respond_handler(self, handler):
        @handler.on_respond
        async def handle(ctx: ResponseContext):
            pass

        assert handler._respond_handler is not None

    def test_decorator_returns_function(self, handler):
        @handler.on_message
        async def my_handler(ctx: MessageContext):
            return "test"

        assert my_handler.__name__ == "my_handler"

    @pytest.mark.asyncio
    async def test_handle_message_send(self, handler, stream):
        received_ctx = None

        @handler.on_message
        async def handle(ctx: MessageContext):
            nonlocal received_ctx
            received_ctx = ctx
            await ctx.emit_status("working", "Processing")

        request = JSONRPCRequest(
            method="message/send",
            params={
                "message": {
                    "messageId": "msg-1",
                    "role": "user",
                    "parts": [{"text": "Hello"}],
                },
                "sessionId": "sess-abc",
                "metadata": {"language": "ko"},
            },
            id="req-1",
        )

        response = await handler.handle_request(request, stream)

        assert response.error is None
        assert response.result["sessionId"] == "sess-abc"
        assert received_ctx is not None
        assert received_ctx.text == "Hello"
        assert received_ctx.session_id == "sess-abc"
        assert received_ctx.user_language == "ko"

    @pytest.mark.asyncio
    async def test_handle_message_stream(self, handler, stream):
        @handler.on_message
        async def handle(ctx: MessageContext):
            await ctx.emit_status("working", "Done")

        request = JSONRPCRequest(
            method="message/stream",
            params={
                "message": {"role": "user", "parts": [{"text": "Test"}]},
            },
            id="req-2",
        )

        response = await handler.handle_request(request, stream)
        assert response.error is None

    @pytest.mark.asyncio
    async def test_handle_respond_clarification(self, handler, stream):
        received_ctx = None

        @handler.on_respond
        async def handle(ctx: ResponseContext):
            nonlocal received_ctx
            received_ctx = ctx

        request = JSONRPCRequest(
            method="respond",
            params={
                "clarificationId": "c-123",
                "answers": {"topic": "gaming", "depth": "moderate"},
                "sessionId": "sess-xyz",
            },
            id="req-3",
        )

        response = await handler.handle_request(request, stream)

        assert response.error is None
        assert received_ctx is not None
        assert received_ctx.response_type == "clarification"
        assert received_ctx.clarification_id == "c-123"
        assert received_ctx.answers["topic"] == "gaming"

    @pytest.mark.asyncio
    async def test_handle_respond_selection(self, handler, stream):
        received_ctx = None

        @handler.on_respond
        async def handle(ctx: ResponseContext):
            nonlocal received_ctx
            received_ctx = ctx

        request = JSONRPCRequest(
            method="respond",
            params={
                "selectionId": "sel-456",
                "selectedIds": ["r/gaming", "r/pcgaming"],
            },
            id="req-4",
        )

        response = await handler.handle_request(request, stream)

        assert response.error is None
        assert received_ctx.response_type == "selection"
        assert received_ctx.selected_ids == ["r/gaming", "r/pcgaming"]

    @pytest.mark.asyncio
    async def test_handle_respond_plan_approval(self, handler, stream):
        received_ctx = None

        @handler.on_respond
        async def handle(ctx: ResponseContext):
            nonlocal received_ctx
            received_ctx = ctx

        request = JSONRPCRequest(
            method="respond",
            params={
                "planId": "plan-789",
                "approved": True,
            },
            id="req-5",
        )

        response = await handler.handle_request(request, stream)

        assert response.error is None
        assert received_ctx.response_type == "plan"
        assert received_ctx.approved is True

    @pytest.mark.asyncio
    async def test_handle_unknown_method(self, handler, stream):
        request = JSONRPCRequest(
            method="unknown/method",
            params={},
            id="req-err",
        )

        response = await handler.handle_request(request, stream)

        assert response.error is not None
        assert response.error.code == JSONRPCError.METHOD_NOT_FOUND
        assert "unknown/method" in response.error.message

    @pytest.mark.asyncio
    async def test_handle_no_message_handler(self, handler, stream):
        # No handler registered
        request = JSONRPCRequest(
            method="message/send",
            params={
                "message": {"role": "user", "parts": [{"text": "Test"}]},
            },
            id="req-no-handler",
        )

        response = await handler.handle_request(request, stream)

        assert response.error is not None
        assert response.error.code == JSONRPCError.INTERNAL_ERROR
        assert "No message handler" in response.error.message

    @pytest.mark.asyncio
    async def test_handle_no_respond_handler(self, handler, stream):
        request = JSONRPCRequest(
            method="respond",
            params={"clarificationId": "c-1", "answers": {}},
            id="req-no-respond",
        )

        response = await handler.handle_request(request, stream)

        assert response.error is not None
        assert "No respond handler" in response.error.message

    @pytest.mark.asyncio
    async def test_handler_exception_caught(self, handler, stream):
        @handler.on_message
        async def handle(ctx: MessageContext):
            raise ValueError("Something went wrong")

        request = JSONRPCRequest(
            method="message/send",
            params={
                "message": {"role": "user", "parts": [{"text": "Test"}]},
            },
            id="req-exc",
        )

        response = await handler.handle_request(request, stream)

        assert response.error is not None
        assert response.error.code == JSONRPCError.INTERNAL_ERROR
        assert "Something went wrong" in response.error.message

    @pytest.mark.asyncio
    async def test_session_id_auto_generated(self, handler, stream):
        @handler.on_message
        async def handle(ctx: MessageContext):
            pass

        request = JSONRPCRequest(
            method="message/send",
            params={
                "message": {"role": "user", "parts": [{"text": "Test"}]},
                # No sessionId provided
            },
            id="req-auto-sess",
        )

        response = await handler.handle_request(request, stream)

        assert response.result["sessionId"] is not None
        assert len(response.result["sessionId"]) > 0


class TestA2AHandlerWithContexts:
    """Tests for A2AHandler with plan_mode and translation contexts."""

    @pytest.fixture
    def handler(self):
        return A2AHandler()

    @pytest.fixture
    def stream(self):
        return SSEStream()

    @pytest.mark.asyncio
    async def test_plan_mode_passed_to_context(self, handler, stream):
        mock_plan_mode = MagicMock()
        received_plan_mode = None

        @handler.on_message
        async def handle(ctx: MessageContext):
            nonlocal received_plan_mode
            received_plan_mode = ctx.plan_mode

        request = JSONRPCRequest(
            method="message/send",
            params={"message": {"role": "user", "parts": [{"text": "Test"}]}},
            id="req-pm",
        )

        await handler.handle_request(request, stream, plan_mode=mock_plan_mode)

        assert received_plan_mode is mock_plan_mode

    @pytest.mark.asyncio
    async def test_translation_passed_to_context(self, handler, stream):
        mock_translation = MagicMock()
        received_translation = None

        @handler.on_message
        async def handle(ctx: MessageContext):
            nonlocal received_translation
            received_translation = ctx.translation

        request = JSONRPCRequest(
            method="message/send",
            params={"message": {"role": "user", "parts": [{"text": "Test"}]}},
            id="req-trans",
        )

        await handler.handle_request(request, stream, translation=mock_translation)

        assert received_translation is mock_translation

    @pytest.mark.asyncio
    async def test_respond_with_both_contexts(self, handler, stream):
        mock_plan_mode = MagicMock()
        mock_translation = MagicMock()

        @handler.on_respond
        async def handle(ctx: ResponseContext):
            assert ctx.plan_mode is mock_plan_mode
            assert ctx.translation is mock_translation

        request = JSONRPCRequest(
            method="respond",
            params={"clarificationId": "c-1", "answers": {}},
            id="req-both",
        )

        response = await handler.handle_request(
            request, stream, plan_mode=mock_plan_mode, translation=mock_translation
        )

        assert response.error is None


class TestA2AHandlerIntegration:
    """Integration tests for A2AHandler with real workflow."""

    @pytest.mark.asyncio
    async def test_full_message_flow(self):
        handler = A2AHandler()
        stream = SSEStream()

        @handler.on_message
        async def handle(ctx: MessageContext):
            await ctx.emit_status("working", "Analyzing request...")
            await ctx.emit_progress(25.0, "Step 1/4")
            await ctx.emit_progress(50.0, "Step 2/4")
            await ctx.emit_progress(75.0, "Step 3/4")
            await ctx.emit_result("Here are your results", {"items": [1, 2, 3]})

        request = JSONRPCRequest(
            method="message/send",
            params={"message": {"role": "user", "parts": [{"text": "Test"}]}},
            id="req-full",
        )

        response = await handler.handle_request(request, stream)

        assert response.error is None

        # Collect all events from queue after handler completes
        events = []
        while not stream._queue.empty():
            events.append(await stream._queue.get())

        assert len(events) == 5  # 1 status + 3 progress + 1 result

        # Verify event sequence
        assert events[0].event == "status-update"
        assert events[1].data["progress"] == 25.0
        assert events[2].data["progress"] == 50.0
        assert events[3].data["progress"] == 75.0
        assert events[4].event == "message"

    @pytest.mark.asyncio
    async def test_clarification_respond_flow(self):
        handler = A2AHandler()
        stream = SSEStream()

        clarification_answers = None
        selected_items = None

        @handler.on_respond
        async def handle(ctx: ResponseContext):
            nonlocal clarification_answers, selected_items

            if ctx.response_type == "clarification":
                clarification_answers = ctx.answers
                await ctx.emit_status("working", "Got answers, searching...")

            elif ctx.response_type == "selection":
                selected_items = ctx.selected_ids
                await ctx.emit_result("Selection applied!", {"count": len(ctx.selected_ids)})

        # First: clarification response
        clarify_request = JSONRPCRequest(
            method="respond",
            params={
                "clarificationId": "c-1",
                "answers": {"topic": "gaming", "depth": "deep"},
            },
            id="req-clarify",
        )

        response1 = await handler.handle_request(clarify_request, stream)
        assert response1.error is None
        assert clarification_answers == {"topic": "gaming", "depth": "deep"}

        # Second: selection response
        select_request = JSONRPCRequest(
            method="respond",
            params={
                "selectionId": "sel-1",
                "selectedIds": ["item-a", "item-b", "item-c"],
            },
            id="req-select",
        )

        response2 = await handler.handle_request(select_request, stream)
        assert response2.error is None
        assert selected_items == ["item-a", "item-b", "item-c"]
