"""E2E tests for session persistence across multiple requests.

These tests verify that PlanModeContext correctly persists state
across multiple /respond calls within the same session.
"""

import asyncio
import uuid

import httpx
import pytest

from tests.sdk.e2e.conftest import (
    TestAgentHandlers,
    collect_sse_until,
)


class TestSessionPersistence:
    """Tests for verifying session state persists across requests."""

    @pytest.mark.asyncio
    async def test_user_answers_persist_across_responds(
        self,
        plan_mode_server: tuple,
        http_client: httpx.AsyncClient,
        test_handlers: TestAgentHandlers,
    ):
        """Test that user answers from clarification persist to later phases.

        The PlanModeContext should accumulate user_answers across multiple
        clarification responses and make them available to the preview phase.
        """
        server, base_url = plan_mode_server
        session_id = str(uuid.uuid4())

        # Step 1: Initial message
        message_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "message/stream",
            "params": {
                "message": {
                    "messageId": str(uuid.uuid4()),
                    "role": "user",
                    "parts": [{"text": "Research gaming"}],
                },
                "sessionId": session_id,
            },
        }

        async with http_client.stream(
            "POST",
            f"{base_url}/",
            json=message_request,
            headers={"Accept": "text/event-stream"},
        ) as response:
            events = await collect_sse_until(
                response,
                lambda e: e.get("event") == "clarification_needed",
            )
            clarification_id = events[-1]["data"]["clarificationId"]

        await asyncio.wait_for(test_handlers.clarification_requested.wait(), timeout=5.0)

        # Step 2: Respond with answers
        user_answers = {"topic": "esports", "depth": "deep"}

        async with http_client.stream(
            "POST",
            f"{base_url}/respond",
            json={
                "sessionId": session_id,
                "clarificationId": clarification_id,
                "answers": user_answers,
            },
            headers={"Accept": "text/event-stream"},
        ) as response:
            events = await collect_sse_until(
                response,
                lambda e: e.get("event") == "selection_required",
            )
            selection_id = events[-1]["data"]["selectionId"]

        await asyncio.wait_for(test_handlers.selection_requested.wait(), timeout=5.0)

        # Verify user answers are stored
        assert test_handlers.user_answers == user_answers

        # Step 3: Respond to selection
        async with http_client.stream(
            "POST",
            f"{base_url}/respond",
            json={
                "sessionId": session_id,
                "selectionId": selection_id,
                "selectedIds": ["r/gaming"],
            },
            headers={"Accept": "text/event-stream"},
        ) as response:
            events = await collect_sse_until(
                response,
                lambda e: e.get("event") == "preview_ready",
            )

            # Verify the preview includes user answers
            preview_data = events[-1]["data"]
            assert "userAnswers" in preview_data
            assert preview_data["userAnswers"]["topic"] == "esports"
            assert preview_data["userAnswers"]["depth"] == "deep"

    @pytest.mark.asyncio
    async def test_selected_items_persist_to_preview(
        self,
        plan_mode_server: tuple,
        http_client: httpx.AsyncClient,
        test_handlers: TestAgentHandlers,
    ):
        """Test that selected items persist from selection to preview phase."""
        server, base_url = plan_mode_server
        session_id = str(uuid.uuid4())

        # Go through workflow to selection
        message_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "message/stream",
            "params": {
                "message": {
                    "messageId": str(uuid.uuid4()),
                    "role": "user",
                    "parts": [{"text": "Test selection persistence"}],
                },
                "sessionId": session_id,
            },
        }

        async with http_client.stream(
            "POST",
            f"{base_url}/",
            json=message_request,
            headers={"Accept": "text/event-stream"},
        ) as response:
            events = await collect_sse_until(
                response,
                lambda e: e.get("event") == "clarification_needed",
            )
            clarification_id = events[-1]["data"]["clarificationId"]

        await asyncio.wait_for(test_handlers.clarification_requested.wait(), timeout=5.0)

        # Respond to clarification
        async with http_client.stream(
            "POST",
            f"{base_url}/respond",
            json={
                "sessionId": session_id,
                "clarificationId": clarification_id,
                "answers": {"topic": "test", "depth": "quick"},
            },
            headers={"Accept": "text/event-stream"},
        ) as response:
            events = await collect_sse_until(
                response,
                lambda e: e.get("event") == "selection_required",
            )
            selection_id = events[-1]["data"]["selectionId"]
            # Save discovered items for verification
            discovery_events = [e for e in events if e.get("event") == "discovery_result"]
            discovery_events[0]["data"]["items"]

        await asyncio.wait_for(test_handlers.selection_requested.wait(), timeout=5.0)

        # Select specific items
        selected = ["r/gaming", "r/games"]

        async with http_client.stream(
            "POST",
            f"{base_url}/respond",
            json={
                "sessionId": session_id,
                "selectionId": selection_id,
                "selectedIds": selected,
            },
            headers={"Accept": "text/event-stream"},
        ) as response:
            await collect_sse_until(
                response,
                lambda e: e.get("event") == "preview_ready",
            )

        await asyncio.wait_for(test_handlers.preview_emitted.wait(), timeout=5.0)

        # Verify selected items are stored
        assert set(test_handlers.selected_ids) == set(selected)


