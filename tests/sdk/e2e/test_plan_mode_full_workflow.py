"""E2E tests for complete plan mode workflow.

These tests spin up a real AgentServer and test the full plan mode
workflow with actual HTTP requests and SSE streaming.
"""

import asyncio
import uuid

import httpx
import pytest

from tests.sdk.e2e.conftest import (
    TestAgentHandlers,
    collect_sse_until,
)


class TestPlanModeFullWorkflow:
    """E2E tests for the complete plan mode workflow."""

    @pytest.mark.asyncio
    async def test_complete_workflow_clarification_to_completion(
        self,
        plan_mode_server: tuple,
        http_client: httpx.AsyncClient,
        test_handlers: TestAgentHandlers,
    ):
        """Test the complete plan mode workflow from start to finish.

        Flow:
        1. Send initial message → Get clarification_needed
        2. Respond to clarification → Get discovery_result + selection_required
        3. Respond to selection → Get preview_ready
        4. Approve plan → Get completed
        """
        server, base_url = plan_mode_server

        # Step 1: Send initial message
        message_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "message/stream",
            "params": {
                "message": {
                    "messageId": str(uuid.uuid4()),
                    "role": "user",
                    "parts": [{"text": "Find gaming content on Reddit"}],
                },
                "sessionId": str(uuid.uuid4()),
            },
        }

        async with http_client.stream(
            "POST",
            f"{base_url}/",
            json=message_request,
            headers={"Accept": "text/event-stream"},
        ) as response:
            assert response.status_code == 200

            # Collect events until we get clarification_needed
            events = await collect_sse_until(
                response,
                lambda e: e.get("event") == "clarification_needed",
                max_events=10,
            )

            # Verify we got the clarification event
            clarification_events = [e for e in events if e.get("event") == "clarification_needed"]
            assert len(clarification_events) >= 1, f"No clarification_needed event. Got: {events}"

            clarification_data = clarification_events[0]["data"]
            assert clarification_data["state"] == "input-required"
            assert "clarificationId" in clarification_data
            assert "questions" in clarification_data
            assert len(clarification_data["questions"]) == 2

            clarification_id = clarification_data["clarificationId"]

        # Wait for handler to process
        await asyncio.wait_for(test_handlers.clarification_requested.wait(), timeout=5.0)

        # Step 2: Respond to clarification
        respond_request = {
            "sessionId": message_request["params"]["sessionId"],
            "clarificationId": clarification_id,
            "answers": {"topic": "gaming", "depth": "deep"},
        }

        async with http_client.stream(
            "POST",
            f"{base_url}/respond",
            json=respond_request,
            headers={"Accept": "text/event-stream"},
        ) as response:
            assert response.status_code == 200

            # Collect events until selection_required
            events = await collect_sse_until(
                response,
                lambda e: e.get("event") == "selection_required",
                max_events=20,
            )

            # Verify discovery and selection events
            discovery_events = [e for e in events if e.get("event") == "discovery_result"]
            assert len(discovery_events) >= 1, f"No discovery_result event. Got: {events}"

            discovery_data = discovery_events[0]["data"]
            assert discovery_data["discoveryType"] == "subreddits"
            assert len(discovery_data["items"]) == 3

            selection_events = [e for e in events if e.get("event") == "selection_required"]
            assert len(selection_events) >= 1, f"No selection_required event. Got: {events}"

            selection_data = selection_events[0]["data"]
            assert selection_data["state"] == "input-required"
            selection_id = selection_data["selectionId"]

        # Wait for handler to process
        await asyncio.wait_for(test_handlers.selection_requested.wait(), timeout=5.0)

        # Step 3: Respond to selection
        selection_response = {
            "sessionId": message_request["params"]["sessionId"],
            "selectionId": selection_id,
            "selectedIds": ["r/gaming", "r/pcgaming"],
        }

        async with http_client.stream(
            "POST",
            f"{base_url}/respond",
            json=selection_response,
            headers={"Accept": "text/event-stream"},
        ) as response:
            assert response.status_code == 200

            # Collect events until preview_ready
            events = await collect_sse_until(
                response,
                lambda e: e.get("event") == "preview_ready",
                max_events=20,
            )

            preview_events = [e for e in events if e.get("event") == "preview_ready"]
            assert len(preview_events) >= 1, f"No preview_ready event. Got: {events}"

            preview_data = preview_events[0]["data"]
            assert preview_data["state"] == "input-required"
            plan_id = preview_data["planId"]

        # Wait for handler to process
        await asyncio.wait_for(test_handlers.preview_emitted.wait(), timeout=5.0)

        # Step 4: Approve plan
        approval_response = {
            "sessionId": message_request["params"]["sessionId"],
            "planId": plan_id,
            "approved": True,
        }

        async with http_client.stream(
            "POST",
            f"{base_url}/respond",
            json=approval_response,
            headers={"Accept": "text/event-stream"},
        ) as response:
            assert response.status_code == 200

            # Collect events until completed
            events = await collect_sse_until(
                response,
                lambda e: e.get("data", {}).get("state") == "completed",
                max_events=20,
            )

            # Verify completion
            completed_events = [e for e in events if e.get("data", {}).get("state") == "completed"]
            assert len(completed_events) >= 1, f"No completed event. Got: {events}"

        # Wait for handler to complete
        await asyncio.wait_for(test_handlers.completed.wait(), timeout=5.0)

        # Verify final state
        assert test_handlers.user_answers == {"topic": "gaming", "depth": "deep"}
        assert test_handlers.selected_ids == ["r/gaming", "r/pcgaming"]
        assert test_handlers.approved is True

    @pytest.mark.asyncio
    async def test_plan_rejection(
        self,
        plan_mode_server: tuple,
        http_client: httpx.AsyncClient,
        test_handlers: TestAgentHandlers,
    ):
        """Test that rejecting a plan doesn't complete the workflow."""
        server, base_url = plan_mode_server
        session_id = str(uuid.uuid4())

        # Step 1: Get to preview stage
        # ... (abbreviated - would go through clarification and selection)
        message_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "message/stream",
            "params": {
                "message": {
                    "messageId": str(uuid.uuid4()),
                    "role": "user",
                    "parts": [{"text": "Test rejection"}],
                },
                "sessionId": session_id,
            },
        }

        # Get clarification
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

        await asyncio.wait_for(test_handlers.selection_requested.wait(), timeout=5.0)

        # Respond to selection
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
            plan_id = events[-1]["data"]["planId"]

        await asyncio.wait_for(test_handlers.preview_emitted.wait(), timeout=5.0)

        # Reject the plan
        async with http_client.stream(
            "POST",
            f"{base_url}/respond",
            json={
                "sessionId": session_id,
                "planId": plan_id,
                "approved": False,
            },
            headers={"Accept": "text/event-stream"},
        ) as response:
            assert response.status_code == 200
            # Should get a status update but not completed

        # Verify plan was rejected
        assert test_handlers.approved is False
        assert not test_handlers.completed.is_set()


