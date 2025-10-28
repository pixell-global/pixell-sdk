"""Tests for secrets utilities module."""

import pytest
import tempfile
from pathlib import Path

from pixell.core.secrets_utils import (
    validate_secret_key,
    mask_secret_value,
    parse_json_file,
    parse_env_file,
    format_secrets_table,
)
from pixell.core.secrets import SecretsError


class TestValidateSecretKey:
    """Test secret key validation."""

    def test_valid_keys(self):
        """Test valid secret keys."""
        assert validate_secret_key("OPENAI_API_KEY") is True
        assert validate_secret_key("DEBUG") is True
        assert validate_secret_key("DATABASE_URL") is True
        assert validate_secret_key("API_KEY_123") is True
        assert validate_secret_key("MY_SECRET") is True
        assert validate_secret_key("_PRIVATE") is True
        assert validate_secret_key("ABC123") is True

    def test_invalid_keys(self):
        """Test invalid secret keys."""
        assert validate_secret_key("lowercase") is False
        assert validate_secret_key("Mixed_Case") is False
        assert validate_secret_key("api-key") is False
        assert validate_secret_key("api.key") is False
        assert validate_secret_key("api key") is False
        assert validate_secret_key("api@key") is False
        assert validate_secret_key("") is False


class TestMaskSecretValue:
    """Test secret value masking."""

    def test_mask_default(self):
        """Test masking with default show_chars."""
        assert mask_secret_value("sk-1234567890") == "sk-***"
        assert mask_secret_value("postgresql://user:pass@host") == "pos***"
        assert mask_secret_value("secret") == "sec***"

    def test_mask_custom_chars(self):
        """Test masking with custom show_chars."""
        assert mask_secret_value("sk-1234567890", show_chars=5) == "sk-12***"
        assert mask_secret_value("secret", show_chars=0) == "***"
        assert mask_secret_value("secret", show_chars=10) == "***"

    def test_mask_short_values(self):
        """Test masking short values."""
        assert mask_secret_value("ab") == "***"
        assert mask_secret_value("a") == "***"
        assert mask_secret_value("abc") == "***"

    def test_mask_empty_value(self):
        """Test masking empty value."""
        assert mask_secret_value("") == "***"


class TestParseJsonFile:
    """Test JSON file parsing."""

    def test_parse_valid_json(self):
        """Test parsing valid JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"OPENAI_API_KEY": "sk-xxx", "DEBUG": "false"}')
            f.flush()
            file_path = Path(f.name)

        try:
            result = parse_json_file(file_path)
            assert result == {"OPENAI_API_KEY": "sk-xxx", "DEBUG": "false"}
        finally:
            file_path.unlink()

    def test_parse_empty_json(self):
        """Test parsing empty JSON object."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{}')
            f.flush()
            file_path = Path(f.name)

        try:
            result = parse_json_file(file_path)
            assert result == {}
        finally:
            file_path.unlink()

    def test_parse_json_non_dict(self):
        """Test parsing JSON that is not a dictionary."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('["key", "value"]')
            f.flush()
            file_path = Path(f.name)

        try:
            with pytest.raises(SecretsError, match="must contain an object/dictionary"):
                parse_json_file(file_path)
        finally:
            file_path.unlink()

    def test_parse_json_non_string_value(self):
        """Test parsing JSON with non-string values."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"DEBUG": true, "PORT": 8080}')
            f.flush()
            file_path = Path(f.name)

        try:
            with pytest.raises(SecretsError, match="must be a string"):
                parse_json_file(file_path)
        finally:
            file_path.unlink()

    def test_parse_json_invalid_format(self):
        """Test parsing invalid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"key": invalid}')
            f.flush()
            file_path = Path(f.name)

        try:
            with pytest.raises(SecretsError, match="Invalid JSON format"):
                parse_json_file(file_path)
        finally:
            file_path.unlink()

    def test_parse_json_file_not_found(self):
        """Test parsing non-existent file."""
        with pytest.raises(SecretsError, match="File not found"):
            parse_json_file(Path("/nonexistent/file.json"))


class TestParseEnvFile:
    """Test .env file parsing."""

    def test_parse_valid_env(self):
        """Test parsing valid .env file."""
        content = """
OPENAI_API_KEY=sk-xxx
DEBUG=false
DATABASE_URL=postgresql://localhost/db
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(content)
            f.flush()
            file_path = Path(f.name)

        try:
            result = parse_env_file(file_path)
            assert result == {
                "OPENAI_API_KEY": "sk-xxx",
                "DEBUG": "false",
                "DATABASE_URL": "postgresql://localhost/db",
            }
        finally:
            file_path.unlink()

    def test_parse_env_with_comments(self):
        """Test parsing .env file with comments."""
        content = """
# This is a comment
OPENAI_API_KEY=sk-xxx
# Another comment
DEBUG=false
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(content)
            f.flush()
            file_path = Path(f.name)

        try:
            result = parse_env_file(file_path)
            assert result == {"OPENAI_API_KEY": "sk-xxx", "DEBUG": "false"}
        finally:
            file_path.unlink()

    def test_parse_env_with_empty_lines(self):
        """Test parsing .env file with empty lines."""
        content = """
