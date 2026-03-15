"""Schema endpoints for nes API.

This module provides endpoints for discovering available entity types,
subtypes, and relationship types:
- GET /api/entity_prefixes - List all available entity prefixes
- GET /api/entity_prefixes/{prefix}/schema - Get schema for a specific entity prefix
- GET /api/schemas/relationships - Get relationship type schemas
"""

import logging

from fastapi import APIRouter, HTTPException, Path

from nes.api.responses import (
    EntityPrefixListResponse,
    EntityPrefixSchemaResponse,
    RelationshipSchemaResponse,
)
from nes.core.models.entity_type_map import ALLOWED_ENTITY_PREFIXES, ENTITY_PREFIX_MAP

logger = logging.getLogger(__name__)

router = APIRouter(tags=["schemas"])


@router.get("/api/entity_prefixes", response_model=EntityPrefixListResponse)
async def list_entity_prefixes():
    """List all available entity prefixes.

    Returns a simple list of all supported entity prefix strings,
    reflecting Nepal's political and administrative structure.

    Returns:
        List of entity prefix strings
    """
    return EntityPrefixListResponse(prefixes=sorted(ALLOWED_ENTITY_PREFIXES))


@router.get("/api/entity_prefixes/{prefix:path}/schema", response_model=EntityPrefixSchemaResponse)
async def get_entity_prefix_schema(
    prefix: str = Path(..., description="Entity prefix (e.g., 'person', 'organization/political_party')")
):
    """Get the JSON schema for a specific entity prefix.

    Returns the Pydantic model schema for the specified entity prefix,
    which can be used for validation and documentation.

    Args:
        prefix: The entity prefix to get the schema for

    Returns:
        JSON schema for the entity type

    Raises:
        HTTPException: 404 if the prefix is not found
    """
    if prefix not in ALLOWED_ENTITY_PREFIXES:
        raise HTTPException(
            status_code=404,
            detail=f"Entity prefix '{prefix}' not found. Use /api/entity_prefixes to see available prefixes."
        )
    
    # Get the entity class for this prefix
    entity_class = ENTITY_PREFIX_MAP.get(prefix)
    
    if entity_class is None:
        raise HTTPException(
            status_code=500,
            detail=f"Entity class not found for prefix '{prefix}'"
        )
    
    # Get the JSON schema from the Pydantic model
    schema = entity_class.model_json_schema()
    
    return EntityPrefixSchemaResponse(
        prefix=prefix,
        description=_get_entity_prefix_description(prefix),
        json_schema=schema
    )


@router.get("/api/schemas/relationships", response_model=RelationshipSchemaResponse)
async def get_relationship_schemas():
    """Get available relationship types.

    Returns a list of all valid relationship types that can be used
    to connect entities.

    Returns:
        List of relationship type names
    """
    relationship_types = [
        "AFFILIATED_WITH",
        "EMPLOYED_BY",
        "MEMBER_OF",
        "PARENT_OF",
        "CHILD_OF",
        "SUPERVISES",
        "LOCATED_IN",
    ]

    return RelationshipSchemaResponse(relationship_types=relationship_types)


def _get_entity_prefix_description(prefix: str) -> str:
    """Get a description for an entity prefix.

    Args:
        prefix: The entity prefix (e.g., "person", "organization/political_party")

    Returns:
        Description string
    """
    descriptions = {
        # Person
        "person": "Individuals including politicians, civil servants, and public figures",
        
        # Organization
        "organization": "Organizations (general)",
        "organization/political_party": "Registered political parties in Nepal",
        "organization/government_body": "Government ministries, departments, and constitutional bodies",
        "organization/hospital": "Hospitals and health facilities",
        "organization/ngo": "Non-governmental organizations",
        "organization/international_org": "International organizations operating in Nepal",
        
        # Location
        "location": "Geographic locations (general)",
        "location/province": "Nepal's 7 provinces (प्रदेश)",
        "location/district": "Nepal's 77 districts (जिल्ला)",
        "location/metropolitan_city": "Metropolitan cities (महानगरपालिका) - 6 cities with >300k population",
        "location/sub_metropolitan_city": "Sub-metropolitan cities (उपमहानगरपालिका) - cities with 100k-300k population",
        "location/municipality": "Municipalities (नगरपालिका) - urban local bodies",
        "location/rural_municipality": "Rural municipalities (गाउँपालिका) - rural local bodies",
        "location/ward": "Wards (वडा) - smallest administrative unit",
        "location/constituency": "Electoral constituencies (निर्वाचन क्षेत्र)",
        
        # Project
        "project": "Development projects and initiatives (general)",
        "project/development_project": "Development projects (विकास परियोजना)",
    }

    return descriptions.get(prefix, f"Entity type: {prefix}")
