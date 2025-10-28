"""Tests for the secrets management module."""

import pytest
from unittest.mock import Mock, patch

from pixell.core.secrets import (
    SecretsClient,
    SecretsError,
    SecretNotFoundError,
)
from pixell.core.deployment import AuthenticationError


class TestSecretsClient:
    """Test the SecretsClient class."""

    def test_init_valid_environment(self):
        """Test initialization with valid environment."""
        client = SecretsClient(environment="local")
        assert client.environment == "local"
        assert client.base_url == "http://localhost:4000"

        client = SecretsClient(environment="prod")
        assert client.environment == "prod"
        assert client.base_url == "https://cloud.pixell.global"

    def test_init_invalid_environment(self):
        """Test initialization with invalid environment."""
        with pytest.raises(ValueError, match="Invalid environment"):
            SecretsClient(environment="invalid")

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        client = SecretsClient(environment="prod", api_key="test-key")
        assert client.api_key == "test-key"
        assert client.session.headers["Authorization"] == "Bearer test-key"

    @patch("pixell.core.secrets.requests.Session.get")
    def test_list_secrets_success(self, mock_get):
        """Test listing secrets successfully."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "secrets": {
                "OPENAI_API_KEY": "sk-xxx",
                "DATABASE_URL": "postgresql://...",
                "DEBUG": "false",
            }
        }
        mock_get.return_value = mock_response

        client = SecretsClient(environment="prod", api_key="test-key")
        result = client.list_secrets("app-123")

        assert len(result) == 3
        assert result["OPENAI_API_KEY"] == "sk-xxx"
        assert result["DATABASE_URL"] == "postgresql://..."
        assert result["DEBUG"] == "false"

        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "api/agent-apps/app-123/secrets" in call_args[0][0]

    @patch("pixell.core.secrets.requests.Session.get")
    def test_list_secrets_empty(self, mock_get):
        """Test listing secrets when none exist."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"secrets": {}}
        mock_get.return_value = mock_response

        client = SecretsClient(environment="prod", api_key="test-key")
        result = client.list_secrets("app-123")

        assert len(result) == 0
        assert result == {}

    @patch("pixell.core.secrets.requests.Session.get")
    def test_list_secrets_authentication_error(self, mock_get):
        """Test listing secrets with authentication error."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        client = SecretsClient(environment="prod", api_key="invalid-key")

        with pytest.raises(AuthenticationError, match="Invalid or missing API key"):
            client.list_secrets("app-123")

    @patch("pixell.core.secrets.requests.Session.get")
    def test_list_secrets_not_found(self, mock_get):
        """Test listing secrets for non-existent app."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        client = SecretsClient(environment="prod", api_key="test-key")

        with pytest.raises(SecretNotFoundError, match="Agent app not found"):
            client.list_secrets("invalid-app")

    @patch("pixell.core.secrets.requests.Session.get")
    def test_get_secret_success(self, mock_get):
        """Test getting a single secret successfully."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "secrets": {
                "OPENAI_API_KEY": "sk-xxx",
                "DEBUG": "false",
            }
        }
        mock_get.return_value = mock_response

        client = SecretsClient(environment="prod", api_key="test-key")
        result = client.get_secret("app-123", "OPENAI_API_KEY")

        assert result == "sk-xxx"

    @patch("pixell.core.secrets.requests.Session.get")
    def test_get_secret_not_found(self, mock_get):
        """Test getting a non-existent secret."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "secrets": {
                "DEBUG": "false",
            }
        }
        mock_get.return_value = mock_response

        client = SecretsClient(environment="prod", api_key="test-key")

        with pytest.raises(SecretNotFoundError, match="Secret not found: OPENAI_API_KEY"):
            client.get_secret("app-123", "OPENAI_API_KEY")

    @patch("pixell.core.secrets.requests.Session.post")
    def test_set_secrets_success(self, mock_post):
        """Test setting secrets successfully."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "message": "Secrets saved successfully",
            "secretCount": 2,
        }
        mock_post.return_value = mock_response

        client = SecretsClient(environment="prod", api_key="test-key")
        secrets = {"OPENAI_API_KEY": "sk-new", "DEBUG": "true"}
        result = client.set_secrets("app-123", secrets)

        assert result["success"] is True
        assert result["secretCount"] == 2

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "api/agent-apps/app-123/secrets" in call_args[0][0]
        assert call_args[1]["json"]["secrets"] == secrets

    @patch("pixell.core.secrets.requests.Session.post")
    def test_set_secrets_invalid_value_type(self, mock_post):
        """Test setting secrets with non-string value."""
        client = SecretsClient(environment="prod", api_key="test-key")
        secrets = {"OPENAI_API_KEY": "sk-new", "DEBUG": True}  # Boolean instead of string

        with pytest.raises(SecretsError, match="must be a string"):
            client.set_secrets("app-123", secrets)

        # Should not make API call
        mock_post.assert_not_called()

    @patch("pixell.core.secrets.requests.Session.post")
    def test_set_secrets_authentication_error(self, mock_post):
        """Test setting secrets with authentication error."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response

        client = SecretsClient(environment="prod", api_key="invalid-key")

        with pytest.raises(AuthenticationError):
            client.set_secrets("app-123", {"KEY": "value"})

    @patch("pixell.core.secrets.requests.Session.post")
    def test_set_secrets_not_found(self, mock_post):
        """Test setting secrets for non-existent app."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_post.return_value = mock_response

        client = SecretsClient(environment="prod", api_key="test-key")

        with pytest.raises(SecretNotFoundError):
            client.set_secrets("invalid-app", {"KEY": "value"})

    @patch("pixell.core.secrets.requests.Session.put")
    def test_update_secret_success(self, mock_put):
        """Test updating a single secret successfully."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "message": "Secret updated successfully",
            "key": "OPENAI_API_KEY",
        }
        mock_put.return_value = mock_response

        client = SecretsClient(environment="prod", api_key="test-key")
        result = client.update_secret("app-123", "OPENAI_API_KEY", "sk-updated")

        assert result["success"] is True
        assert result["key"] == "OPENAI_API_KEY"

        mock_put.assert_called_once()
        call_args = mock_put.call_args
        assert "api/agent-apps/app-123/secrets/OPENAI_API_KEY" in call_args[0][0]
        assert call_args[1]["json"]["value"] == "sk-updated"

    @patch("pixell.core.secrets.requests.Session.put")
    def test_update_secret_invalid_value_type(self, mock_put):
        """Test updating secret with non-string value."""
        client = SecretsClient(environment="prod", api_key="test-key")

        with pytest.raises(SecretsError, match="must be a string"):
            client.update_secret("app-123", "DEBUG", 123)  # type: ignore

        mock_put.assert_not_called()

    @patch("pixell.core.secrets.requests.Session.put")
    def test_update_secret_authentication_error(self, mock_put):
        """Test updating secret with authentication error."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_put.return_value = mock_response

        client = SecretsClient(environment="prod", api_key="invalid-key")

        with pytest.raises(AuthenticationError):
            client.update_secret("app-123", "KEY", "value")

    @patch("pixell.core.secrets.requests.Session.delete")
    def test_delete_secret_success(self, mock_delete):
        """Test deleting a secret successfully."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "message": "Secret deleted successfully",
            "key": "DEBUG",
        }
        mock_delete.return_value = mock_response

        client = SecretsClient(environment="prod", api_key="test-key")
        result = client.delete_secret("app-123", "DEBUG")

        assert result["success"] is True
        assert result["key"] == "DEBUG"

        mock_delete.assert_called_once()
        call_args = mock_delete.call_args
        assert "api/agent-apps/app-123/secrets/DEBUG" in call_args[0][0]

    @patch("pixell.core.secrets.requests.Session.delete")
    def test_delete_secret_not_found(self, mock_delete):
        """Test deleting a non-existent secret."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_delete.return_value = mock_response

        client = SecretsClient(environment="prod", api_key="test-key")

        with pytest.raises(SecretNotFoundError):
            client.delete_secret("app-123", "NONEXISTENT")

    @patch("pixell.core.secrets.requests.Session.delete")
    def test_delete_secret_authentication_error(self, mock_delete):
        """Test deleting secret with authentication error."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_delete.return_value = mock_response

        client = SecretsClient(environment="prod", api_key="invalid-key")

        with pytest.raises(AuthenticationError):
            client.delete_secret("app-123", "KEY")

    @patch("pixell.core.secrets.requests.Session.delete")
    def test_delete_all_secrets_success(self, mock_delete):
        """Test deleting all secrets successfully."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "message": "Secrets deleted successfully",
        }
        mock_delete.return_value = mock_response

        client = SecretsClient(environment="prod", api_key="test-key")
        result = client.delete_all_secrets("app-123")

        assert result["success"] is True

        mock_delete.assert_called_once()
        call_args = mock_delete.call_args
        assert "api/agent-apps/app-123/secrets" in call_args[0][0]

    @patch("pixell.core.secrets.requests.Session.delete")
    def test_delete_all_secrets_not_found(self, mock_delete):
        """Test deleting all secrets for non-existent app."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_delete.return_value = mock_response

        client = SecretsClient(environment="prod", api_key="test-key")

        with pytest.raises(SecretNotFoundError):
            client.delete_all_secrets("invalid-app")

    @patch("pixell.core.secrets.requests.Session.delete")
    def test_delete_all_secrets_authentication_error(self, mock_delete):
        """Test deleting all secrets with authentication error."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_delete.return_value = mock_response

        client = SecretsClient(environment="prod", api_key="invalid-key")

        with pytest.raises(AuthenticationError):
            client.delete_all_secrets("app-123")
