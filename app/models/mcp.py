from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class McpToolCatalogEntry(BaseModel):
    """Safe subset of MCP tool metadata used for explicit human review."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)
    title: str | None = None
    description: str | None = None
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None = None
    read_only_hint: bool | None = None
    destructive_hint: bool | None = None
