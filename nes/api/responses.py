"""Response models for nes API.

This module defines Pydantic models for API responses, ensuring consistent
response formats across all endpoints.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Detailed error information for a specific field or validation."""

    field: Optional[str] = Field(None, description="Field that caused the error")
    message: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code")


class ErrorResponse(BaseModel):
    """Standard error response format."""

    error: Dict[str, Any] = Field(
        ...,
        description="Error information",
        examples=[{"code": "NOT_FOUND", "message": "Entity not found", "details": []}],
    )


class EntityListResponse(BaseModel):
    """Response model for entity list/search endpoints."""

    model_config = {"exclude_none": True}

    entities: List[Dict[str, Any]] = Field(..., description="List of entities")
    total: int = Field(..., description="Total number of matching entities")
    limit: Optional[int] = Field(
        default=None,
        description="Maximum number of results returned (search mode only)",
    )
    offset: Optional[int] = Field(
        default=None, description="Number of results skipped (search mode only)"
    )
    requested: Optional[int] = Field(
        default=None, description="Number of entities requested (batch mode only)"
    )
    not_found: Optional[List[str]] = Field(
        default=None, description="Entity IDs not found (batch mode only)"
    )


class RelationshipListResponse(BaseModel):
    """Response model for relationship list endpoints."""

    relationships: List[Dict[str, Any]] = Field(
        ..., description="List of relationships"
    )
    total: int = Field(..., description="Total number of matching relationships")
    limit: int = Field(..., description="Maximum number of results returned")
    offset: int = Field(..., description="Number of results skipped")


class VersionListResponse(BaseModel):
    """Response model for version list endpoints."""

    versions: List[Dict[str, Any]] = Field(..., description="List of versions")
    total: int = Field(..., description="Total number of versions")
    limit: int = Field(..., description="Maximum number of results returned")
    offset: int = Field(..., description="Number of results skipped")


class EntityPrefixListResponse(BaseModel):
    """Response model for entity prefix list endpoint."""

    prefixes: List[str] = Field(..., description="List of available entity prefixes")


class EntityPrefixSchemaResponse(BaseModel):
    """Response model for entity prefix schema endpoint."""

    prefix: str = Field(..., description="The entity prefix")
    description: str = Field(..., description="Description of the entity type")
    json_schema: Dict[str, Any] = Field(
        ..., description="JSON schema for the entity type"
    )


class RelationshipSchemaResponse(BaseModel):
    """Response model for relationship schema endpoint."""

    relationship_types: List[str] = Field(
        ..., description="Available relationship types"
    )


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str = Field(..., description="Overall health status")
    version: str = Field(..., description="API version")
    api_version: str = Field(..., description="API version number")
    database: Dict[str, str] = Field(..., description="Database status")
    timestamp: datetime = Field(..., description="Health check timestamp")
