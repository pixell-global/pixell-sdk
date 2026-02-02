"""File Reader Service - Read schema and data from spreadsheets.

This module provides tools for reading Google Sheets schema and data,
with intelligent column normalization for use as template variables.

Example:
    from pixell.tools.file_reader import FileReaderService, SheetSchema

    # Initialize with OAuth client
    file_reader = FileReaderService(oauth_client)

    # Get sheet schema for variable discovery
    schema = await file_reader.get_sheet_schema("1abc...xyz")

    # Schema includes normalized variable names
    for col in schema.columns:
        print(f"{col.name} -> {col.normalized_name}")  # "First Name" -> "first_name"
        print(f"  Samples: {col.sample_values}")
        print(f"  Is email: {col.is_email_column}")

    # Get full data for template rendering
    data = await file_reader.get_sheet_data("1abc...xyz")
    for row in data.rows:
        print(row)  # {"first_name": "Alex", "email": "alex@example.com", ...}
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from pixell.sdk.oauth import OAuthClient


@dataclass
class ColumnSchema:
    """Schema information for a single column.

    Attributes:
        name: Original column name from the sheet
        normalized_name: Cleaned name suitable for use as a template variable
        inferred_type: Detected data type ("text", "email", "number", "date", "url")
        sample_values: First 3-5 non-empty values for preview
        is_email_column: Whether this column appears to contain email addresses
    """

    name: str
    normalized_name: str
    inferred_type: str = "text"
    sample_values: list[str] = field(default_factory=list)
    is_email_column: bool = False

    @classmethod
    def from_column(cls, name: str, values: list[Any]) -> "ColumnSchema":
        """Create ColumnSchema from column name and values.

        Args:
            name: Original column header
            values: All values in the column (for type inference)

        Returns:
            ColumnSchema with inferred metadata
        """
        normalized = normalize_column_name(name)
        sample_values = _get_sample_values(values)
        inferred_type, is_email = _infer_column_type(name, values)

        return cls(
            name=name,
            normalized_name=normalized,
            inferred_type=inferred_type,
            sample_values=sample_values,
            is_email_column=is_email,
        )


@dataclass
class SheetSchema:
    """Schema information for a Google Sheet.

    Attributes:
        columns: List of column schemas
        row_count: Number of data rows (excluding header)
        sheet_name: Name of the sheet/tab
        sheet_id: Google Sheets ID
    """

    columns: list[ColumnSchema]
    row_count: int
    sheet_name: str
    sheet_id: str

    def get_column_by_name(self, name: str) -> ColumnSchema | None:
        """Get column by original or normalized name."""
        name_lower = name.lower()
        for col in self.columns:
            if col.name.lower() == name_lower or col.normalized_name == name_lower:
                return col
        return None

    def get_email_column(self) -> ColumnSchema | None:
        """Get the primary email column, if any."""
        for col in self.columns:
            if col.is_email_column:
                return col
        return None

    @property
    def variable_names(self) -> list[str]:
        """Get all normalized variable names."""
        return [col.normalized_name for col in self.columns]


@dataclass
class SheetData:
    """Full data from a Google Sheet.

    Attributes:
        schema: The sheet's schema
        rows: List of row dicts with normalized column names as keys
        raw_rows: List of row dicts with original column names as keys
    """

    schema: SheetSchema
    rows: list[dict[str, Any]]
    raw_rows: list[dict[str, Any]]

    @property
    def row_count(self) -> int:
        """Number of data rows."""
        return len(self.rows)


def normalize_column_name(name: str) -> str:
    """Normalize a column name for use as a template variable.

    Examples:
        "First Name" -> "first_name"
        "Email Address" -> "email_address"
        "이름" -> "이름" (preserve non-ASCII)
        "Company (Optional)" -> "company_optional"
        "Price ($)" -> "price"

    Args:
        name: Original column name

    Returns:
        Normalized variable name
    """
    if not name:
        return "unnamed"

    # Convert to lowercase
    result = name.strip().lower()

    # Replace common patterns
    result = result.replace(" ", "_")
    result = result.replace("-", "_")
    result = result.replace("(", "_")
    result = result.replace(")", "")
    result = result.replace("[", "_")
    result = result.replace("]", "")

    # Remove special characters except underscores and alphanumeric
    # Keep non-ASCII characters (like Korean, Chinese, etc.)
    result = re.sub(r"[^\w\u0080-\uffff]", "", result, flags=re.UNICODE)

    # Collapse multiple underscores
    result = re.sub(r"_+", "_", result)

    # Remove leading/trailing underscores
    result = result.strip("_")

    # Ensure it doesn't start with a number
    if result and result[0].isdigit():
        result = "_" + result

    return result or "column"


def _get_sample_values(values: list[Any], max_samples: int = 5) -> list[str]:
    """Get first N non-empty values as strings."""
    samples = []
    for val in values:
        if val is not None and str(val).strip():
            samples.append(str(val).strip())
            if len(samples) >= max_samples:
                break
    return samples


def _infer_column_type(name: str, values: list[Any]) -> tuple[str, bool]:
    """Infer column type and detect if it's an email column.

    Returns:
        Tuple of (type_string, is_email)
    """
    name_lower = name.lower()
    non_empty = [str(v).strip() for v in values if v is not None and str(v).strip()]

    # Check for email by name or content
    email_indicators = ["email", "e-mail", "mail", "이메일"]
    is_email_by_name = any(ind in name_lower for ind in email_indicators)

    # Check content for email pattern
    email_pattern = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")
    email_count = sum(1 for v in non_empty[:10] if email_pattern.match(v))
    is_email_by_content = email_count >= min(3, len(non_empty[:10]) // 2 + 1)

    is_email = is_email_by_name or is_email_by_content
    if is_email:
        return "email", True

    # Check for URLs
    url_pattern = re.compile(r"^https?://", re.IGNORECASE)
    if non_empty and all(url_pattern.match(v) for v in non_empty[:5]):
        return "url", False

    # Check for dates
    date_indicators = ["date", "날짜", "created", "updated", "timestamp"]
    if any(ind in name_lower for ind in date_indicators):
        return "date", False

    # Check for numbers
    try:
        if non_empty and all(
            v.replace(",", "").replace(".", "").replace("-", "").isdigit()
            for v in non_empty[:5]
        ):
            return "number", False
    except (ValueError, AttributeError):
        pass

    return "text", False


class FileReaderService:
    """Service for reading Google Sheets schema and data.

    This service provides high-level methods for:
    - Getting sheet schema (columns, types, samples) for variable discovery
    - Getting full sheet data for template rendering

    All column names are automatically normalized for use as template variables.
    """

    SHEETS_API_BASE = "https://sheets.googleapis.com/v4/spreadsheets"

    def __init__(self, oauth_client: "OAuthClient"):
        """Initialize FileReaderService.

        Args:
            oauth_client: OAuthClient for getting Google OAuth tokens
        """
        self._oauth = oauth_client
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def _get_auth_headers(self) -> dict[str, str]:
        """Get authorization headers for Google Sheets API."""
        token = await self._oauth.get_token("google")
        return {"Authorization": f"Bearer {token.access_token}"}

    async def get_sheet_schema(
        self,
        sheet_id: str,
        tab_name: str | None = None,
    ) -> SheetSchema:
        """Get schema information for a Google Sheet.

        Args:
            sheet_id: The Google Sheets ID (from URL)
            tab_name: Optional specific tab/sheet name. If not provided,
                     uses the first sheet.

        Returns:
            SheetSchema with columns, types, and sample values.

        Raises:
            OAuthNotConnectedError: If Google is not connected
            httpx.HTTPError: On API errors
        """
        client = await self._get_client()
        headers = await self._get_auth_headers()

        # First, get spreadsheet metadata to find the sheet name
        if not tab_name:
            meta_url = f"{self.SHEETS_API_BASE}/{sheet_id}"
            meta_resp = await client.get(
                meta_url,
                headers=headers,
                params={"fields": "sheets.properties.title"},
            )
            meta_resp.raise_for_status()
            meta = meta_resp.json()
            sheets = meta.get("sheets", [])
            if sheets:
                tab_name = sheets[0]["properties"]["title"]
            else:
                tab_name = "Sheet1"

        # Fetch data to infer schema (limit to reasonable amount for schema)
        range_spec = f"'{tab_name}'!A1:ZZ101"  # Header + 100 rows
        url = f"{self.SHEETS_API_BASE}/{sheet_id}/values/{range_spec}"

        response = await client.get(
            url,
            headers=headers,
            params={"majorDimension": "ROWS", "valueRenderOption": "FORMATTED_VALUE"},
        )
        response.raise_for_status()
        data = response.json()

        values = data.get("values", [])
        if not values:
            return SheetSchema(
                columns=[],
                row_count=0,
                sheet_name=tab_name,
                sheet_id=sheet_id,
            )

        # First row is headers
        headers_row = values[0]
        data_rows = values[1:]

        # Build column schemas
        columns = []
        for i, header in enumerate(headers_row):
            col_values = [row[i] if i < len(row) else None for row in data_rows]
            columns.append(ColumnSchema.from_column(header, col_values))

        return SheetSchema(
            columns=columns,
            row_count=len(data_rows),
            sheet_name=tab_name,
            sheet_id=sheet_id,
        )

    async def get_sheet_data(
        self,
        sheet_id: str,
        tab_name: str | None = None,
        max_rows: int | None = None,
    ) -> SheetData:
        """Get full data from a Google Sheet.

        Args:
            sheet_id: The Google Sheets ID (from URL)
            tab_name: Optional specific tab/sheet name
            max_rows: Optional limit on number of rows to fetch

        Returns:
            SheetData with schema and normalized row data.
        """
        client = await self._get_client()
        headers = await self._get_auth_headers()

        # Get metadata if no tab name specified
        if not tab_name:
            meta_url = f"{self.SHEETS_API_BASE}/{sheet_id}"
            meta_resp = await client.get(
                meta_url,
                headers=headers,
                params={"fields": "sheets.properties.title"},
            )
            meta_resp.raise_for_status()
            meta = meta_resp.json()
            sheets = meta.get("sheets", [])
            if sheets:
                tab_name = sheets[0]["properties"]["title"]
            else:
                tab_name = "Sheet1"

        # Fetch all data
        if max_rows:
            range_spec = f"'{tab_name}'!A1:ZZ{max_rows + 1}"  # +1 for header
        else:
            range_spec = f"'{tab_name}'"

        url = f"{self.SHEETS_API_BASE}/{sheet_id}/values/{range_spec}"
        response = await client.get(
            url,
            headers=headers,
            params={"majorDimension": "ROWS", "valueRenderOption": "FORMATTED_VALUE"},
        )
        response.raise_for_status()
        data = response.json()

        values = data.get("values", [])
        if not values:
            return SheetData(
                schema=SheetSchema(
                    columns=[],
                    row_count=0,
                    sheet_name=tab_name,
                    sheet_id=sheet_id,
                ),
                rows=[],
                raw_rows=[],
            )

        # Parse header and data
        headers_row = values[0]
        data_rows = values[1:]

        # Build schema
        columns = []
        for i, header in enumerate(headers_row):
            col_values = [row[i] if i < len(row) else None for row in data_rows]
            columns.append(ColumnSchema.from_column(header, col_values))

        schema = SheetSchema(
            columns=columns,
            row_count=len(data_rows),
            sheet_name=tab_name,
            sheet_id=sheet_id,
        )

        # Build row dicts with both normalized and raw keys
        rows = []
        raw_rows = []
        for row_data in data_rows:
            normalized_row = {}
            raw_row = {}
            for i, col in enumerate(columns):
                val = row_data[i] if i < len(row_data) else ""
                normalized_row[col.normalized_name] = val
                raw_row[col.name] = val
            rows.append(normalized_row)
            raw_rows.append(raw_row)

        return SheetData(schema=schema, rows=rows, raw_rows=raw_rows)

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


# Exports
__all__ = [
    "FileReaderService",
    "SheetSchema",
    "SheetData",
    "ColumnSchema",
    "normalize_column_name",
]
