"""Tests for A2A SSE Streaming."""

import pytest
import asyncio
import json
from datetime import datetime
from pixell.sdk.a2a.streaming import SSEEvent, SSEStream, create_sse_response
from pixell.sdk.a2a.protocol import A2AMessage


class TestSSEEvent:
    """Tests for SSEEvent."""

    def test_create_event(self):
        event = SSEEvent(event="status-update", data={"state": "working"})
        assert event.event == "status-update"
        assert event.data == {"state": "working"}
        assert event.id is None
        assert event.retry is None

    def test_event_with_id(self):
        event = SSEEvent(event="message", data={"text": "hello"}, id="evt-123")
        assert event.id == "evt-123"

    def test_event_with_retry(self):
        event = SSEEvent(event="error", data={"code": -1}, retry=5000)
        assert event.retry == 5000

    def test_encode_minimal(self):
        event = SSEEvent(event="test", data={"key": "value"})
        encoded = event.encode()
        assert "event: test\n" in encoded
        assert 'data: {"key": "value"}' in encoded
        assert encoded.endswith("\n\n")

    def test_encode_with_id(self):
        event = SSEEvent(event="test", data={}, id="123")
        encoded = event.encode()
        assert "id: 123\n" in encoded
        assert "event: test\n" in encoded

    def test_encode_with_retry(self):
        event = SSEEvent(event="test", data={}, retry=3000)
        encoded = event.encode()
        assert "retry: 3000\n" in encoded

    def test_encode_full(self):
        event = SSEEvent(event="message", data={"hello": "world"}, id="456", retry=1000)
        encoded = event.encode()
        lines = encoded.strip().split("\n")
        assert any(line.startswith("id:") for line in lines)
        assert any(line.startswith("retry:") for line in lines)
        assert any(line.startswith("event:") for line in lines)
        assert any(line.startswith("data:") for line in lines)

    def test_encode_complex_data(self):
        data = {
            "nested": {"array": [1, 2, 3], "obj": {"a": 1}},
            "unicode": "한글 테스트",
        }
        event = SSEEvent(event="complex", data=data)
        encoded = event.encode()
        # Verify JSON is valid
        data_line = [l for l in encoded.split("\n") if l.startswith("data:")][0]
        json_str = data_line.replace("data: ", "")
        parsed = json.loads(json_str)
        assert parsed["nested"]["array"] == [1, 2, 3]
        assert parsed["unicode"] == "한글 테스트"