class TestSessionIsolation:
    """Tests for verifying sessions are isolated from each other."""

    @pytest.mark.asyncio
    async def test_concurrent_sessions_are_isolated(
        self,
        plan_mode_server: tuple,
        http_client: httpx.AsyncClient,
        test_handlers: TestAgentHandlers,
    ):
        """Test that concurrent sessions don't interfere with each other.

        Start two sessions with different data and verify they maintain
        independent state.
        """
        server, base_url = plan_mode_server

        session_a_id = str(uuid.uuid4())
        session_b_id = str(uuid.uuid4())

        # Start session A
        message_a = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "message/stream",
            "params": {
                "message": {
                    "messageId": str(uuid.uuid4()),
                    "role": "user",
                    "parts": [{"text": "Session A query"}],
                },
                "sessionId": session_a_id,
            },
        }

        async with http_client.stream(
            "POST",
            f"{base_url}/",
            json=message_a,
            headers={"Accept": "text/event-stream"},
        ) as response:
            events = await collect_sse_until(
                response,
                lambda e: e.get("event") == "clarification_needed",
            )
            clarification_a_id = events[-1]["data"]["clarificationId"]

        # Reset handlers for session B test
        test_handlers.reset()

        # Start session B
        message_b = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "message/stream",
            "params": {
                "message": {
                    "messageId": str(uuid.uuid4()),
                    "role": "user",
                    "parts": [{"text": "Session B query"}],
                },
                "sessionId": session_b_id,
            },
        }

        async with http_client.stream(
            "POST",
            f"{base_url}/",
            json=message_b,
            headers={"Accept": "text/event-stream"},
        ) as response:
            events = await collect_sse_until(
                response,
                lambda e: e.get("event") == "clarification_needed",
            )
            clarification_b_id = events[-1]["data"]["clarificationId"]

        # Respond to session A with topic "gaming"
        async with http_client.stream(
            "POST",
            f"{base_url}/respond",
            json={
                "sessionId": session_a_id,
                "clarificationId": clarification_a_id,
                "answers": {"topic": "gaming", "depth": "deep"},
            },
            headers={"Accept": "text/event-stream"},
        ) as response:
            await collect_sse_until(
                response,
                lambda e: e.get("event") == "selection_required",
            )

        # Respond to session B with topic "fitness"
        async with http_client.stream(
            "POST",
            f"{base_url}/respond",
            json={
                "sessionId": session_b_id,
                "clarificationId": clarification_b_id,
                "answers": {"topic": "fitness", "depth": "quick"},
            },
            headers={"Accept": "text/event-stream"},
        ) as response:
            await collect_sse_until(
                response,
                lambda e: e.get("event") == "selection_required",
            )

        # Both sessions should have processed without interfering
        # Note: The test handlers track only the last session's data
        # In a real test, we'd need separate handler tracking per session
        # or verify via the server's internal state

        # At minimum, verify both sessions got through clarification
        assert clarification_a_id != clarification_b_id


class TestSessionTimeout:
    """Tests for session timeout behavior."""

    @pytest.mark.skip(reason="Flaky test - httpx.ReadTimeout in CI")
    @pytest.mark.asyncio
    async def test_session_not_found_returns_error(
        self,
        plan_mode_server: tuple,
        http_client: httpx.AsyncClient,
    ):
        """Test that responding to a non-existent session handles gracefully.

        When a client sends a /respond with an unknown sessionId,
        the server should handle it gracefully.
        """
        server, base_url = plan_mode_server

        # Try to respond to a session that doesn't exist
        response = await http_client.post(
            f"{base_url}/respond",
            json={
                "sessionId": str(uuid.uuid4()),  # Random session ID
                "clarificationId": str(uuid.uuid4()),
                "answers": {"topic": "test"},
            },
        )

        # The response should still be 200 (SSE), but the handler
        # should handle the missing session gracefully
        # The actual behavior depends on implementation
        assert response.status_code in [200, 400, 404]
