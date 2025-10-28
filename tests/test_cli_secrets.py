"""Tests for the pixell secrets CLI commands."""

import pytest
import tempfile
import json
from unittest.mock import Mock, patch
from click.testing import CliRunner
from pathlib import Path

from pixell.cli.main import cli
from pixell.core.secrets import SecretNotFoundError
from pixell.core.deployment import AuthenticationError


@pytest.fixture
def runner():
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_secrets_client():
    """Create a mock SecretsClient."""
    with patch("pixell.core.secrets.SecretsClient") as mock:
        yield mock


class TestSecretsListCommand:
    """Test pixell secrets list command."""

    @patch("pixell.core.secrets.SecretsClient")
    @patch("pixell.core.deployment.get_app_id")
    @patch("pixell.core.deployment.get_api_key")
    def test_list_success_table_format(self, mock_get_api_key, mock_get_app_id, mock_client, runner):
        """Test listing secrets in table format."""
        mock_get_app_id.return_value = "app-123"
        mock_get_api_key.return_value = "test-key"

        mock_instance = Mock()
        mock_instance.list_secrets.return_value = {
            "OPENAI_API_KEY": "sk-xxx",
            "DEBUG": "false",
        }
        mock_client.return_value = mock_instance

        result = runner.invoke(cli, ["secrets", "list"])

        assert result.exit_code == 0
        assert "OPENAI_API_KEY" in result.output
        assert "DEBUG" in result.output
        assert "sk-***" in result.output
        assert "Total: 2 secret(s)" in result.output

    @patch("pixell.core.secrets.SecretsClient")
    @patch("pixell.core.deployment.get_app_id")
    @patch("pixell.core.deployment.get_api_key")
    def test_list_success_json_format(self, mock_get_api_key, mock_get_app_id, mock_client, runner):
        """Test listing secrets in JSON format."""
        mock_get_app_id.return_value = "app-123"
        mock_get_api_key.return_value = "test-key"

        mock_instance = Mock()
        mock_instance.list_secrets.return_value = {
            "OPENAI_API_KEY": "sk-xxx",
            "DEBUG": "false",
        }
        mock_client.return_value = mock_instance

        result = runner.invoke(cli, ["secrets", "list", "--format", "json"])

        assert result.exit_code == 0
        output_data = json.loads(result.output)
        assert output_data["secrets"]["OPENAI_API_KEY"] == "sk-xxx"
        assert output_data["secrets"]["DEBUG"] == "false"

    @patch("pixell.core.secrets.SecretsClient")
    @patch("pixell.core.deployment.get_app_id")
    @patch("pixell.core.deployment.get_api_key")
    def test_list_empty(self, mock_get_api_key, mock_get_app_id, mock_client, runner):
        """Test listing secrets when none exist."""
        mock_get_app_id.return_value = "app-123"
        mock_get_api_key.return_value = "test-key"

        mock_instance = Mock()
        mock_instance.list_secrets.return_value = {}
        mock_client.return_value = mock_instance

        result = runner.invoke(cli, ["secrets", "list"])

        assert result.exit_code == 0
        assert "No secrets found" in result.output

    @patch("pixell.core.deployment.get_app_id")
    @patch("pixell.core.deployment.get_api_key")
    def test_list_no_app_id(self, mock_get_api_key, mock_get_app_id, runner):
        """Test listing without app ID."""
        mock_get_app_id.return_value = None
        mock_get_api_key.return_value = "test-key"

        result = runner.invoke(cli, ["secrets", "list"])

        assert result.exit_code == 1
        assert "ERROR: No app ID provided" in result.output

    @patch("pixell.core.deployment.get_app_id")
    @patch("pixell.core.deployment.get_api_key")
    def test_list_no_api_key(self, mock_get_api_key, mock_get_app_id, runner):
        """Test listing without API key."""
        mock_get_app_id.return_value = "app-123"
        mock_get_api_key.return_value = None

        result = runner.invoke(cli, ["secrets", "list"])

        assert result.exit_code == 1
        assert "ERROR: No API key provided" in result.output

    @patch("pixell.core.secrets.SecretsClient")
    @patch("pixell.core.deployment.get_app_id")
    @patch("pixell.core.deployment.get_api_key")
    def test_list_authentication_error(self, mock_get_api_key, mock_get_app_id, mock_client, runner):
        """Test listing with authentication error."""
        mock_get_app_id.return_value = "app-123"
        mock_get_api_key.return_value = "invalid-key"

        mock_instance = Mock()
        mock_instance.list_secrets.side_effect = AuthenticationError("Invalid API key")
        mock_client.return_value = mock_instance

        result = runner.invoke(cli, ["secrets", "list"])

        assert result.exit_code == 2
        assert "AUTHENTICATION ERROR" in result.output

    @patch("pixell.core.secrets.SecretsClient")
    @patch("pixell.core.deployment.get_app_id")
    @patch("pixell.core.deployment.get_api_key")
    def test_list_not_found(self, mock_get_api_key, mock_get_app_id, mock_client, runner):
        """Test listing for non-existent app."""
        mock_get_app_id.return_value = "app-123"
        mock_get_api_key.return_value = "test-key"

        mock_instance = Mock()
        mock_instance.list_secrets.side_effect = SecretNotFoundError("Agent app not found")
        mock_client.return_value = mock_instance

        result = runner.invoke(cli, ["secrets", "list"])

        assert result.exit_code == 3
        assert "NOT FOUND" in result.output


