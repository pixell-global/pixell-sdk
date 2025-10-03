from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Tuple


def parse_dotenv(dotenv_path: Path) -> Dict[str, str]:
    """Parse a simple .env file with KEY=VALUE pairs.

    - Ignores blank lines and lines starting with '#'
    - Trims whitespace around keys/values
    - Strips matching single or double quotes around values
    - Does not support multi-line values
    """
    env: Dict[str, str] = {}
    if not dotenv_path.exists():
        return env
    try:
        content = dotenv_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return env

    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if (value.startswith("'") and value.endswith("'")) or (
            value.startswith('"') and value.endswith('"')
        ):
            if len(value) >= 2:
                value = value[1:-1]
        env[key] = value
    return env


def merge_envs(
    base: Dict[str, str], *overrides: Iterable[Tuple[str, str]] | Dict[str, str]
) -> Dict[str, str]:
    """Merge multiple environment dictionaries in order.

    Later dictionaries override earlier ones. Accepts dicts or iterables of (k, v).
    Returns a new dict without mutating inputs.
    """
    merged: Dict[str, str] = dict(base)
    for layer in overrides:
        if isinstance(layer, dict):
            for k, v in layer.items():
                merged[str(k)] = str(v)
        else:
            for k, v in layer:  # type: ignore[assignment]
                merged[str(k)] = str(v)
    return merged