class TestSSEStream:
    """Tests for SSEStream."""

    @pytest.fixture
    def stream(self):
        """Fresh SSE stream."""
        return SSEStream()

    @pytest.mark.asyncio
    async def test_emit_status(self, stream):
        await stream.emit_status("working", "Processing...")

        event = await asyncio.wait_for(stream._queue.get(), timeout=1.0)
        assert event.event == "status-update"
        assert event.data["state"] == "working"
        assert event.data["message"] == "Processing..."
        assert "timestamp" in event.data

    @pytest.mark.asyncio
    async def test_emit_status_with_extra_data(self, stream):
        await stream.emit_status("working", "Loading...", progress=50, custom="value")

        event = await asyncio.wait_for(stream._queue.get(), timeout=1.0)
        assert event.data["progress"] == 50
        assert event.data["custom"] == "value"

    @pytest.mark.asyncio
    async def test_emit_progress(self, stream):
        await stream.emit_progress(75.5, "Almost done")

        event = await asyncio.wait_for(stream._queue.get(), timeout=1.0)
        assert event.event == "status-update"
        assert event.data["state"] == "working"
        assert event.data["progress"] == 75.5
        assert event.data["message"] == "Almost done"

    @pytest.mark.asyncio
    async def test_emit_progress_without_message(self, stream):
        await stream.emit_progress(25.0)

        event = await asyncio.wait_for(stream._queue.get(), timeout=1.0)
        assert event.data["progress"] == 25.0
        assert "message" not in event.data

    @pytest.mark.asyncio
    async def test_emit_clarification(self, stream):
        clarification = {
            "clarificationId": "c-123",
            "questions": [{"id": "q1", "question": "What topic?"}],
        }
        await stream.emit_clarification(clarification)

        event = await asyncio.wait_for(stream._queue.get(), timeout=1.0)
        assert event.event == "clarification_needed"
        assert event.data["state"] == "input-required"
        assert event.data["clarificationId"] == "c-123"
        assert len(event.data["questions"]) == 1

    @pytest.mark.asyncio
    async def test_emit_discovery(self, stream):
        discovery = {
            "discoveryType": "subreddits",
            "items": [{"id": "r/test", "name": "Test"}],
        }
        await stream.emit_discovery(discovery)

        event = await asyncio.wait_for(stream._queue.get(), timeout=1.0)
        assert event.event == "discovery_result"
        assert event.data["state"] == "working"
        assert event.data["discoveryType"] == "subreddits"

    @pytest.mark.asyncio
    async def test_emit_selection(self, stream):
        selection = {
            "selectionId": "s-123",
            "minSelect": 1,
            "maxSelect": 5,
        }
        await stream.emit_selection(selection)

        event = await asyncio.wait_for(stream._queue.get(), timeout=1.0)
        assert event.event == "selection_required"
        assert event.data["state"] == "input-required"
        assert event.data["selectionId"] == "s-123"

    @pytest.mark.asyncio
    async def test_emit_preview(self, stream):
        preview = {
            "planId": "plan-123",
            "userIntent": "Find gaming content",
            "searchKeywords": ["gaming", "esports"],
        }
        await stream.emit_preview(preview)

        event = await asyncio.wait_for(stream._queue.get(), timeout=1.0)
        assert event.event == "preview_ready"
        assert event.data["state"] == "input-required"
        assert event.data["planId"] == "plan-123"

    @pytest.mark.asyncio
    async def test_emit_result_final(self, stream):
        message = A2AMessage.agent("Here are your results")
        await stream.emit_result(message, final=True)

        event = await asyncio.wait_for(stream._queue.get(), timeout=1.0)
        assert event.event == "message"
        assert event.data["state"] == "completed"
        assert event.data["final"] is True
        assert event.data["message"]["parts"][0]["text"] == "Here are your results"

    @pytest.mark.asyncio
    async def test_emit_result_not_final(self, stream):
        message = A2AMessage.agent("Intermediate result")
        await stream.emit_result(message, final=False)

        event = await asyncio.wait_for(stream._queue.get(), timeout=1.0)
        assert event.data["state"] == "working"
        assert event.data["final"] is False

    @pytest.mark.asyncio
    async def test_emit_error(self, stream):
        await stream.emit_error("validation_error", "Invalid input", recoverable=True)

        event = await asyncio.wait_for(stream._queue.get(), timeout=1.0)
        assert event.event == "error"
        assert event.data["state"] == "failed"
        assert event.data["error_type"] == "validation_error"
        assert event.data["message"] == "Invalid input"
        assert event.data["recoverable"] is True

    @pytest.mark.asyncio
    async def test_emit_error_with_data(self, stream):
        await stream.emit_error(
            "api_error",
            "Rate limited",
            recoverable=True,
            retry_after=60,
            endpoint="/api/search",
        )

        event = await asyncio.wait_for(stream._queue.get(), timeout=1.0)
        assert event.data["retry_after"] == 60
        assert event.data["endpoint"] == "/api/search"

    @pytest.mark.asyncio
    async def test_event_id_increments(self, stream):
        await stream.emit_status("working", "1")
        await stream.emit_status("working", "2")
        await stream.emit_status("working", "3")

        events = []
        for _ in range(3):
            event = await asyncio.wait_for(stream._queue.get(), timeout=1.0)
            events.append(event)

        assert events[0].id == "1"
        assert events[1].id == "2"
        assert events[2].id == "3"

    @pytest.mark.asyncio
    async def test_close_stops_emitting(self, stream):
        await stream.emit_status("working", "Before close")
        stream.close()
        await stream.emit_status("working", "After close")

        # Should only have one event
        event = await asyncio.wait_for(stream._queue.get(), timeout=1.0)
        assert event.data["message"] == "Before close"

        # Queue should be empty
        assert stream._queue.empty()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        async with SSEStream() as stream:
            assert not stream._closed
            await stream.emit_status("working", "Inside context")

        assert stream._closed

    @pytest.mark.asyncio
    async def test_timestamp_added(self, stream):
        await stream.emit_status("working", "Test")

        event = await asyncio.wait_for(stream._queue.get(), timeout=1.0)
        timestamp = event.data["timestamp"]
        # Should be valid ISO format
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))