class TestSecretsGetCommand:
    """Test pixell secrets get command."""

    @patch("pixell.core.secrets.SecretsClient")
    @patch("pixell.core.deployment.get_app_id")
    @patch("pixell.core.deployment.get_api_key")
    def test_get_success(self, mock_get_api_key, mock_get_app_id, mock_client, runner):
        """Test getting a single secret."""
        mock_get_app_id.return_value = "app-123"
        mock_get_api_key.return_value = "test-key"

        mock_instance = Mock()
        mock_instance.get_secret.return_value = "sk-1234567890"
        mock_client.return_value = mock_instance

        result = runner.invoke(cli, ["secrets", "get", "OPENAI_API_KEY"])

        assert result.exit_code == 0
        assert result.output.strip() == "sk-1234567890"

    @patch("pixell.core.secrets.SecretsClient")
    @patch("pixell.core.deployment.get_app_id")
    @patch("pixell.core.deployment.get_api_key")
    def test_get_not_found(self, mock_get_api_key, mock_get_app_id, mock_client, runner):
        """Test getting non-existent secret."""
        mock_get_app_id.return_value = "app-123"
        mock_get_api_key.return_value = "test-key"

        mock_instance = Mock()
        mock_instance.get_secret.side_effect = SecretNotFoundError("Secret not found")
        mock_client.return_value = mock_instance

        result = runner.invoke(cli, ["secrets", "get", "NONEXISTENT"])

        assert result.exit_code == 3
        assert "NOT FOUND" in result.output