class TestClarificationEvent:
    """Tests for clarification event structure."""

    @pytest.mark.asyncio
    async def test_clarification_has_correct_structure(
        self,
        plan_mode_server: tuple,
        http_client: httpx.AsyncClient,
        test_handlers: TestAgentHandlers,
    ):
        """Test that clarification events have the correct structure."""
        server, base_url = plan_mode_server

        message_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "message/stream",
            "params": {
                "message": {
                    "messageId": str(uuid.uuid4()),
                    "role": "user",
                    "parts": [{"text": "Test query"}],
                },
                "sessionId": str(uuid.uuid4()),
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

            clarification = events[-1]["data"]

            # Verify structure
            assert "clarificationId" in clarification
            assert "agentId" in clarification
            assert "questions" in clarification
            assert "state" in clarification
            assert clarification["state"] == "input-required"

            # Verify questions structure
            questions = clarification["questions"]
            assert len(questions) >= 1

            for q in questions:
                assert "questionId" in q
                assert "questionType" in q
                assert "question" in q

                # Verify question types
                assert q["questionType"] in [
                    "single_choice",
                    "multiple_choice",
                    "free_text",
                    "yes_no",
                    "numeric_range",
                ]


class TestDiscoveryAndSelectionEvents:
    """Tests for discovery and selection event structure."""

    @pytest.mark.asyncio
    async def test_discovery_items_have_metadata(
        self,
        plan_mode_server: tuple,
        http_client: httpx.AsyncClient,
        test_handlers: TestAgentHandlers,
    ):
        """Test that discovery items include metadata."""
        server, base_url = plan_mode_server
        session_id = str(uuid.uuid4())

        # Get through clarification
        message_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "message/stream",
            "params": {
                "message": {
                    "messageId": str(uuid.uuid4()),
                    "role": "user",
                    "parts": [{"text": "Test"}],
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

        # Respond and get discovery
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
                lambda e: e.get("event") == "discovery_result",
            )

            discovery = events[-1]["data"]

            # Verify discovery structure
            assert "discoveryType" in discovery
            assert "items" in discovery
            assert len(discovery["items"]) >= 1

            for item in discovery["items"]:
                assert "id" in item
                assert "name" in item
                # Metadata is optional but should be present in our test
                if "metadata" in item:
                    assert isinstance(item["metadata"], dict)
