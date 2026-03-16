"""Entity endpoints for nes API.

This module provides endpoints for entity search, retrieval, and filtering:
- GET /api/entities - List/search entities with filtering and pagination
- GET /api/entities/{entity_id} - Get a specific entity by ID
- GET /api/entities/{entity_id}/versions - Get version history for an entity
- GET /api/entities/{entity_id}/relationships - Get relationships for an entity
"""

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from nes.api.app import get_search_service
from nes.api.responses import (
    EntityListResponse,
    RelationshipListResponse,
    VersionListResponse,
)
from nes.core.models.entity import EntityType
from nes.core.models.entity_type_map import ALLOWED_ENTITY_PREFIXES
from nes.services.search import SearchService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/entities", tags=["entities"])


@router.get("", response_model=EntityListResponse, response_model_exclude_none=True)
async def list_entities(
    ids: Optional[str] = Query(
        None, description="Comma-separated entity IDs for batch lookup (max 25)"
    ),
    query: Optional[str] = Query(
        None, description="Text query to search in entity names"
    ),
    entity_type: Optional[str] = Query(
        None,
        description="(Deprecated: use entity_prefix) Filter by entity type (person, organization, location)",
    ),
    sub_type: Optional[str] = Query(
        None, description="(Deprecated: use entity_prefix) Filter by entity subtype"
    ),
    entity_prefix: Optional[str] = Query(
        None,
        description=(
            "Filter by N-level entity prefix using startswith logic "
            "(e.g. 'organization/nepal_govt' matches all nepal_govt children). "
            "Must be a value registered in ALLOWED_ENTITY_PREFIXES."
        ),
    ),
    attributes: Optional[str] = Query(
        None, description="Filter by attributes (JSON object)"
    ),
    tags: Optional[str] = Query(
        None,
        description="Comma-separated tags to filter by (AND logic - entity must have ALL tags)",
    ),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    search_service: SearchService = Depends(get_search_service),
):
    """List or search entities with optional filtering and pagination.

    Supports two modes:
    1. Batch lookup: Provide 'ids' parameter to fetch specific entities (max 25)
    2. Search/filter: Provide 'query', 'entity_type', etc. to search entities

    The 'ids' parameter cannot be combined with any other parameters.

    Examples:
    - /api/entities?ids=entity:person/ram-chandra-poudel,entity:person/kp-sharma-oli - Batch lookup
    - /api/entities - List all entities
    - /api/entities?query=poudel - Search for "poudel"
    - /api/entities?entity_type=person - List all persons
    - /api/entities?entity_type=organization&sub_type=political_party - List political parties
    - /api/entities?attributes={"party":"nepali-congress"} - Filter by attributes
    - /api/entities?tags=politician,senior-leader - Filter by tags (AND logic)
    """
    if entity_type is not None or sub_type is not None:
        logger.warning(
            "Deprecated filter used: entity_type=%s sub_type=%s — use entity_prefix instead",
            entity_type,
            sub_type,
        )

    # Validate mutually exclusive parameters
    other_params = [
        query,
        entity_type,
        sub_type,
        entity_prefix,
        attributes,
        tags,
        limit != 100,
        offset != 0,
    ]

    if ids is not None and any(other_params):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "The 'ids' parameter cannot be combined with other parameters",
                }
            },
        )

    # Batch lookup mode
    if ids is not None:
        return await _batch_lookup_entities(ids=ids, search_service=search_service)

    # Validate entity_type if provided
    valid_types = [t.value for t in EntityType]
    if entity_type and entity_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_ENTITY_TYPE",
                    "message": f"Invalid entity_type: {entity_type}. Must be one of: {', '.join(valid_types)}",
                }
            },
        )

    # Validate entity_prefix if provided
    if entity_prefix is not None:
        if entity_prefix not in ALLOWED_ENTITY_PREFIXES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "INVALID_ENTITY_PREFIX",
                        "message": (
                            f"Invalid entity_prefix: '{entity_prefix}'. "
                            "Must be a registered prefix in ALLOWED_ENTITY_PREFIXES."
                        ),
                    }
                },
            )

    # Parse attributes JSON if provided
    attr_filters = None
    if attributes:
        try:
            attr_filters = json.loads(attributes)
            if not isinstance(attr_filters, dict):
                raise ValueError("Attributes must be a JSON object")
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "INVALID_ATTRIBUTES",
                        "message": f"Invalid attributes JSON: {str(e)}",
                    }
                },
            )

    # Parse tags parameter (comma-separated list)
    tags_list: Optional[List[str]] = None
    if tags:
        # Split by comma and trim whitespace, filter out empty strings
        tags_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        # If all tags were empty/whitespace, treat as no filter
        if not tags_list:
            tags_list = None

    # Search entities
    try:
        entities = await search_service.search_entities(
            query=query,
            entity_type=entity_type,
            sub_type=sub_type,
            entity_prefix=entity_prefix,
            attributes=attr_filters,
            tags=tags_list,
            limit=limit,
            offset=offset,
        )

        # Convert entities to dict format
        entity_dicts = [entity.model_dump(mode="json") for entity in entities]

        # For now, total is the count of returned entities
        # In a real implementation, we'd query the total count separately
        total = len(entity_dicts)

        return EntityListResponse(
            entities=entity_dicts, total=total, limit=limit, offset=offset
        )

    except Exception as e:
        logger.error(f"Error searching entities: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "SEARCH_ERROR",
                    "message": "An error occurred while searching entities",
                }
            },
        )