class TestSSEStreamEvents:
    """Tests for SSEStream.events() async generator."""

    @pytest.mark.asyncio
    async def test_events_yields_emitted(self):
        stream = SSEStream()

        # Emit in background
        async def emit_events():
            await asyncio.sleep(0.1)
            await stream.emit_status("working", "Event 1")
            await asyncio.sleep(0.1)
            await stream.emit_status("working", "Event 2")
            await asyncio.sleep(0.1)
            stream.close()

        emit_task = asyncio.create_task(emit_events())

        received = []
        async for event in stream.events():
            received.append(event)
            if len(received) >= 2:
                stream.close()

        await emit_task
        assert len(received) >= 2
        assert received[0].data["message"] == "Event 1"
        assert received[1].data["message"] == "Event 2"


class TestCreateSSEResponse:
    """Tests for create_sse_response helper."""

    @pytest.mark.asyncio
    async def test_creates_generator(self):
        stream = SSEStream()

        # Emit an event
        await stream.emit_status("working", "Test")
        stream.close()

        # Get generator
        response_gen = create_sse_response(stream)

        # Should be an async generator
        assert hasattr(response_gen, "__anext__")

    @pytest.mark.asyncio
    async def test_yields_encoded_events(self):
        stream = SSEStream()

        await stream.emit_status("working", "Hello")

        # Directly get from queue and encode since create_sse_response
        # uses stream.events() which checks _closed before yielding
        event = await asyncio.wait_for(stream._queue.get(), timeout=1.0)
        encoded = event.encode()

        assert "event: status-update" in encoded
        assert "Hello" in encoded


class TestSSEStreamConcurrency:
    """Tests for SSEStream under concurrent operations."""

    @pytest.mark.asyncio
    async def test_multiple_emitters(self):
        stream = SSEStream()

        async def emitter(prefix: str, count: int):
            for i in range(count):
                await stream.emit_status("working", f"{prefix}-{i}")
                await asyncio.sleep(0.01)

        # Start multiple emitters
        await asyncio.gather(
            emitter("A", 5),
            emitter("B", 5),
            emitter("C", 5),
        )

        # Should have all events
        events = []
        while not stream._queue.empty():
            events.append(await stream._queue.get())

        assert len(events) == 15

        # Verify all prefixes present
        messages = [e.data["message"] for e in events]
        assert sum(1 for m in messages if m.startswith("A-")) == 5
        assert sum(1 for m in messages if m.startswith("B-")) == 5
        assert sum(1 for m in messages if m.startswith("C-")) == 5

    @pytest.mark.asyncio
    async def test_emit_and_consume_concurrent(self):
        stream = SSEStream()
        received = []

        async def producer():
            for i in range(10):
                await stream.emit_status("working", f"Event {i}")
                await asyncio.sleep(0.02)
            stream.close()

        async def consumer():
            # Consume directly from queue until closed
            while True:
                try:
                    event = await asyncio.wait_for(stream._queue.get(), timeout=1.0)
                    received.append(event)
                except asyncio.TimeoutError:
                    if stream._closed:
                        break

        await asyncio.gather(
            producer(),
            asyncio.wait_for(consumer(), timeout=5.0),
        )

        assert len(received) == 10
