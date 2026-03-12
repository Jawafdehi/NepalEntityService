"""File-based implementation of EntityDatabase for nes.

This module provides a file-based storage implementation using JSON files
organized in a directory structure. The default database path is 'nes-db/v2'.

Features:
- JSON-based storage with human-readable format
- Batch operations for improved performance
- Comprehensive error handling

Performance Characteristics:
- Concurrent read operations via asyncio
"""

import asyncio
import json
import logging
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from nes.core.models.entity import Entity, EntitySubType, EntityType
from nes.core.models.entity_type_map import ENTITY_TYPE_MAP
from nes.core.models.location import Location
from nes.core.models.organization import (
    GovernmentBody,
    Hospital,
    Organization,
    PoliticalParty,
)
from nes.core.models.person import Person
from nes.core.models.project import Project
from nes.core.models.relationship import Relationship
from nes.core.models.version import Author, Version

from .entity_database import EntityDatabase

# Configure logger for this module
logger = logging.getLogger(__name__)


class FileDatabase(EntityDatabase):
    """File-based implementation of EntityDatabase.

    Stores entities, relationships, versions, and authors as JSON files
    in a directory structure organized by type and subtype.

    Default database path: nes-db/v2

    Directory structure:
        nes-db/v2/
            entity/
                person/
                    {slug}.json
                organization/
                    political_party/
                        {slug}.json
                    government_body/
                        {slug}.json
                location/
                    province/
                        {slug}.json
                    district/
                        {slug}.json
            relationship/
                {relationship-id}.json
            version/
                entity/
                    {entity-id}/
                        {version-number}.json
                relationship/
                    {relationship-id}/
                        {version-number}.json
            author/
                {slug}.json
    """

    def __init__(self, base_path: str = "nes-db/v2"):
        """Initialize FileDatabase with the specified base path.

        Args:
            base_path: Root directory for database storage (default: nes-db/v2)

        Raises:
            OSError: If base_path cannot be created
        """
        try:
            self.base_path = Path(base_path)
            self.base_path.mkdir(exist_ok=True, parents=True)
        except OSError as e:
            logger.error(f"Failed to create database directory at {base_path}: {e}")
            raise

        logger.info(f"FileDatabase initialized at {base_path}")

    async def batch_get_entities(self, entity_ids: List[str]) -> List[Optional[Entity]]:
        """Batch retrieve multiple entities by their IDs.

        This method is optimized for retrieving multiple entities at once,
        reducing I/O overhead compared to individual get_entity calls.

        Args:
            entity_ids: List of entity IDs to retrieve

        Returns:
            List of entities in the same order as entity_ids.
            None is returned for entities that don't exist.
        """
        if not entity_ids:
            return []

        async def load_entity(entity_id: str) -> Optional[Entity]:
            """Load a single entity from disk."""
            file_path = self._id_to_path(entity_id)

            if not file_path.exists():
                return None

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                return self._entity_from_dict(data)
            except (json.JSONDecodeError, ValueError, KeyError):
                return None

        # Load all entities concurrently
        return await asyncio.gather(
            *[load_entity(entity_id) for entity_id in entity_ids]
        )

    # ========================================================================
    # File System Helper Methods
    # ========================================================================

    def _id_to_path(self, obj_id: str) -> Path:
        """Convert an object ID to a file path.

        Converts IDs like 'entity:person/ram-chandra-poudel' to file paths
        like 'nes-db/v2/entity/person/ram-chandra-poudel.json'.

        Args:
            obj_id: Object identifier following the pattern 'type:subtype/slug'

        Returns:
            Path to the JSON file for this object

        Examples:
            >>> db._id_to_path('entity:person/ram-chandra-poudel')
            Path('nes-db/v2/entity/person/ram-chandra-poudel.json')
            >>> db._id_to_path('relationship:rel-123')
            Path('nes-db/v2/relationship/rel-123.json')
        """
        # Replace colons with slashes and add .json extension
        file_path = obj_id.replace(":", "/") + ".json"
        return self.base_path / file_path

    def _ensure_dir(self, file_path: Path):
        """Ensure the directory for a file path exists.

        Creates all parent directories if they don't exist. This is called
        before writing any file to ensure the directory structure is in place.

        Args:
            file_path: Path to a file

        Raises:
            OSError: If directory creation fails
        """
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create directory for {file_path}: {e}")
            raise

    # ========================================================================
    # Entity CRUD Operations
    # ========================================================================

    async def put_entity(self, entity: Entity) -> Entity:
        """Store an entity in the database.

        Writes the entity to a JSON file.
        Computed fields are automatically removed before serialization.

        Args:
            entity: The entity to store

        Returns:
            The stored entity

        Raises:
            OSError: If file write fails
            ValueError: If entity serialization fails
        """
        try:
            file_path = self._id_to_path(entity.id)
            self._ensure_dir(file_path)

            # Serialize entity and remove computed fields
            data = self._serialize_entity(entity)

            # Write to file
            self._write_json_file(file_path, data)

            logger.debug(f"Stored entity: {entity.id}")
            return entity

        except Exception as e:
            logger.error(f"Failed to store entity {entity.id}: {e}")
            raise

    def _serialize_entity(self, entity: Entity) -> dict:
        """Serialize an entity to a dictionary, removing computed fields.

        Args:
            entity: Entity to serialize

        Returns:
            Dictionary representation suitable for JSON storage
        """
        data = entity.model_dump(mode="json")

        # Remove computed fields from entity
        data.pop("id", None)
        data.pop("location_type", None)  # Location computed field
        data.pop("administrative_level", None)  # Location computed field

        # Remove computed fields from nested version_summary
        if "version_summary" in data and isinstance(data["version_summary"], dict):
            data["version_summary"].pop("id", None)

        return data

    def _write_json_file(self, file_path: Path, data: dict):
        """Write data to a JSON file with consistent formatting.

        Args:
            file_path: Path to write to
            data: Data to serialize

        Raises:
            OSError: If file write fails
            ValueError: If JSON serialization fails
        """
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                default=str,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )

    async def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Retrieve an entity by its ID.

        Args:
            entity_id: The unique identifier of the entity

        Returns:
            The entity if found, None otherwise

        Raises:
            ValueError: If entity data is invalid
            json.JSONDecodeError: If JSON file is malformed
        """
        try:
            return await self._load_entity_from_disk(entity_id)
        except Exception as e:
            logger.error(f"Failed to get entity {entity_id}: {e}")
            raise

    async def _load_entity_from_disk(self, entity_id: str) -> Optional[Entity]:
        """Load an entity from disk.

        Args:
            entity_id: Entity ID to load

        Returns:
            Entity if found, None otherwise

        Raises:
            ValueError: If entity data is invalid
            json.JSONDecodeError: If JSON file is malformed
        """
        file_path = self._id_to_path(entity_id)

        if not file_path.exists():
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            return self._entity_from_dict(data)

        except json.JSONDecodeError as e:
            logger.error(f"Malformed JSON in {file_path}: {e}")
            raise
        except (ValueError, KeyError) as e:
            logger.error(f"Invalid entity data in {file_path}: {e}")
            raise

    async def delete_entity(self, entity_id: str) -> bool:
        """Delete an entity from the database.

        Args:
            entity_id: The unique identifier of the entity to delete

        Returns:
            True if the entity was deleted, False if it didn't exist

        Raises:
            OSError: If file deletion fails
        """
        try:
            file_path = self._id_to_path(entity_id)

            if not file_path.exists():
                return False

            file_path.unlink()

            logger.debug(f"Deleted entity: {entity_id}")
            return True

        except OSError as e:
            logger.error(f"Failed to delete entity {entity_id}: {e}")
            raise

    async def list_entities(
        self,
        limit: int = 100,
        offset: int = 0,
        entity_type: Optional[str] = None,
        sub_type: Optional[str] = None,
        attr_filters: Optional[Dict[str, Union[str, int, float, bool]]] = None,
    ) -> List[Entity]:
        """List entities with optional filtering and pagination.

        Args:
            limit: Maximum number of entities to return
            offset: Number of entities to skip
            entity_type: Filter by entity type (person, organization, location)
            sub_type: Filter by entity subtype
            attr_filters: Filter by entity attributes (AND logic)

        Returns:
            List of entities matching the criteria

        Note:
            Results are not sorted. For sorted results, use search_entities.
        """
        # Build search path based on type/subtype
        search_path = self._build_entity_search_path(entity_type, sub_type)

        # If search path doesn't exist, return empty list
        if not search_path.exists():
            logger.debug(f"Search path does not exist: {search_path}")
            return []

        entities = []

        # Recursively find all JSON files
        for file_path in search_path.rglob("*.json"):
            # Skip if we already have enough entities
            if len(entities) >= limit + offset:
                break

            try:
                entity = self._load_and_filter_entity(file_path, attr_filters)
                if entity:
                    entities.append(entity)

            except (json.JSONDecodeError, ValueError, KeyError) as e:
                # Skip invalid files but log the error
                logger.warning(f"Skipping invalid entity file {file_path}: {e}")
                continue

        # Apply pagination
        return entities[offset : offset + limit]

    def _build_entity_search_path(
        self, entity_type: Optional[str] = None, sub_type: Optional[str] = None
    ) -> Path:
        """Build the search path for entity queries.

        Args:
            entity_type: Optional entity type filter
            sub_type: Optional entity subtype filter

        Returns:
            Path to search for entities
        """
        if sub_type and entity_type:
            return self.base_path / "entity" / entity_type / sub_type
        elif entity_type:
            return self.base_path / "entity" / entity_type
        else:
            return self.base_path / "entity"

    def _load_and_filter_entity(
        self,
        file_path: Path,
        attr_filters: Optional[Dict[str, Union[str, int, float, bool]]] = None,
    ) -> Optional[Entity]:
        """Load an entity from a file and apply attribute filters.

        Args:
            file_path: Path to the entity JSON file
            attr_filters: Optional attribute filters to apply

        Returns:
            Entity if it passes filters, None otherwise

        Raises:
            json.JSONDecodeError: If JSON is malformed
            ValueError: If entity data is invalid
        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Check if this is an entity (has 'type' field)
        if "type" not in data:
            return None

        # Apply attribute filters if provided
        if attr_filters and not self._matches_attribute_filters(data, attr_filters):
            return None

        # Parse entity
        return self._entity_from_dict(data)

    def _matches_attribute_filters(
        self, data: dict, attr_filters: Dict[str, Union[str, int, float, bool]]
    ) -> bool:
        """Check if entity data matches attribute filters.

        Args:
            data: Entity data dictionary
            attr_filters: Attribute filters to check (AND logic)

        Returns:
            True if all filters match, False otherwise
        """
        attributes = data.get("attributes") or {}
        # Check if all filter criteria match (AND logic)
        return all(attributes.get(k) == v for k, v in attr_filters.items())

    def _entity_matches_tags(self, entity: Entity, tags: List[str]) -> bool:
        """Check if entity has all specified tags (AND logic).

        Args:
            entity: Entity to check
            tags: List of tags that entity must have

        Returns:
            True if entity has ALL specified tags, False otherwise
        """
        entity_tags = entity.tags or []
        # Check if all required tags are present in entity's tags
        return all(tag in entity_tags for tag in tags)

    async def search_entities(
        self,
        query: Optional[str] = None,
        entity_type: Optional[str] = None,
        sub_type: Optional[str] = None,
        attr_filters: Optional[Dict[str, Union[str, int, float, bool]]] = None,
        tags: Optional[List[str]] = None,
        entity_prefix: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Entity]:
        """Search entities with text query and optional filtering.

        Performs case-insensitive text search across entity name fields
        (both English and Nepali). Supports filtering by type, subtype,
        attributes, tags, and entity_prefix. Results are ranked by relevance.

        Args:
            query: Text query to search for in entity names (case-insensitive)
            entity_type: Filter by entity type (person, organization, location)
            sub_type: Filter by entity subtype
            attr_filters: Filter by entity attributes (AND logic)
            tags: Filter by tags (AND logic - entity must have ALL specified tags)
            entity_prefix: Filter by N-level prefix using startswith logic
                (e.g. 'organization/nepal_govt' matches 'organization/nepal_govt/moha')
            limit: Maximum number of entities to return
            offset: Number of entities to skip

        Returns:
            List of entities matching the search criteria, ranked by relevance
        """
        # Derive entity_type and sub_type from entity_prefix when not explicitly given
        effective_type = entity_type
        effective_sub_type = sub_type
        if entity_prefix:
            segments = entity_prefix.split("/")
            if not entity_type:
                effective_type = segments[0]
            if not sub_type and len(segments) >= 2:
                effective_sub_type = segments[1]

        # Build search path based on type/subtype
        search_path = self._build_entity_search_path(effective_type, effective_sub_type)

        # If search path doesn't exist, return empty list
        if not search_path.exists():
            logger.debug(f"Search path does not exist: {search_path}")
            return []

        # Normalize query for case-insensitive search
        normalized_query = query.lower() if query else None

        # Collect entities with relevance scores
        entities_with_scores = []

        # Recursively find all JSON files
        for file_path in search_path.rglob("*.json"):
            try:
                entity = self._load_and_filter_entity(file_path, attr_filters)
                if not entity:
                    continue

                # Apply entity_prefix filter (startswith logic)
                if entity_prefix is not None:
                    ep = entity.entity_prefix
                    if ep is None:
                        # Fallback for legacy entities that predate entity_prefix
                        type_val = (
                            entity.type.value
                            if hasattr(entity.type, "value")
                            else entity.type
                        )
                        sub_val = (
                            entity.sub_type.value
                            if (entity.sub_type and hasattr(entity.sub_type, "value"))
                            else entity.sub_type
                        )
                        ep = type_val if sub_val is None else f"{type_val}/{sub_val}"
                    if not (ep == entity_prefix or ep.startswith(entity_prefix + "/")):
                        continue

                # Apply tag filtering (AND logic - entity must have ALL specified tags)
                if tags and len(tags) > 0:
                    if not self._entity_matches_tags(entity, tags):
                        continue

                # If no query, include all entities (filtered by type/attributes/tags)
                if not normalized_query:
                    entities_with_scores.append((entity, 0))
                    continue

                # Calculate relevance score based on name matches
                score = self._calculate_relevance_score(entity, normalized_query)

                # Only include entities with positive scores (matches found)
                if score > 0:
                    entities_with_scores.append((entity, score))

            except (json.JSONDecodeError, ValueError, KeyError) as e:
                # Skip invalid files but log the error
                logger.warning(f"Skipping invalid entity file {file_path}: {e}")
                continue

        # Sort by relevance score (higher is better)
        entities_with_scores.sort(key=lambda x: x[1], reverse=True)

        # Extract entities and apply pagination
        entities = [entity for entity, score in entities_with_scores]
        return entities[offset : offset + limit]

    def _calculate_relevance_score(self, entity: Entity, normalized_query: str) -> int:
        """Calculate relevance score for an entity based on query match.

        Scoring logic:
        - Exact full name match: 100 points
        - Full name contains query: 50 points
        - First/last name exact match: 75 points
        - First/last name contains query: 25 points
        - Primary name match: bonus 20 points
        - Alias/alternate name match: bonus 10 points

        Args:
            entity: Entity to score
            normalized_query: Lowercase query string

        Returns:
            Relevance score (higher is better, 0 means no match)
        """
        score = 0

        for name in entity.names:
            # Determine name kind bonus
            name_kind_bonus = 20 if name.kind.value == "PRIMARY" else 10

            # Check English names
            if name.en:
                # Check full name
                if name.en.full:
                    full_name_lower = name.en.full.lower()
                    if full_name_lower == normalized_query:
                        score += 100 + name_kind_bonus
                    elif normalized_query in full_name_lower:
                        score += 50 + name_kind_bonus

                # Check first name
                if name.en.given:
                    first_name_lower = name.en.given.lower()
                    if first_name_lower == normalized_query:
                        score += 75 + name_kind_bonus
                    elif normalized_query in first_name_lower:
                        score += 25 + name_kind_bonus

                # Check last name
                if name.en.family:
                    last_name_lower = name.en.family.lower()
                    if last_name_lower == normalized_query:
                        score += 75 + name_kind_bonus
                    elif normalized_query in last_name_lower:
                        score += 25 + name_kind_bonus

                # Check middle name
                if name.en.middle:
                    middle_name_lower = name.en.middle.lower()
                    if middle_name_lower == normalized_query:
                        score += 75 + name_kind_bonus
                    elif normalized_query in middle_name_lower:
                        score += 25 + name_kind_bonus

            # Check Nepali names (Devanagari)
            if name.ne:
                # Check full name
                if name.ne.full:
                    full_name_lower = name.ne.full.lower()
                    if full_name_lower == normalized_query:
                        score += 100 + name_kind_bonus
                    elif normalized_query in full_name_lower:
                        score += 50 + name_kind_bonus

                # Check first name
                if name.ne.given:
                    first_name_lower = name.ne.given.lower()
                    if first_name_lower == normalized_query:
                        score += 75 + name_kind_bonus
                    elif normalized_query in first_name_lower:
                        score += 25 + name_kind_bonus

                # Check last name
                if name.ne.family:
                    last_name_lower = name.ne.family.lower()
                    if last_name_lower == normalized_query:
                        score += 75 + name_kind_bonus
                    elif normalized_query in last_name_lower:
                        score += 25 + name_kind_bonus

                # Check middle name
                if name.ne.middle:
                    middle_name_lower = name.ne.middle.lower()
                    if middle_name_lower == normalized_query:
                        score += 75 + name_kind_bonus
                    elif normalized_query in middle_name_lower:
                        score += 25 + name_kind_bonus

        return score

    def _entity_from_dict(self, data: dict) -> Entity:
        """Convert a dictionary to an Entity instance.

        Args:
            data: Dictionary representation of an entity

        Returns:
            Entity instance of the appropriate subclass

        Raises:
            ValueError: If entity type is invalid
            KeyError: If entity type/subtype combination is not found
        """
        if "type" not in data:
            raise ValueError("Entity must have a 'type' field")

        entity_type = EntityType(data["type"])
        entity_subtype = (
            EntitySubType(data["sub_type"]) if data.get("sub_type") else None
        )

        # Determine the correct entity class based on type and subtype
        if entity_type == EntityType.PERSON:
            return Person.model_validate(data)
        elif entity_type == EntityType.ORGANIZATION:
            if entity_subtype == EntitySubType.POLITICAL_PARTY:
                return PoliticalParty.model_validate(data)
            elif entity_subtype == EntitySubType.GOVERNMENT_BODY:
                return GovernmentBody.model_validate(data)
            elif entity_subtype == EntitySubType.HOSPITAL:
                return Hospital.model_validate(data)
            else:
                return Organization.model_validate(data)
        elif entity_type == EntityType.LOCATION:
            return Location.model_validate(data)
        elif entity_type == EntityType.PROJECT:
            return Project.model_validate(data)
        else:
            raise ValueError(f"Unknown entity type: {entity_type}")

    # ========================================================================
    # Relationship CRUD Operations
    # ========================================================================

    async def put_relationship(self, relationship: Relationship) -> Relationship:
        """Store a relationship in the database.

        Args:
            relationship: The relationship to store

        Returns:
            The stored relationship

        Raises:
            OSError: If file write fails
            ValueError: If relationship serialization fails
        """
        try:
            file_path = self._id_to_path(relationship.id)
            self._ensure_dir(file_path)

            # Serialize relationship and remove computed fields
            data = self._serialize_relationship(relationship)

            # Write to file
            self._write_json_file(file_path, data)

            logger.debug(f"Stored relationship: {relationship.id}")
            return relationship

        except Exception as e:
            logger.error(f"Failed to store relationship {relationship.id}: {e}")
            raise

    def _serialize_relationship(self, relationship: Relationship) -> dict:
        """Serialize a relationship to a dictionary, removing computed fields.

        Args:
            relationship: Relationship to serialize

        Returns:
            Dictionary representation suitable for JSON storage
        """
        data = relationship.model_dump(mode="json")
        data.pop("id", None)
        if "version_summary" in data and isinstance(data["version_summary"], dict):
            data["version_summary"].pop("id", None)
        return data

    async def get_relationship(self, relationship_id: str) -> Optional[Relationship]:
        """Retrieve a relationship by its ID.

        Args:
            relationship_id: The unique identifier of the relationship

        Returns:
            The relationship if found, None otherwise

        Raises:
            ValueError: If relationship data is invalid
            json.JSONDecodeError: If JSON file is malformed
        """
        try:
            return await self._load_relationship_from_disk(relationship_id)
        except Exception as e:
            logger.error(f"Failed to get relationship {relationship_id}: {e}")
            raise

    async def _load_relationship_from_disk(
        self, relationship_id: str
    ) -> Optional[Relationship]:
        """Load a relationship from disk.

        Args:
            relationship_id: Relationship ID to load

        Returns:
            Relationship if found, None otherwise

        Raises:
            ValueError: If relationship data is invalid
            json.JSONDecodeError: If JSON file is malformed
        """
        file_path = self._id_to_path(relationship_id)

        if not file_path.exists():
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            return Relationship.model_validate(data)

        except json.JSONDecodeError as e:
            logger.error(f"Malformed JSON in {file_path}: {e}")
            raise
        except (ValueError, KeyError) as e:
            logger.error(f"Invalid relationship data in {file_path}: {e}")
            raise

    async def delete_relationship(self, relationship_id: str) -> bool:
        """Delete a relationship from the database.

        Args:
            relationship_id: The unique identifier of the relationship to delete

        Returns:
            True if the relationship was deleted, False if it didn't exist

        Raises:
            OSError: If file deletion fails
        """
        try:
            file_path = self._id_to_path(relationship_id)

            if not file_path.exists():
                return False

            file_path.unlink()

            logger.debug(f"Deleted relationship: {relationship_id}")
            return True

        except OSError as e:
            logger.error(f"Failed to delete relationship {relationship_id}: {e}")
            raise

    async def list_relationships(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Relationship]:
        """List relationships with pagination.

        Args:
            limit: Maximum number of relationships to return
            offset: Number of relationships to skip

        Returns:
            List of relationships
        """
        search_path = self.base_path / "relationship"

        if not search_path.exists():
            logger.debug(f"Relationship path does not exist: {search_path}")
            return []

        relationships = []

        # Recursively find all JSON files
        for file_path in search_path.rglob("*.json"):
            if len(relationships) >= limit + offset:
                break

            try:
                relationship = self._load_relationship_from_file(file_path)
                if relationship:
                    relationships.append(relationship)

            except (json.JSONDecodeError, ValueError, KeyError) as e:
                # Skip invalid files but log the error
                logger.warning(f"Skipping invalid relationship file {file_path}: {e}")
                continue

        # Apply pagination
        return relationships[offset : offset + limit]

    def _load_relationship_from_file(self, file_path: Path) -> Optional[Relationship]:
        """Load a relationship from a file.

        Args:
            file_path: Path to the relationship JSON file

        Returns:
            Relationship if valid, None otherwise

        Raises:
            json.JSONDecodeError: If JSON is malformed
            ValueError: If relationship data is invalid
        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Check if this is a relationship (has source_entity_id)
        if "source_entity_id" not in data:
            return None

        return Relationship.model_validate(data)

    async def list_relationships_by_entity(
        self,
        entity_id: str,
        direction: str = "both",
        relationship_type: Optional[str] = None,
        active_on: Optional["date"] = None,
        start_date_from: Optional["date"] = None,
        start_date_to: Optional["date"] = None,
        currently_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Relationship]:
        """List relationships by entity (source or target).

        Args:
            entity_id: The entity ID to search for
            direction: Direction filter - "source", "target", or "both" (default)
            relationship_type: Optional filter by relationship type
            active_on: Optional filter for relationships active on a specific date
            start_date_from: Optional filter for relationships starting from this date
            start_date_to: Optional filter for relationships starting before this date
            currently_active: Optional filter for relationships with no end date
            limit: Maximum number of relationships to return
            offset: Number of relationships to skip

        Returns:
            List of relationships matching the criteria
        """
        from datetime import date

        search_path = self.base_path / "relationship"

        if not search_path.exists():
            return []

        relationships = []

        # Recursively find all JSON files
        for file_path in search_path.rglob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Check if this is a relationship (has source_entity_id)
                if "source_entity_id" not in data:
                    continue

                # Apply direction filter
                if direction == "source" and data.get("source_entity_id") != entity_id:
                    continue
                elif (
                    direction == "target" and data.get("target_entity_id") != entity_id
                ):
                    continue
                elif direction == "both":
                    if (
                        data.get("source_entity_id") != entity_id
                        and data.get("target_entity_id") != entity_id
                    ):
                        continue

                # Apply relationship type filter
                if relationship_type and data.get("type") != relationship_type:
                    continue

                # Parse relationship for temporal filtering
                relationship = Relationship.model_validate(data)

                # Apply temporal filters
                if active_on is not None:
                    # Check if relationship was active on the specified date
                    if relationship.start_date and relationship.start_date > active_on:
                        continue
                    if relationship.end_date and relationship.end_date < active_on:
                        continue

                if start_date_from is not None:
                    # Filter relationships starting from this date
                    if (
                        not relationship.start_date
                        or relationship.start_date < start_date_from
                    ):
                        continue

                if start_date_to is not None:
                    # Filter relationships starting before this date
                    if (
                        not relationship.start_date
                        or relationship.start_date > start_date_to
                    ):
                        continue

                if currently_active is not None:
                    # Filter for currently active relationships (no end date)
                    if currently_active and relationship.end_date is not None:
                        continue
                    if not currently_active and relationship.end_date is None:
                        continue

                relationships.append(relationship)

            except (json.JSONDecodeError, ValueError, KeyError):
                # Skip invalid files
                continue

        # Apply pagination
        return relationships[offset : offset + limit]

    async def list_relationships_by_type(
        self,
        relationship_type: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Relationship]:
        """List relationships by relationship type.

        Args:
            relationship_type: The relationship type to filter by
            limit: Maximum number of relationships to return
            offset: Number of relationships to skip

        Returns:
            List of relationships matching the type
        """
        search_path = self.base_path / "relationship"

        if not search_path.exists():
            return []

        relationships = []

        # Recursively find all JSON files
        for file_path in search_path.rglob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Check if this is a relationship (has source_entity_id)
                if "source_entity_id" not in data:
                    continue

                # Apply type filter
                if data.get("type") != relationship_type:
                    continue

                relationship = Relationship.model_validate(data)
                relationships.append(relationship)

            except (json.JSONDecodeError, ValueError, KeyError):
                # Skip invalid files
                continue

        # Apply pagination
        return relationships[offset : offset + limit]

    async def put_version(self, version: Version) -> Version:
        """Store a version in the database."""
        file_path = self._id_to_path(version.id)
        self._ensure_dir(file_path)

        # Serialize version and remove computed fields
        data = version.model_dump(mode="json")
        data.pop("id", None)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                default=str,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )

        return version

    async def get_version(self, version_id: str) -> Optional[Version]:
        """Retrieve a version by its ID."""
        file_path = self._id_to_path(version_id)

        if not file_path.exists():
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return Version.model_validate(data)

    async def delete_version(self, version_id: str) -> bool:
        """Delete a version from the database."""
        file_path = self._id_to_path(version_id)

        if file_path.exists():
            file_path.unlink()
            return True

        return False

    async def list_versions(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Version]:
        """List versions with pagination."""
        search_path = self.base_path / "version"

        if not search_path.exists():
            return []

        versions = []

        # Recursively find all JSON files
        for file_path in search_path.rglob("*.json"):
            if len(versions) >= limit + offset:
                break

            try:
                with open(file_path, "r") as f:
                    data = json.load(f)

                # Check if this is a version (has version_number)
                if "version_number" not in data:
                    continue

                version = Version.model_validate(data)
                versions.append(version)

            except (json.JSONDecodeError, ValueError, KeyError):
                # Skip invalid files
                continue

        # Apply pagination
        return versions[offset : offset + limit]

    async def list_versions_by_entity(
        self,
        entity_or_relationship_id: str,
        limit: int = 100,
        offset: int = 0,
        author_slug: Optional[str] = None,
        created_after: Optional["datetime"] = None,
        created_before: Optional["datetime"] = None,
        min_version: Optional[int] = None,
        max_version: Optional[int] = None,
        order: str = "asc",
    ) -> List[Version]:
        """List versions for a specific entity or relationship with filtering.

        Args:
            entity_or_relationship_id: The entity or relationship ID to filter by
            limit: Maximum number of versions to return
            offset: Number of versions to skip
            author_slug: Optional filter by author slug
            created_after: Optional filter for versions created after this datetime
            created_before: Optional filter for versions created before this datetime
            min_version: Optional filter for minimum version number (inclusive)
            max_version: Optional filter for maximum version number (inclusive)
            order: Sort order - "asc" (default) or "desc"

        Returns:
            List of versions matching the criteria, sorted by version number
        """
        from datetime import datetime

        # Determine the search path based on entity or relationship ID
        # Version files are stored in: version/entity/{entity-id}/{version-number}.json
        # or: version/relationship/{relationship-id}/{version-number}.json
        # Use the _id_to_path method to get the correct path structure
        # This will handle the colon-to-slash conversion properly
        version_base_path = self._id_to_path(f"version:{entity_or_relationship_id}")

        # Remove the .json extension since we're looking for a directory
        search_path = version_base_path.parent / version_base_path.stem

        # If search path doesn't exist, return empty list
        if not search_path.exists():
            return []

        versions = []

        # Find all JSON files in the entity/relationship version directory
        for file_path in search_path.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)

                # Check if this is a version (has version_number)
                if "version_number" not in data:
                    continue

                # Parse version
                version = Version.model_validate(data)

                # Apply author filter
                if author_slug and version.author.slug != author_slug:
                    continue

                # Apply date range filters
                # created_after: inclusive (>=)
                if created_after and version.created_at < created_after:
                    continue
                # created_before: exclusive (<)
                if created_before and version.created_at >= created_before:
                    continue

                # Apply version number range filters
                if min_version is not None and version.version_number < min_version:
                    continue
                if max_version is not None and version.version_number > max_version:
                    continue

                versions.append(version)

            except (json.JSONDecodeError, ValueError, KeyError):
                # Skip invalid files
                continue

        # Sort by version number
        reverse_order = order.lower() == "desc"
        versions.sort(key=lambda v: v.version_number, reverse=reverse_order)

        # Apply pagination
        return versions[offset : offset + limit]

    async def put_author(self, author: Author) -> Author:
        """Store an author in the database."""
        file_path = self._id_to_path(author.id)
        self._ensure_dir(file_path)

        # Serialize author and remove computed fields
        data = author.model_dump(mode="json")
        data.pop("id", None)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                default=str,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )

        return author

    async def get_author(self, author_id: str) -> Optional[Author]:
        """Retrieve an author by its ID."""
        file_path = self._id_to_path(author_id)

        if not file_path.exists():
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return Author.model_validate(data)

    async def delete_author(self, author_id: str) -> bool:
        """Delete an author from the database."""
        file_path = self._id_to_path(author_id)

        if file_path.exists():
            file_path.unlink()
            return True

        return False

    async def list_authors(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Author]:
        """List authors with pagination."""
        search_path = self.base_path / "author"

        if not search_path.exists():
            return []

        authors = []

        # Recursively find all JSON files
        for file_path in search_path.rglob("*.json"):
            if len(authors) >= limit + offset:
                break

            try:
                with open(file_path, "r") as f:
                    data = json.load(f)

                # Check if this is an author (has slug)
                if "slug" not in data:
                    continue

                author = Author.model_validate(data)
                authors.append(author)

            except (json.JSONDecodeError, ValueError, KeyError):
                # Skip invalid files
                continue

        # Apply pagination
        return authors[offset : offset + limit]