@router.get("/tags")
async def list_tags(search_service: SearchService = Depends(get_search_service)):
    """Return all unique tag values present in the database."""
    tags = await search_service.get_all_tags()
    return {"tags": tags}


@router.get("/{entity_id:path}")
async def get_entity(
    entity_id: str = Path(
        ..., description="Entity ID (e.g., entity:person/ram-chandra-poudel)"
    ),
    search_service: SearchService = Depends(get_search_service),
):
    """Get a specific entity by its ID.

    Returns the complete entity data including names, attributes, identifiers,
    and version information.

    Args:
        entity_id: The unique entity identifier

    Returns:
        Entity data as JSON

    Raises:
        404: If entity is not found
    """
    try:
        entity = await search_service.get_entity(entity_id)

        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Entity {entity_id} not found",
                    }
                },
            )

        return entity.model_dump(mode="json")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving entity {entity_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "RETRIEVAL_ERROR",
                    "message": "An error occurred while retrieving the entity",
                }
            },
        )


@router.get("/{entity_id:path}/versions", response_model=VersionListResponse)
async def get_entity_versions(
    entity_id: str = Path(..., description="Entity ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of versions"),
    offset: int = Query(0, ge=0, description="Number of versions to skip"),
    search_service: SearchService = Depends(get_search_service),
):
    """Get version history for an entity.

    Returns all versions for the specified entity, sorted by version number
    in ascending order (oldest first).

    Args:
        entity_id: The entity ID to get versions for
        limit: Maximum number of versions to return
        offset: Number of versions to skip

    Returns:
        List of versions with snapshots
    """
    try:
        versions = await search_service.get_entity_versions(
            entity_id=entity_id, limit=limit, offset=offset
        )

        # Convert versions to dict format
        version_dicts = [version.model_dump(mode="json") for version in versions]

        return VersionListResponse(
            versions=version_dicts, total=len(version_dicts), limit=limit, offset=offset
        )

    except Exception as e:
        logger.error(f"Error retrieving versions for {entity_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "VERSION_ERROR",
                    "message": "An error occurred while retrieving versions",
                }
            },
        )


@router.get("/{entity_id:path}/relationships", response_model=RelationshipListResponse)
async def get_entity_relationships(
    entity_id: str = Path(..., description="Entity ID"),
    relationship_type: Optional[str] = Query(
        None, description="Filter by relationship type"
    ),
    currently_active: Optional[bool] = Query(
        None, description="Filter for currently active relationships"
    ),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of relationships"
    ),
    offset: int = Query(0, ge=0, description="Number of relationships to skip"),
    search_service: SearchService = Depends(get_search_service),
):
    """Get all relationships for an entity.

    Returns relationships where the entity is either the source or target.
    Supports filtering by relationship type and temporal constraints.

    Args:
        entity_id: The entity ID to get relationships for
        relationship_type: Optional filter by relationship type
        currently_active: Optional filter for relationships with no end date
        limit: Maximum number of relationships to return
        offset: Number of relationships to skip

    Returns:
        List of relationships
    """
    try:
        relationships = await search_service.search_relationships(
            source_entity_id=entity_id,
            relationship_type=relationship_type,
            currently_active=currently_active,
            limit=limit,
            offset=offset,
        )

        # Convert relationships to dict format
        relationship_dicts = [rel.model_dump(mode="json") for rel in relationships]

        return RelationshipListResponse(
            relationships=relationship_dicts,
            total=len(relationship_dicts),
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        logger.error(
            f"Error retrieving relationships for {entity_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "RELATIONSHIP_ERROR",
                    "message": "An error occurred while retrieving relationships",
                }
            },
        )


# ============================================================================
# Helper Functions
# ============================================================================


async def _batch_lookup_entities(
    ids: str,
    search_service: SearchService,
) -> EntityListResponse:
    """Handle batch entity lookup by IDs.

    Args:
        ids: Comma-separated entity IDs
        search_service: Search service instance

    Returns:
        EntityListResponse with batch lookup results

    Raises:
        HTTPException: If validation fails or batch size exceeded
    """
    # Validate ids parameter is not empty or whitespace
    if not ids or not ids.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "At least one entity ID is required",
                }
            },
        )

    # Parse comma-separated entity IDs
    entity_ids = [eid.strip() for eid in ids.split(",") if eid.strip()]

    # Validate entity IDs are not empty after parsing
    if not entity_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "At least one entity ID is required",
                }
            },
        )

    # Validate batch size
    MAX_BATCH_SIZE = 25
    if len(entity_ids) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "BATCH_SIZE_EXCEEDED",
                    "message": f"Maximum batch size is {MAX_BATCH_SIZE}. Requested: {len(entity_ids)}",
                }
            },
        )

    try:
        # Fetch entities in batch
        result = await search_service.get_entities_batch(entity_ids)

        # Build response
        entity_dicts = [entity.model_dump(mode="json") for entity in result.entities]

        response_data = {
            "entities": entity_dicts,
            "total": len(entity_dicts),
            "requested": len(entity_ids),
        }

        # Include not_found field only if there are missing entities
        if result.not_found:
            response_data["not_found"] = result.not_found

        return EntityListResponse(**response_data)

    except Exception as e:
        logger.error(f"Error in batch entity lookup: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "BATCH_LOOKUP_ERROR",
                    "message": "An error occurred during batch entity lookup",
                }
            },
        )
