"""Search Service implementation for nes.

The Search Service provides read-optimized search capabilities:
- Entity text search with multilingual support (Nepali and English)
- Type and subtype filtering
- Attribute-based filtering with AND logic
- Tag-based filtering with AND logic
- Pagination support
- Relationship search with temporal filtering
- Version retrieval for entities and relationships

This service is separate from the Publication Service and focuses on
read operations only. It uses the database layer directly for efficient queries.
"""

import asyncio
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Union

from nes.core.models.entity import Entity
from nes.core.models.relationship import Relationship
from nes.core.models.version import Version
from nes.database.entity_database import EntityDatabase


@dataclass
class BatchLookupResult:
    """Result of batch entity lookup operation.

    Attributes:
        entities: List of entities that were found
        not_found: List of entity IDs that were not found
    """

    entities: List[Entity]
    not_found: List[str]


class SearchService:
    """Search Service for read-optimized entity and relationship queries.

    The Search Service provides a clean interface for searching and retrieving
    entities, relationships, and versions. It delegates to the database layer
    for actual query execution.

    Attributes:
        database: The database instance to query
    """

    def __init__(self, database: EntityDatabase):
        """Initialize the Search Service.

        Args:
            database: Database instance for querying
        """
        self.database = database

    async def search_entities(
        self,
        query: Optional[str] = None,
        entity_type: Optional[str] = None,
        sub_type: Optional[str] = None,
        attributes: Optional[Dict[str, Union[str, int, float, bool]]] = None,
        tags: Optional[List[str]] = None,
        entity_prefix: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Entity]:
        """Search entities with text query and optional filtering.

        Performs case-insensitive text search across entity name fields
        (both English and Nepali). Supports filtering by type, subtype,
        attributes, tags, and entity_prefix. Results are ranked by relevance
        when a query is provided.

        Args:
            query: Text query to search for in entity names (case-insensitive)
            entity_type: Filter by entity type (person, organization, location)
            sub_type: Filter by entity subtype (deprecated: use entity_prefix)
            attributes: Filter by entity attributes (AND logic)
            tags: Filter by tags (AND logic - entity must have ALL specified tags)
            entity_prefix: Filter by N-level prefix using startswith logic
                (e.g. 'organization/nepal_govt' matches 'organization/nepal_govt/moha')
            limit: Maximum number of entities to return (default: 100)
            offset: Number of entities to skip (default: 0)

        Returns:
            List of entities matching the search criteria, ranked by relevance
        """
        return await self.database.search_entities(
            query=query,
            entity_type=entity_type,
            sub_type=sub_type,
            attr_filters=attributes,
            tags=tags,
            entity_prefix=entity_prefix,
            limit=limit,
            offset=offset,
        )

    async def get_all_tags(self) -> List[str]:
        """Return all unique tag values across all entities."""
        return await self.database.get_all_tags()

    async def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get a specific entity by its ID.

        Args:
            entity_id: The unique entity identifier

        Returns:
            The entity if found, None otherwise

        Examples:
            >>> entity = await service.get_entity("entity:person/ram-chandra-poudel")
            >>> if entity:
            ...     print(f"Found: {entity.names.english}")
        """
        return await self.database.get_entity(entity_id)

    async def get_entities_batch(self, entity_ids: List[str]) -> BatchLookupResult:
        """Fetch multiple entities by their IDs in a single operation.

        This method fetches entities concurrently for improved performance.
        Entities that don't exist are tracked in the not_found list.

        Args:
            entity_ids: List of entity IDs to fetch

        Returns:
            BatchLookupResult with found entities and list of not found IDs

        Examples:
            >>> result = await service.get_entities_batch([
            ...     "entity:person/ram-chandra-poudel",
            ...     "entity:person/sher-bahadur-deuba",
            ...     "entity:person/nonexistent"
            ... ])
            >>> print(f"Found {len(result.entities)} entities")
            >>> print(f"Not found: {result.not_found}")
        """
        entities = []
        not_found = []

        # Fetch entities concurrently
        tasks = [self.database.get_entity(entity_id) for entity_id in entity_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for entity_id, result in zip(entity_ids, results):
            if isinstance(result, Exception):
                # Log error but don't fail the entire batch
                not_found.append(entity_id)
            elif result is None:
                not_found.append(entity_id)
            else:
                entities.append(result)

        return BatchLookupResult(entities=entities, not_found=not_found)

    async def search_relationships(
        self,
        relationship_type: Optional[str] = None,
        source_entity_id: Optional[str] = None,
        target_entity_id: Optional[str] = None,
        active_on: Optional[date] = None,
        currently_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Relationship]:
        """Search relationships with filtering and temporal queries.

        Supports filtering by relationship type, source/target entities,
        and temporal constraints (active on a specific date or currently active).

        Args:
            relationship_type: Filter by relationship type (e.g., "MEMBER_OF")
            source_entity_id: Filter by source entity ID
            target_entity_id: Filter by target entity ID
            active_on: Filter for relationships active on a specific date
            currently_active: Filter for relationships with no end date
            limit: Maximum number of relationships to return (default: 100)
            offset: Number of relationships to skip (default: 0)

        Returns:
            List of relationships matching the criteria

        Examples:
            >>> # Search by relationship type
            >>> results = await service.search_relationships(
            ...     relationship_type="MEMBER_OF"
            ... )

            >>> # Search by source entity
            >>> results = await service.search_relationships(
            ...     source_entity_id="entity:person/ram-chandra-poudel"
            ... )

            >>> # Search for currently active relationships
            >>> results = await service.search_relationships(
            ...     source_entity_id="entity:person/ram-chandra-poudel",
            ...     currently_active=True
            ... )

            >>> # Search for relationships active on a specific date
            >>> results = await service.search_relationships(
            ...     source_entity_id="entity:person/ram-chandra-poudel",
            ...     active_on=date(2021, 6, 1)
            ... )
        """
        # Route to appropriate database method based on filters
        if source_entity_id or target_entity_id:
            return await self._search_relationships_by_entity(
                source_entity_id=source_entity_id,
                target_entity_id=target_entity_id,
                relationship_type=relationship_type,
                active_on=active_on,
                currently_active=currently_active,
                limit=limit,
                offset=offset,
            )

        if relationship_type:
            return await self.database.list_relationships_by_type(
                relationship_type=relationship_type,
                limit=limit,
                offset=offset,
            )

        # No filters - list all relationships
        return await self.database.list_relationships(
            limit=limit,
            offset=offset,
        )

    async def _search_relationships_by_entity(
        self,
        source_entity_id: Optional[str],
        target_entity_id: Optional[str],
        relationship_type: Optional[str],
        active_on: Optional[date],
        currently_active: Optional[bool],
        limit: int,
        offset: int,
    ) -> List[Relationship]:
        """Helper method to search relationships by entity.

        This method handles the logic for searching relationships when
        source or target entity filters are specified.

        Args:
            source_entity_id: Filter by source entity ID
            target_entity_id: Filter by target entity ID
            relationship_type: Filter by relationship type
            active_on: Filter for relationships active on a specific date
            currently_active: Filter for relationships with no end date
            limit: Maximum number of relationships to return
            offset: Number of relationships to skip

        Returns:
            List of relationships matching the criteria
        """
        # Determine which entity to query by and the direction
        if source_entity_id and target_entity_id:
            # Both specified - query by source and filter by target
            entity_id = source_entity_id
            direction = "source"
        elif source_entity_id:
            entity_id = source_entity_id
            direction = "source"
        else:
            entity_id = target_entity_id
            direction = "target"

        # Query database
        results = await self.database.list_relationships_by_entity(
            entity_id=entity_id,
            direction=direction,
            relationship_type=relationship_type,
            active_on=active_on,
            currently_active=currently_active,
            limit=limit,
            offset=offset,
        )

        # If both source and target specified, apply additional filtering
        if source_entity_id and target_entity_id:
            results = self._filter_by_both_entities(
                results, source_entity_id, target_entity_id
            )

        return results

    def _filter_by_both_entities(
        self,
        relationships: List[Relationship],
        source_entity_id: str,
        target_entity_id: str,
    ) -> List[Relationship]:
        """Filter relationships by both source and target entity IDs.

        Args:
            relationships: List of relationships to filter
            source_entity_id: Required source entity ID
            target_entity_id: Required target entity ID

        Returns:
            Filtered list of relationships
        """
        return [
            r
            for r in relationships
            if r.source_entity_id == source_entity_id
            and r.target_entity_id == target_entity_id
        ]

    async def get_entity_versions(
        self,
        entity_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Version]:
        """Get version history for an entity.

        Returns all versions for the specified entity, sorted by version number
        in ascending order (oldest first).

        Args:
            entity_id: The entity ID to get versions for
            limit: Maximum number of versions to return (default: 100)
            offset: Number of versions to skip (default: 0)

        Returns:
            List of versions for the entity, sorted by version number

        Examples:
            >>> # Get all versions for an entity
            >>> versions = await service.get_entity_versions(
            ...     entity_id="entity:person/ram-chandra-poudel"
            ... )

            >>> # Get paginated versions
            >>> versions = await service.get_entity_versions(
            ...     entity_id="entity:person/ram-chandra-poudel",
            ...     limit=10,
            ...     offset=0
            ... )
        """
        return await self.database.list_versions_by_entity(
            entity_or_relationship_id=entity_id,
            limit=limit,
            offset=offset,
            order="asc",
        )

    async def get_relationship_versions(
        self,
        relationship_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Version]:
        """Get version history for a relationship.

        Returns all versions for the specified relationship, sorted by version
        number in ascending order (oldest first).

        Args:
            relationship_id: The relationship ID to get versions for
            limit: Maximum number of versions to return (default: 100)
            offset: Number of versions to skip (default: 0)

        Returns:
            List of versions for the relationship, sorted by version number

        Examples:
            >>> # Get all versions for a relationship
            >>> versions = await service.get_relationship_versions(
            ...     relationship_id="relationship:rel-123"
            ... )
        """
        return await self.database.list_versions_by_entity(
            entity_or_relationship_id=relationship_id,
            limit=limit,
            offset=offset,
            order="asc",
        )
