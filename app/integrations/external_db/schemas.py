"""
Pydantic schemas for external database data.

These schemas define the structure of data coming from the external database
before it gets transformed into ONTEX models.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    """Schema for search queries to the external database."""

    query: str = Field(..., description="Search query string")
    filters: dict[str, Any] = Field(default_factory=dict, description="Optional filters")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum results to return")
    offset: int = Field(default=0, ge=0, description="Offset for pagination")


class SearchResult(BaseModel):
    """Schema for individual search results from external database."""

    id: str = Field(..., description="Unique identifier from external database")
    title: str | None = Field(None, description="Title or name of the record")
    summary: str | None = Field(None, description="Brief summary or description")
    relevance_score: float = Field(default=0.0, description="Relevance score (0-1)")
    raw_data: dict[str, Any] = Field(default_factory=dict, description="Raw data from source")


class ExternalRecord(BaseModel):
    """Schema for a full record from the external database."""

    id: str = Field(..., description="Unique identifier")
    source: str = Field(..., description="Name of the external database")
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    data: dict[str, Any] = Field(..., description="Full record data")

    # TODO: Add specific fields for your external database
    # Example fields (customize based on your needs):
    # title: str | None = None
    # description: str | None = None
    # date: datetime | None = None
    # authors: list[str] = Field(default_factory=list)
    # metadata: dict[str, Any] = Field(default_factory=dict)