class TestSecretsSetCommand:
    """Test pixell secrets set command."""

    @patch("pixell.core.secrets.SecretsClient")
    @patch("pixell.core.deployment.get_app_id")
    @patch("pixell.core.deployment.get_api_key")
    def test_set_from_cli_args(self, mock_get_api_key, mock_get_app_id, mock_client, runner):
        """Test setting secrets from CLI arguments."""
        mock_get_app_id.return_value = "app-123"
        mock_get_api_key.return_value = "test-key"

        mock_instance = Mock()
        mock_instance.set_secrets.return_value = {"success": True, "secretCount": 2}
        mock_client.return_value = mock_instance

        result = runner.invoke(
            cli,
            ["secrets", "set", "-s", "OPENAI_API_KEY=sk-xxx", "-s", "DEBUG=false"],
            input="y\n",
        )

        assert result.exit_code == 0
        assert "Secrets saved successfully" in result.output
        mock_instance.set_secrets.assert_called_once()
        call_args = mock_instance.set_secrets.call_args
        assert call_args[0][1] == {"OPENAI_API_KEY": "sk-xxx", "DEBUG": "false"}

    @patch("pixell.core.secrets.SecretsClient")
    @patch("pixell.core.deployment.get_app_id")
    @patch("pixell.core.deployment.get_api_key")
    def test_set_from_json_file(self, mock_get_api_key, mock_get_app_id, mock_client, runner):
        """Test setting secrets from JSON file."""
        mock_get_app_id.return_value = "app-123"
        mock_get_api_key.return_value = "test-key"

        mock_instance = Mock()
        mock_instance.set_secrets.return_value = {"success": True, "secretCount": 2}
        mock_client.return_value = mock_instance

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"OPENAI_API_KEY": "sk-xxx", "DEBUG": "false"}, f)
            f.flush()
            file_path = Path(f.name)

        try:
            result = runner.invoke(
                cli,
                ["secrets", "set", "--file", str(file_path)],
                input="y\n",
            )

            assert result.exit_code == 0
            assert "Secrets saved successfully" in result.output
        finally:
            file_path.unlink()

    @patch("pixell.core.secrets.SecretsClient")
    @patch("pixell.core.deployment.get_app_id")
    @patch("pixell.core.deployment.get_api_key")
    def test_set_from_env_file(self, mock_get_api_key, mock_get_app_id, mock_client, runner):
        """Test setting secrets from .env file."""
        mock_get_app_id.return_value = "app-123"
        mock_get_api_key.return_value = "test-key"

        mock_instance = Mock()
        mock_instance.set_secrets.return_value = {"success": True, "secretCount": 2}
        mock_client.return_value = mock_instance

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("OPENAI_API_KEY=sk-xxx\n")
            f.write("DEBUG=false\n")
            f.flush()
            file_path = Path(f.name)

        try:
            result = runner.invoke(
                cli,
                ["secrets", "set", "--file", str(file_path)],
                input="y\n",
            )

            assert result.exit_code == 0
            assert "Secrets saved successfully" in result.output
        finally:
            file_path.unlink()

    @patch("pixell.core.deployment.get_app_id")
    @patch("pixell.core.deployment.get_api_key")
    def test_set_no_secrets_provided(self, mock_get_api_key, mock_get_app_id, runner):
        """Test setting without providing any secrets."""
        mock_get_app_id.return_value = "app-123"
        mock_get_api_key.return_value = "test-key"

        result = runner.invoke(cli, ["secrets", "set"])

        assert result.exit_code == 1
        assert "No secrets provided" in result.output

    @patch("pixell.core.deployment.get_app_id")
    @patch("pixell.core.deployment.get_api_key")
    def test_set_invalid_key_format(self, mock_get_api_key, mock_get_app_id, runner):
        """Test setting with invalid key format."""
        mock_get_app_id.return_value = "app-123"
        mock_get_api_key.return_value = "test-key"

        result = runner.invoke(
            cli,
            ["secrets", "set", "-s", "invalid-key=value"],
        )

        assert result.exit_code == 1
        assert "Invalid secret key" in result.output

    @patch("pixell.core.deployment.get_app_id")
    @patch("pixell.core.deployment.get_api_key")
    def test_set_cancelled(self, mock_get_api_key, mock_get_app_id, runner):
        """Test cancelling set operation."""
        mock_get_app_id.return_value = "app-123"
        mock_get_api_key.return_value = "test-key"

        result = runner.invoke(
            cli,
            ["secrets", "set", "-s", "KEY=value"],
            input="n\n",
        )

        assert result.exit_code == 0
        assert "Cancelled" in result.output


