from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional
import json
import os


class SecretsProvider:
    """Abstract interface for fetching secrets as a dict of environment variables."""

    def fetch_secrets(self) -> Dict[str, str]:  # pragma: no cover - interface only
        raise NotImplementedError


class EnvSecretsProvider(SecretsProvider):
    """Returns current process environment as secrets (useful in local/dev)."""

    def fetch_secrets(self) -> Dict[str, str]:
        return dict(os.environ)


class StaticSecretsProvider(SecretsProvider):
    """Returns a static mapping of secrets provided at construction time."""

    def __init__(self, secrets: Dict[str, str]):
        self._secrets = dict(secrets)

    def fetch_secrets(self) -> Dict[str, str]:
        return dict(self._secrets)


@dataclass
class AWSSecretsConfig:
    """Configuration for AWS Secrets Manager provider.

    Attributes:
        secret_ids: Comma separated secret names or ARNs to fetch
        region_name: AWS region, optional (uses default chain if not set)
    """

    secret_ids: str
    region_name: Optional[str] = None


class AWSSecretsManagerProvider(SecretsProvider):
    """Fetch secrets from AWS Secrets Manager.

    Each secret is fetched via GetSecretValue. If SecretString is JSON, merge keys; otherwise
    use the secret id as the key with the string value.
    """

    def __init__(self, config: AWSSecretsConfig, client: Optional[object] = None):
        self.config = config
        self._client = client

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:  # Lazy import to avoid hard dependency
            import boto3  # type: ignore
        except Exception as exc:  # pragma: no cover - env dependent
            raise RuntimeError("boto3 is required for AWSSecretsManagerProvider") from exc
        kwargs = {}
        if self.config.region_name:
            kwargs["region_name"] = self.config.region_name
        self._client = boto3.client("secretsmanager", **kwargs)
        return self._client

    def fetch_secrets(self) -> Dict[str, str]:
        client = self._get_client()
        out: Dict[str, str] = {}
        for secret_id in [s.strip() for s in self.config.secret_ids.split(",") if s.strip()]:
            resp = client.get_secret_value(SecretId=secret_id)
            value = resp.get("SecretString", "")
            if not value:
                continue
            try:
                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    for k, v in parsed.items():
                        out[str(k)] = str(v)
                else:
                    out[secret_id] = str(parsed)
            except json.JSONDecodeError:
                out[secret_id] = value
        return out


def get_provider_from_env() -> Optional[SecretsProvider]:
    """Build a secrets provider from environment variables.

    Selection via PIXELL_SECRETS_PROVIDER:
        - "env": EnvSecretsProvider
        - "static": StaticSecretsProvider using PIXELL_SECRETS_JSON (JSON mapping)
        - "aws": AWSSecretsManagerProvider using PIXELL_AWS_SECRETS (comma-separated ids)
                and optional PIXELL_AWS_REGION

    Returns None when not configured.
    """
    provider = os.getenv("PIXELL_SECRETS_PROVIDER", "").strip().lower()
    if not provider:
        # Allow simple static mapping with PIXELL_SECRETS_JSON without specifying provider
        static_json = os.getenv("PIXELL_SECRETS_JSON")
        if static_json:
            try:
                data = json.loads(static_json)
                if isinstance(data, dict):
                    return StaticSecretsProvider({str(k): str(v) for k, v in data.items()})
            except Exception:
                return None
        return None

    if provider == "env":
        return EnvSecretsProvider()
    if provider == "static":
        raw = os.getenv("PIXELL_SECRETS_JSON", "{}")
        try:
            data = json.loads(raw)
        except Exception as exc:
            raise RuntimeError("Invalid PIXELL_SECRETS_JSON: must be JSON object") from exc
        if not isinstance(data, dict):
            raise RuntimeError("PIXELL_SECRETS_JSON must be a JSON object")
        return StaticSecretsProvider({str(k): str(v) for k, v in data.items()})
    if provider == "aws":
        secret_ids = os.getenv("PIXELL_AWS_SECRETS", "").strip()
        if not secret_ids:
            raise RuntimeError("PIXELL_AWS_SECRETS is required when provider=aws")
        region = os.getenv("PIXELL_AWS_REGION") or None
        return AWSSecretsManagerProvider(
            AWSSecretsConfig(secret_ids=secret_ids, region_name=region)
        )

    raise RuntimeError(f"Unknown PIXELL_SECRETS_PROVIDER: {provider}")
