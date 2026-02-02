"""Template Client - CRUD operations for templates via pixell-api.

This module provides a high-level client for managing email templates
through the pixell-api, including version history support.

Example:
    from pixell.services import TemplateClient
    from pixell.sdk import PXUIDataClient

    data_client = PXUIDataClient(base_url, jwt_token)
    templates = TemplateClient(data_client)

    # List templates
    result = await templates.list_templates()
    for t in result["items"]:
        print(f"{t['name']}: {t['subject']}")

    # Create a template
    template = await templates.create_template(
        name="Cold Outreach",
        subject="Quick question about {{company}}",
        body="Hey {{first_name}},\\n\\nI noticed...",
        variables=["first_name", "company"],
    )

    # Update with version history
    updated = await templates.update_template(
        template["id"],
        subject="New subject line",
        change_description="Updated subject for better open rates",
    )

    # List versions
    versions = await templates.list_versions(template["id"])

    # Restore a previous version
    restored = await templates.restore_version(template["id"], version_id)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pixell.sdk.data_client import PXUIDataClient


class TemplateClient:
    """Client for template CRUD operations via pixell-api.

    Provides methods for:
    - Listing, creating, updating, and deleting templates
    - Version history management
    - Template restoration

    All operations are authenticated via the PXUIDataClient's JWT token.
    """

    def __init__(self, data_client: "PXUIDataClient"):
        """Initialize TemplateClient.

        Args:
            data_client: PXUIDataClient instance with valid JWT token
        """
        self._api = data_client

    # ==================== Template CRUD ====================

    async def list_templates(
        self,
        page: int = 1,
        per_page: int = 50,
    ) -> dict[str, Any]:
        """List user's templates with pagination.

        Args:
            page: Page number (1-indexed)
            per_page: Items per page (1-100)

        Returns:
            Dict with:
            - items: List of template dicts
            - total: Total count
            - page: Current page
            - per_page: Items per page
            - has_more: Whether more pages exist
        """
        return await self._api._request(
            "GET",
            "/api/v1/templates",
            params={"page": page, "per_page": per_page},
        )

    async def get_template(self, template_id: str) -> dict[str, Any]:
        """Get a single template by ID.

        Args:
            template_id: Template UUID

        Returns:
            Template dict with all fields

        Raises:
            APIError: 404 if not found, 403 if not authorized
        """
        return await self._api._request(
            "GET",
            f"/api/v1/templates/{template_id}",
        )

    async def create_template(
        self,
        name: str,
        subject: str = "",
        body: str = "",
        preview_text: str | None = None,
        variables: list[str] | None = None,
        data_source_id: str | None = None,
        variable_configs: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Create a new template.

        Args:
            name: Template name (required)
            subject: Email subject line (can contain {{variables}})
            body: Template body (can contain {{variables}} and conditionals)
            preview_text: Email preview text
            variables: List of variable names used in template
            data_source_id: Optional Google Sheet ID for data source
            variable_configs: Optional variable configurations

        Returns:
            Created template dict

        Example:
            template = await client.create_template(
                name="Welcome Email",
                subject="Welcome to {{company}}, {{first_name}}!",
                body="Hey {{first_name}},\\n\\nWelcome aboard!",
                variables=["first_name", "company"],
            )
        """
        payload: dict[str, Any] = {"name": name, "subject": subject, "body": body}

        if preview_text is not None:
            payload["preview_text"] = preview_text
        if variables is not None:
            payload["variables"] = variables
        if data_source_id is not None:
            payload["data_source_id"] = data_source_id
        if variable_configs is not None:
            payload["variable_configs"] = variable_configs

        return await self._api._request(
            "POST",
            "/api/v1/templates",
            json=payload,
        )

    async def update_template(
        self,
        template_id: str,
        name: str | None = None,
        subject: str | None = None,
        body: str | None = None,
        preview_text: str | None = None,
        variables: list[str] | None = None,
        data_source_id: str | None = None,
        variable_configs: list[dict[str, Any]] | None = None,
        create_version: bool = True,
    ) -> dict[str, Any]:
        """Update an existing template.

        Only provided fields are updated. A version snapshot is automatically
        created before updating (unless create_version=False).

        Args:
            template_id: Template UUID
            name: New template name
            subject: New subject line
            body: New body content
            preview_text: New preview text
            variables: New variables list
            data_source_id: New data source ID
            variable_configs: New variable configurations
            create_version: Whether to create a version snapshot (default: True)

        Returns:
            Updated template dict

        Example:
            await client.update_template(
                template_id,
                subject="New subject line {{first_name}}",
            )
        """
        payload: dict[str, Any] = {}

        if name is not None:
            payload["name"] = name
        if subject is not None:
            payload["subject"] = subject
        if body is not None:
            payload["body"] = body
        if preview_text is not None:
            payload["preview_text"] = preview_text
        if variables is not None:
            payload["variables"] = variables
        if data_source_id is not None:
            payload["data_source_id"] = data_source_id
        if variable_configs is not None:
            payload["variable_configs"] = variable_configs

        return await self._api._request(
            "PATCH",
            f"/api/v1/templates/{template_id}",
            json=payload,
            params={"create_version": create_version},
        )

    async def delete_template(self, template_id: str) -> bool:
        """Delete a template.

        Args:
            template_id: Template UUID

        Returns:
            True if deleted successfully

        Raises:
            APIError: 404 if not found, 403 if not authorized
        """
        await self._api._request(
            "DELETE",
            f"/api/v1/templates/{template_id}",
        )
        return True

    # ==================== Version History ====================

    async def list_versions(self, template_id: str) -> dict[str, Any]:
        """List version history for a template.

        Args:
            template_id: Template UUID

        Returns:
            Dict with:
            - template_id: Template UUID
            - template_name: Current template name
            - versions: List of version dicts (most recent first)
            - total: Total version count
        """
        return await self._api._request(
            "GET",
            f"/api/v1/templates/{template_id}/versions",
        )

    async def get_version(
        self,
        template_id: str,
        version_id: str,
    ) -> dict[str, Any]:
        """Get a specific version of a template.

        Args:
            template_id: Template UUID
            version_id: Version UUID

        Returns:
            Version dict with full content snapshot
        """
        return await self._api._request(
            "GET",
            f"/api/v1/templates/{template_id}/versions/{version_id}",
        )

    async def restore_version(
        self,
        template_id: str,
        version_id: str,
    ) -> dict[str, Any]:
        """Restore a template to a previous version.

        This creates a new version snapshot before restoring, then updates
        the template content to match the specified version.

        Args:
            template_id: Template UUID
            version_id: Version UUID to restore

        Returns:
            Updated template dict with restored content
        """
        return await self._api._request(
            "POST",
            f"/api/v1/templates/{template_id}/restore/{version_id}",
        )

    # ==================== Utility Methods ====================

    async def extract_variables(self, text: str) -> list[str]:
        """Extract variable names from template text.

        Finds all {{variable}} patterns in the text.

        Args:
            text: Template text (subject or body)

        Returns:
            List of unique variable names
        """
        import re

        pattern = r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\|[^}]*)?\}\}"
        matches = re.findall(pattern, text)
        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for var in matches:
            if var not in seen:
                seen.add(var)
                unique.append(var)
        return unique

    async def create_with_auto_variables(
        self,
        name: str,
        subject: str,
        body: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Create a template with auto-extracted variables.

        Convenience method that extracts variables from subject and body
        automatically before creating the template.

        Args:
            name: Template name
            subject: Subject line
            body: Template body
            **kwargs: Additional arguments passed to create_template()

        Returns:
            Created template dict
        """
        # Extract variables from both subject and body
        subject_vars = await self.extract_variables(subject)
        body_vars = await self.extract_variables(body)

        # Combine and deduplicate
        all_vars = []
        seen = set()
        for var in subject_vars + body_vars:
            if var not in seen:
                seen.add(var)
                all_vars.append(var)

        return await self.create_template(
            name=name,
            subject=subject,
            body=body,
            variables=all_vars,
            **kwargs,
        )