class TestSecretsUpdateCommand:
    """Test pixell secrets update command."""

    @patch("pixell.core.secrets.SecretsClient")
    @patch("pixell.core.deployment.get_app_id")
    @patch("pixell.core.deployment.get_api_key")
    def test_update_success(self, mock_get_api_key, mock_get_app_id, mock_client, runner):
        """Test updating a secret."""
        mock_get_app_id.return_value = "app-123"
        mock_get_api_key.return_value = "test-key"

        mock_instance = Mock()
        mock_instance.update_secret.return_value = {"success": True, "key": "OPENAI_API_KEY"}
        mock_client.return_value = mock_instance

        result = runner.invoke(cli, ["secrets", "update", "OPENAI_API_KEY", "sk-new"])

        assert result.exit_code == 0
        assert "updated successfully" in result.output

    @patch("pixell.core.deployment.get_app_id")
    @patch("pixell.core.deployment.get_api_key")
    def test_update_invalid_key(self, mock_get_api_key, mock_get_app_id, runner):
        """Test updating with invalid key format."""
        mock_get_app_id.return_value = "app-123"
        mock_get_api_key.return_value = "test-key"

        result = runner.invoke(cli, ["secrets", "update", "invalid-key", "value"])

        assert result.exit_code == 1
        assert "Invalid secret key" in result.output


class TestSecretsDeleteCommand:
    """Test pixell secrets delete command."""

    @patch("pixell.core.secrets.SecretsClient")
    @patch("pixell.core.deployment.get_app_id")
    @patch("pixell.core.deployment.get_api_key")
    def test_delete_with_confirmation(self, mock_get_api_key, mock_get_app_id, mock_client, runner):
        """Test deleting a secret with confirmation."""
        mock_get_app_id.return_value = "app-123"
        mock_get_api_key.return_value = "test-key"

        mock_instance = Mock()
        mock_instance.delete_secret.return_value = {"success": True, "key": "DEBUG"}
        mock_client.return_value = mock_instance

        result = runner.invoke(cli, ["secrets", "delete", "DEBUG"], input="y\n")

        assert result.exit_code == 0
        assert "deleted successfully" in result.output

    @patch("pixell.core.secrets.SecretsClient")
    @patch("pixell.core.deployment.get_app_id")
    @patch("pixell.core.deployment.get_api_key")
    def test_delete_with_force(self, mock_get_api_key, mock_get_app_id, mock_client, runner):
        """Test deleting a secret with --force flag."""
        mock_get_app_id.return_value = "app-123"
        mock_get_api_key.return_value = "test-key"

        mock_instance = Mock()
        mock_instance.delete_secret.return_value = {"success": True, "key": "DEBUG"}
        mock_client.return_value = mock_instance

        result = runner.invoke(cli, ["secrets", "delete", "DEBUG", "--force"])

        assert result.exit_code == 0
        assert "deleted successfully" in result.output

    @patch("pixell.core.deployment.get_app_id")
    @patch("pixell.core.deployment.get_api_key")
    def test_delete_cancelled(self, mock_get_api_key, mock_get_app_id, runner):
        """Test cancelling delete operation."""
        mock_get_app_id.return_value = "app-123"
        mock_get_api_key.return_value = "test-key"

        result = runner.invoke(cli, ["secrets", "delete", "DEBUG"], input="n\n")

        assert result.exit_code == 0
        assert "Cancelled" in result.output


class TestSecretsDeleteAllCommand:
    """Test pixell secrets delete-all command."""

    @patch("pixell.core.secrets.SecretsClient")
    @patch("pixell.core.deployment.get_app_id")
    @patch("pixell.core.deployment.get_api_key")
    def test_delete_all_with_confirm(self, mock_get_api_key, mock_get_app_id, mock_client, runner):
        """Test deleting all secrets with --confirm flag."""
        mock_get_app_id.return_value = "app-123"
        mock_get_api_key.return_value = "test-key"

        mock_instance = Mock()
        mock_instance.delete_all_secrets.return_value = {"success": True}
        mock_client.return_value = mock_instance

        result = runner.invoke(cli, ["secrets", "delete-all", "--confirm"], input="y\n")

        assert result.exit_code == 0
        assert "All secrets deleted successfully" in result.output

    @patch("pixell.core.deployment.get_app_id")
    @patch("pixell.core.deployment.get_api_key")
    def test_delete_all_without_confirm_flag(self, mock_get_api_key, mock_get_app_id, runner):
        """Test deleting all without --confirm flag."""
        mock_get_app_id.return_value = "app-123"
        mock_get_api_key.return_value = "test-key"

        result = runner.invoke(cli, ["secrets", "delete-all"])

        assert result.exit_code == 1
        assert "requires --confirm flag" in result.output

    @patch("pixell.core.deployment.get_app_id")
    @patch("pixell.core.deployment.get_api_key")
    def test_delete_all_cancelled(self, mock_get_api_key, mock_get_app_id, runner):
        """Test cancelling delete-all operation."""
        mock_get_app_id.return_value = "app-123"
        mock_get_api_key.return_value = "test-key"

        result = runner.invoke(cli, ["secrets", "delete-all", "--confirm"], input="n\n")

        assert result.exit_code == 0
        assert "Cancelled" in result.output