OPENAI_API_KEY=sk-xxx

DEBUG=false

"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(content)
            f.flush()
            file_path = Path(f.name)

        try:
            result = parse_env_file(file_path)
            assert result == {"OPENAI_API_KEY": "sk-xxx", "DEBUG": "false"}
        finally:
            file_path.unlink()

    def test_parse_env_with_quoted_values(self):
        """Test parsing .env file with quoted values."""
        content = """
API_KEY="sk-xxx"
MESSAGE='Hello World'
UNQUOTED=value
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(content)
            f.flush()
            file_path = Path(f.name)

        try:
            result = parse_env_file(file_path)
            assert result == {
                "API_KEY": "sk-xxx",
                "MESSAGE": "Hello World",
                "UNQUOTED": "value",
            }
        finally:
            file_path.unlink()

    def test_parse_env_with_spaces_in_value(self):
        """Test parsing .env file with spaces in values."""
        content = 'MESSAGE=Hello World'
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(content)
            f.flush()
            file_path = Path(f.name)

        try:
            result = parse_env_file(file_path)
            assert result == {"MESSAGE": "Hello World"}
        finally:
            file_path.unlink()

    def test_parse_env_with_equals_in_value(self):
        """Test parsing .env file with equals sign in value."""
        content = 'CONNECTION_STRING=postgresql://user:pass=secret@host'
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(content)
            f.flush()
            file_path = Path(f.name)

        try:
            result = parse_env_file(file_path)
            assert result == {"CONNECTION_STRING": "postgresql://user:pass=secret@host"}
        finally:
            file_path.unlink()

    def test_parse_env_invalid_format(self):
        """Test parsing .env file with invalid format."""
        content = "INVALID LINE WITHOUT EQUALS"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(content)
            f.flush()
            file_path = Path(f.name)

        try:
            with pytest.raises(SecretsError, match="Invalid format at line"):
                parse_env_file(file_path)
        finally:
            file_path.unlink()

    def test_parse_env_empty_key(self):
        """Test parsing .env file with empty key."""
        content = "=value"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(content)
            f.flush()
            file_path = Path(f.name)

        try:
            with pytest.raises(SecretsError, match="Empty key"):
                parse_env_file(file_path)
        finally:
            file_path.unlink()

    def test_parse_env_empty_file(self):
        """Test parsing empty .env file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("")
            f.flush()
            file_path = Path(f.name)

        try:
            result = parse_env_file(file_path)
            assert result == {}
        finally:
            file_path.unlink()

    def test_parse_env_file_not_found(self):
        """Test parsing non-existent .env file."""
        with pytest.raises(SecretsError, match="File not found"):
            parse_env_file(Path("/nonexistent/.env"))


class TestFormatSecretsTable:
    """Test secrets table formatting."""

    def test_format_empty_secrets(self):
        """Test formatting empty secrets."""
        result = format_secrets_table({})
        assert "No secrets found" in result

    def test_format_with_masking(self):
        """Test formatting with masked values."""
        secrets = {
            "OPENAI_API_KEY": "sk-1234567890",
            "DEBUG": "false",
        }
        result = format_secrets_table(secrets, mask=True)

        assert "Key" in result
        assert "Value (masked)" in result
        assert "OPENAI_API_KEY" in result
        assert "DEBUG" in result
        assert "sk-***" in result
        assert "fal***" in result
        assert "Total: 2 secret(s)" in result

    def test_format_without_masking(self):
        """Test formatting without masked values."""
        secrets = {
            "OPENAI_API_KEY": "sk-1234567890",
            "DEBUG": "false",
        }
        result = format_secrets_table(secrets, mask=False)

        assert "Key" in result
        assert "Value" in result
        assert "OPENAI_API_KEY" in result
        assert "sk-1234567890" in result
        assert "false" in result
        assert "Total: 2 secret(s)" in result

    def test_format_sorted(self):
        """Test that secrets are sorted by key."""
        secrets = {
            "ZETA": "value3",
            "ALPHA": "value1",
            "BETA": "value2",
        }
        result = format_secrets_table(secrets, mask=False)

        # Find positions in output
        alpha_pos = result.find("ALPHA")
        beta_pos = result.find("BETA")
        zeta_pos = result.find("ZETA")

        assert alpha_pos < beta_pos < zeta_pos
