"""Secrets management module for managing agent app environment variables/secrets."""

from typing import Optional, Dict, Any
import requests  # type: ignore
from urllib.parse import urljoin

from pixell.core.deployment import get_api_key, AuthenticationError


class SecretsError(Exception):
    """Base exception for secrets management errors."""

    pass


class SecretNotFoundError(SecretsError):
    """Secret or agent app not found."""

    pass


class SecretsClient:
    """Client for managing secrets for agent apps."""

    # Environment configurations (reuse from deployment)
    ENVIRONMENTS = {
        "local": {"base_url": "http://localhost:4000", "name": "Local Development"},
        "prod": {"base_url": "https://cloud.pixell.global", "name": "Production"},
    }

    def __init__(self, environment: str = "prod", api_key: Optional[str] = None):
        """Initialize secrets client.

        Args:
            environment: Deployment environment ('local' or 'prod')
            api_key: Optional API key for authentication

        Raises:
            ValueError: If environment is invalid
        """
        if environment not in self.ENVIRONMENTS:
            raise ValueError(
                f"Invalid environment: {environment}. Must be one of: {list(self.ENVIRONMENTS.keys())}"
            )

        self.environment = environment
        self.base_url = self.ENVIRONMENTS[environment]["base_url"]
        self.api_key = api_key or get_api_key()

        # Session for connection pooling
        self.session = requests.Session()
        if self.api_key:
            self.session.headers["Authorization"] = f"Bearer {self.api_key}"

    def list_secrets(self, app_id: str) -> Dict[str, str]:
        """List all secrets for an agent app.

        Args:
            app_id: The agent app ID

        Returns:
            Dictionary of secret key-value pairs

        Raises:
            AuthenticationError: If authentication fails
            SecretNotFoundError: If agent app not found
            SecretsError: If request fails
        """
        url = urljoin(self.base_url, f"/api/agent-apps/{app_id}/secrets")

        try:
            response = self.session.get(url, timeout=30)

            if response.status_code == 200:
                data = response.json()
                return data.get("secrets", {})
            elif response.status_code == 401:
                raise AuthenticationError("Invalid or missing API key")
            elif response.status_code == 404:
                raise SecretNotFoundError(f"Agent app not found: {app_id}")
            else:
                response.raise_for_status()
                return {}

        except requests.exceptions.RequestException as e:
            if isinstance(e, (AuthenticationError, SecretNotFoundError)):
                raise
            raise SecretsError(f"Failed to list secrets: {str(e)}")

    def get_secret(self, app_id: str, key: str) -> str:
        """Get a single secret value.

        Args:
            app_id: The agent app ID
            key: The secret key to retrieve

        Returns:
            The secret value

        Raises:
            AuthenticationError: If authentication fails
            SecretNotFoundError: If secret or agent app not found
            SecretsError: If request fails
        """
        secrets = self.list_secrets(app_id)

        if key not in secrets:
            raise SecretNotFoundError(f"Secret not found: {key}")

        return secrets[key]

    def set_secrets(self, app_id: str, secrets: Dict[str, str]) -> Dict[str, Any]:
        """Set/replace all secrets for an agent app (bulk operation).

        This replaces ALL secrets with the provided values.
        Existing secrets not in the request are deleted.

        Args:
            app_id: The agent app ID
            secrets: Dictionary of secret key-value pairs

        Returns:
            Response with success status and secret count

        Raises:
            AuthenticationError: If authentication fails
            SecretNotFoundError: If agent app not found
            SecretsError: If request fails
        """
        url = urljoin(self.base_url, f"/api/agent-apps/{app_id}/secrets")

        # Validate all values are strings
        for key, value in secrets.items():
            if not isinstance(value, str):
                raise SecretsError(f"Secret value for '{key}' must be a string")

        payload = {"secrets": secrets}

        try:
            response = self.session.post(url, json=payload, timeout=30)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 400:
                error_data = response.json()
                raise SecretsError(
                    f"Invalid request: {error_data.get('message', error_data.get('error'))}"
                )
            elif response.status_code == 401:
                raise AuthenticationError("Invalid or missing API key")
            elif response.status_code == 404:
                raise SecretNotFoundError(f"Agent app not found: {app_id}")
            else:
                response.raise_for_status()
                return response.json()

        except requests.exceptions.RequestException as e:
            if isinstance(e, (AuthenticationError, SecretNotFoundError, SecretsError)):
                raise
            raise SecretsError(f"Failed to set secrets: {str(e)}")

    def update_secret(self, app_id: str, key: str, value: str) -> Dict[str, Any]:
        """Update or create a single secret.

        Does not affect other secrets.

        Args:
            app_id: The agent app ID
            key: The secret key
            value: The secret value

        Returns:
            Response with success status and key

        Raises:
            AuthenticationError: If authentication fails
            SecretNotFoundError: If agent app not found
            SecretsError: If request fails or invalid key format
        """
        url = urljoin(self.base_url, f"/api/agent-apps/{app_id}/secrets/{key}")

        if not isinstance(value, str):
            raise SecretsError("Secret value must be a string")

        payload = {"value": value}

        try:
            response = self.session.put(url, json=payload, timeout=30)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 400:
                error_data = response.json()
                raise SecretsError(
                    f"Invalid request: {error_data.get('message', error_data.get('error'))}"
                )
            elif response.status_code == 401:
                raise AuthenticationError("Invalid or missing API key")
            elif response.status_code == 404:
                raise SecretNotFoundError(f"Agent app not found: {app_id}")
            else:
                response.raise_for_status()
                return response.json()

        except requests.exceptions.RequestException as e:
            if isinstance(e, (AuthenticationError, SecretNotFoundError, SecretsError)):
                raise
            raise SecretsError(f"Failed to update secret: {str(e)}")

    def delete_secret(self, app_id: str, key: str) -> Dict[str, Any]:
        """Delete a single secret.

        Args:
            app_id: The agent app ID
            key: The secret key to delete

        Returns:
            Response with success status and key

        Raises:
            AuthenticationError: If authentication fails
            SecretNotFoundError: If secret or agent app not found
            SecretsError: If request fails
        """
        url = urljoin(self.base_url, f"/api/agent-apps/{app_id}/secrets/{key}")

        try:
            response = self.session.delete(url, timeout=30)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                raise AuthenticationError("Invalid or missing API key")
            elif response.status_code == 404:
                raise SecretNotFoundError(f"Secret or agent app not found: {key}")
            else:
                response.raise_for_status()
                return response.json()

        except requests.exceptions.RequestException as e:
            if isinstance(e, (AuthenticationError, SecretNotFoundError)):
                raise
            raise SecretsError(f"Failed to delete secret: {str(e)}")

    def delete_all_secrets(self, app_id: str) -> Dict[str, Any]:
        """Delete all secrets for an agent app.

        Args:
            app_id: The agent app ID

        Returns:
            Response with success status

        Raises:
            AuthenticationError: If authentication fails
            SecretNotFoundError: If agent app not found
            SecretsError: If request fails
        """
        url = urljoin(self.base_url, f"/api/agent-apps/{app_id}/secrets")

        try:
            response = self.session.delete(url, timeout=30)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                raise AuthenticationError("Invalid or missing API key")
            elif response.status_code == 404:
                raise SecretNotFoundError(f"Agent app not found: {app_id}")
            else:
                response.raise_for_status()
                return response.json()

        except requests.exceptions.RequestException as e:
            if isinstance(e, (AuthenticationError, SecretNotFoundError)):
                raise
            raise SecretsError(f"Failed to delete all secrets: {str(e)}")
