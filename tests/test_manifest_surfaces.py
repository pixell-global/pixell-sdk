"""Tests for A2A/REST/UI surface support in agent manifests."""

import pytest

from pixell.models.agent_manifest import AgentManifest


class TestAgentManifestSurfaces:
    """Test A2A/REST/UI surface configuration in agent manifests."""

    def test_manifest_with_all_surfaces(self):
        """Test manifest with A2A, REST, and UI surfaces configured."""
        manifest_data = {
            "version": "1.0",
            "name": "test-agent",
            "display_name": "Test Agent",
            "description": "A test agent",
            "author": "Test Author",
            "license": "MIT",
            "runtime": "python3.11",
            "metadata": {"version": "1.0.0"},
            "a2a": {"service": "src.a2a.server:serve"},
            "rest": {"entry": "src.rest.index:mount"},
            "ui": {"path": "ui"},
        }

        manifest = AgentManifest(**manifest_data)

        assert manifest.a2a is not None
        assert manifest.a2a.service == "src.a2a.server:serve"
        assert manifest.rest is not None
        assert manifest.rest.entry == "src.rest.index:mount"
        assert manifest.ui is not None
        assert manifest.ui.path == "ui"

    def test_manifest_with_optional_entrypoint(self):
        """Test that entrypoint is optional when surfaces are configured."""
        manifest_data = {
            "version": "1.0",
            "name": "test-agent",
            "display_name": "Test Agent",
            "description": "A test agent",
            "author": "Test Author",
            "license": "MIT",
            "runtime": "python3.11",
            "metadata": {"version": "1.0.0"},
            "rest": {"entry": "src.rest.index:mount"},
        }

        manifest = AgentManifest(**manifest_data)
        assert manifest.entrypoint is None
        assert manifest.rest is not None

    def test_manifest_with_entrypoint_and_surfaces(self):
        """Test manifest with both entrypoint and surfaces."""
        manifest_data = {
            "version": "1.0",
            "name": "test-agent",
            "display_name": "Test Agent",
            "description": "A test agent",
            "author": "Test Author",
            "license": "MIT",
            "entrypoint": "src.main:handler",
            "runtime": "python3.11",
            "metadata": {"version": "1.0.0"},
            "rest": {"entry": "src.rest.index:mount"},
        }

        manifest = AgentManifest(**manifest_data)
        assert manifest.entrypoint == "src.main:handler"
        assert manifest.rest is not None

    def test_a2a_service_validation(self):
        """Test A2A service field validation."""
        # Valid format
        manifest_data = {
            "version": "1.0",
            "name": "test-agent",
            "display_name": "Test Agent",
            "description": "A test agent",
            "author": "Test Author",
            "license": "MIT",
            "runtime": "python3.11",
            "metadata": {"version": "1.0.0"},
            "a2a": {"service": "src.a2a.server:serve"},
        }

        manifest = AgentManifest(**manifest_data)
        assert manifest.a2a.service == "src.a2a.server:serve"

        # Invalid format - missing colon
        with pytest.raises(ValueError, match="A2A service must be in format 'module:function'"):
            AgentManifest(**{**manifest_data, "a2a": {"service": "src.a2a.server.serve"}})

    def test_rest_entry_validation(self):
        """Test REST entry field validation."""
        # Valid format
        manifest_data = {
            "version": "1.0",
            "name": "test-agent",
            "display_name": "Test Agent",
            "description": "A test agent",
            "author": "Test Author",
            "license": "MIT",
            "runtime": "python3.11",
            "metadata": {"version": "1.0.0"},
            "rest": {"entry": "src.rest.index:mount"},
        }

        manifest = AgentManifest(**manifest_data)
        assert manifest.rest.entry == "src.rest.index:mount"

        # Invalid format - missing colon
        with pytest.raises(ValueError, match="REST entry must be in format 'module:function'"):
            AgentManifest(**{**manifest_data, "rest": {"entry": "src.rest.index.mount"}})

    def test_ui_path_validation(self):
        """Test UI path field."""
        manifest_data = {
            "version": "1.0",
            "name": "test-agent",
            "display_name": "Test Agent",
            "description": "A test agent",
            "author": "Test Author",
            "license": "MIT",
            "runtime": "python3.11",
            "metadata": {"version": "1.0.0"},
            "ui": {"path": "ui"},
        }

        manifest = AgentManifest(**manifest_data)
        assert manifest.ui.path == "ui"

    def test_manifest_without_surfaces(self):
        """Test manifest without any surfaces (traditional agent)."""
        manifest_data = {
            "version": "1.0",
            "name": "test-agent",
            "display_name": "Test Agent",
            "description": "A test agent",
            "author": "Test Author",
            "license": "MIT",
            "entrypoint": "src.main:handler",
            "runtime": "python3.11",
            "metadata": {"version": "1.0.0"},
        }

        manifest = AgentManifest(**manifest_data)
        assert manifest.entrypoint == "src.main:handler"
        assert manifest.a2a is None
        assert manifest.rest is None
        assert manifest.ui is None
