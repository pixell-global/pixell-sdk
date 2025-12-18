"""E2E tests for agent card endpoint.

Tests verify that the .well-known/agent.json endpoint returns
correct information including plan mode configuration.
"""

import httpx
import pytest


class TestAgentCard:
    """Tests for the agent card endpoint."""

    @pytest.mark.asyncio
    async def test_agent_card_endpoint_exists(
        self,
        plan_mode_server: tuple,
        http_client: httpx.AsyncClient,
    ):
        """Test that the agent card endpoint returns 200."""
        server, base_url = plan_mode_server

        response = await http_client.get(f"{base_url}/.well-known/agent.json")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")

    @pytest.mark.asyncio
    async def test_agent_card_has_required_fields(
        self,
        plan_mode_server: tuple,
        http_client: httpx.AsyncClient,
    ):
        """Test that agent card contains required A2A fields."""
        server, base_url = plan_mode_server

        response = await http_client.get(f"{base_url}/.well-known/agent.json")
        card = response.json()

        # Required A2A fields
        assert "name" in card
        assert "description" in card
        assert "version" in card
        assert "url" in card
        assert "capabilities" in card

    @pytest.mark.asyncio
    async def test_agent_card_includes_plan_mode_config(
        self,
        plan_mode_server: tuple,
        http_client: httpx.AsyncClient,
    ):
        """Test that agent card includes plan mode configuration."""
        server, base_url = plan_mode_server

        response = await http_client.get(f"{base_url}/.well-known/agent.json")
        card = response.json()

        # Plan mode should be included
        assert "planMode" in card
        plan_mode = card["planMode"]

        assert plan_mode["supported"] is True
        assert "phases" in plan_mode
        assert isinstance(plan_mode["phases"], list)

        # Verify configured phases
        expected_phases = ["clarification", "discovery", "selection", "preview"]
        assert plan_mode["phases"] == expected_phases

    @pytest.mark.asyncio
    async def test_agent_card_streaming_capability(
        self,
        plan_mode_server: tuple,
        http_client: httpx.AsyncClient,
    ):
        """Test that agent card advertises streaming capability."""
        server, base_url = plan_mode_server

        response = await http_client.get(f"{base_url}/.well-known/agent.json")
        card = response.json()

        capabilities = card["capabilities"]
        assert "streaming" in capabilities
        assert capabilities["streaming"] is True


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_endpoint_returns_ok(
        self,
        plan_mode_server: tuple,
        http_client: httpx.AsyncClient,
    ):
        """Test that health endpoint returns healthy status."""
        server, base_url = plan_mode_server

        response = await http_client.get(f"{base_url}/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "agent_id" in data
        assert data["agent_id"] == "e2e-test-agent"