class TestEnvironmentVariableFallback:
    """Test PIXELL_APP_ID environment variable fallback."""

    @patch("pixell.core.secrets.SecretsClient")
    @patch("pixell.core.deployment.get_app_id")
    @patch("pixell.core.deployment.get_api_key")
    def test_app_id_from_env_var(self, mock_get_api_key, mock_get_app_id, mock_client, runner):
        """Test using PIXELL_APP_ID from environment."""
        mock_get_app_id.return_value = "app-from-env"
        mock_get_api_key.return_value = "test-key"

        mock_instance = Mock()
        mock_instance.list_secrets.return_value = {}
        mock_client.return_value = mock_instance

        result = runner.invoke(cli, ["secrets", "list"])

        assert result.exit_code == 0
        # Verify client was created with correct app_id
        mock_instance.list_secrets.assert_called_once_with("app-from-env")


class TestExitCodes:
    """Test exit codes for all scenarios."""

    @patch("pixell.core.secrets.SecretsClient")
    @patch("pixell.core.deployment.get_app_id")
    @patch("pixell.core.deployment.get_api_key")
    def test_exit_code_success(self, mock_get_api_key, mock_get_app_id, mock_client, runner):
        """Test exit code 0 for success."""
        mock_get_app_id.return_value = "app-123"
        mock_get_api_key.return_value = "test-key"

        mock_instance = Mock()
        mock_instance.list_secrets.return_value = {}
        mock_client.return_value = mock_instance

        result = runner.invoke(cli, ["secrets", "list"])
        assert result.exit_code == 0

    @patch("pixell.core.deployment.get_app_id")
    @patch("pixell.core.deployment.get_api_key")
    def test_exit_code_general_error(self, mock_get_api_key, mock_get_app_id, runner):
        """Test exit code 1 for general errors."""
        mock_get_app_id.return_value = None
        mock_get_api_key.return_value = "test-key"

        result = runner.invoke(cli, ["secrets", "list"])
        assert result.exit_code == 1

    @patch("pixell.core.secrets.SecretsClient")
    @patch("pixell.core.deployment.get_app_id")
    @patch("pixell.core.deployment.get_api_key")
    def test_exit_code_auth_error(self, mock_get_api_key, mock_get_app_id, mock_client, runner):
        """Test exit code 2 for authentication errors."""
        mock_get_app_id.return_value = "app-123"
        mock_get_api_key.return_value = "test-key"

        mock_instance = Mock()
        mock_instance.list_secrets.side_effect = AuthenticationError("Invalid API key")
        mock_client.return_value = mock_instance

        result = runner.invoke(cli, ["secrets", "list"])
        assert result.exit_code == 2

    @patch("pixell.core.secrets.SecretsClient")
    @patch("pixell.core.deployment.get_app_id")
    @patch("pixell.core.deployment.get_api_key")
    def test_exit_code_not_found(self, mock_get_api_key, mock_get_app_id, mock_client, runner):
        """Test exit code 3 for not found errors."""
        mock_get_app_id.return_value = "app-123"
        mock_get_api_key.return_value = "test-key"

        mock_instance = Mock()
        mock_instance.list_secrets.side_effect = SecretNotFoundError("Not found")
        mock_client.return_value = mock_instance

        result = runner.invoke(cli, ["secrets", "list"])
        assert result.exit_code == 3
