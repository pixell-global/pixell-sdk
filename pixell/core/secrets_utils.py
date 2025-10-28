"""Utility functions for secrets management."""

import json
import re
from pathlib import Path
from typing import Dict

from pixell.core.secrets import SecretsError


def validate_secret_key(key: str) -> bool:
    """Validate a secret key format.

    Secret keys must contain only uppercase letters, numbers, and underscores.

    Args:
        key: The secret key to validate

    Returns:
        True if valid, False otherwise
    """
    pattern = r"^[A-Z0-9_]+$"
    return bool(re.match(pattern, key))


def mask_secret_value(value: str, show_chars: int = 3) -> str:
    """Mask a secret value for display.

    Shows the first N characters followed by asterisks.

    Args:
        value: The secret value to mask
        show_chars: Number of characters to show (default: 3)

    Returns:
        Masked value (e.g., "sk-***")
    """
    if not value:
        return "***"

    if len(value) <= show_chars:
        return "***"

    return value[:show_chars] + "***"


def parse_json_file(file_path: Path) -> Dict[str, str]:
    """Parse a JSON file containing secrets.

    Expected format: {"KEY": "value", "KEY2": "value2"}

    Args:
        file_path: Path to the JSON file

    Returns:
        Dictionary of secret key-value pairs

    Raises:
        SecretsError: If file cannot be read or parsed
    """
    try:
        with open(file_path, "r") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise SecretsError("JSON file must contain an object/dictionary at the root")

        # Validate all values are strings
        secrets = {}
        for key, value in data.items():
            if not isinstance(value, str):
                raise SecretsError(f"Secret value for '{key}' must be a string, got {type(value).__name__}")
            secrets[key] = value

        return secrets

    except FileNotFoundError:
        raise SecretsError(f"File not found: {file_path}")
    except json.JSONDecodeError as e:
        raise SecretsError(f"Invalid JSON format: {e}")
    except Exception as e:
        raise SecretsError(f"Failed to read JSON file: {e}")


def parse_env_file(file_path: Path) -> Dict[str, str]:
    """Parse a .env file containing secrets.

    Expected format:
    KEY=value
    KEY2=value2
    # Comments are ignored

    Supports:
    - Comments (lines starting with #)
    - Empty lines
    - Quoted values (single or double quotes)
    - Values with spaces

    Args:
        file_path: Path to the .env file

    Returns:
        Dictionary of secret key-value pairs

    Raises:
        SecretsError: If file cannot be read or parsed
    """
    try:
        secrets = {}

        with open(file_path, "r") as f:
            for line_num, line in enumerate(f, 1):
                # Strip whitespace
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                # Parse KEY=VALUE
                if "=" not in line:
                    raise SecretsError(
                        f"Invalid format at line {line_num}: '{line}'. Expected KEY=VALUE format."
                    )

                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                # Remove quotes if present
                if value and value[0] in ('"', "'") and value[-1] == value[0]:
                    value = value[1:-1]

                if not key:
                    raise SecretsError(f"Empty key at line {line_num}")

                secrets[key] = value

        return secrets

    except FileNotFoundError:
        raise SecretsError(f"File not found: {file_path}")
    except SecretsError:
        raise
    except Exception as e:
        raise SecretsError(f"Failed to read .env file: {e}")


def format_secrets_table(secrets: Dict[str, str], mask: bool = True) -> str:
    """Format secrets as a table.

    Args:
        secrets: Dictionary of secret key-value pairs
        mask: Whether to mask secret values (default: True)

    Returns:
        Formatted table string
    """
    if not secrets:
        return "No secrets found."

    # Calculate column widths
    max_key_len = max(len(key) for key in secrets.keys())
    max_val_len = max(len(mask_secret_value(val) if mask else val) for val in secrets.values())

    key_width = max(20, max_key_len + 2)
    val_width = max(20, max_val_len + 2)

    # Header
    header = f"{'Key':<{key_width}} {'Value' if not mask else 'Value (masked)':<{val_width}}"
    separator = "━" * len(header)

    lines = [header, separator]

    # Rows
    for key, value in sorted(secrets.items()):
        display_value = mask_secret_value(value) if mask else value
        lines.append(f"{key:<{key_width}} {display_value:<{val_width}}")

    lines.append("")
    lines.append(f"Total: {len(secrets)} secret(s)")

    return "\n".join(lines)
