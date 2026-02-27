"""Publication Service for managing entities and relationships with automatic versioning.

The Publication Service is the central orchestration layer that manages:
- Entity lifecycle (creation, updates, retrieval, deletion)
- Relationship management with bidirectional consistency
- Automatic versioning for all changes
- Author attribution tracking
- Coordinated operations across entities and relationships
- Business rule enforcement
"""

import logging
from datetime import UTC, date, datetime
from typing import Any, Dict, List, Optional

from nes.core.models.base import Name, NameKind
from nes.core.models.entity import Entity, EntitySubType, EntityType
from nes.core.models.location import Location
from nes.core.models.organization import (
    GovernmentBody,
    Hospital,
    Organization,
    PoliticalParty,
)
from nes.core.models.person import Person
from nes.core.models.project import Project
from nes.core.models.relationship import Relationship, RelationshipType
from nes.core.models.version import Author, Version, VersionSummary, VersionType
from nes.database.entity_database import EntityDatabase

logger = logging.getLogger(__name__)


class PublicationService:
    """Service for publishing and managing entities and relationships.

    This service provides high-level operations for entity and relationship
    management with automatic versioning, validation, and business rule enforcement.
    """

    def __init__(self, database: EntityDatabase):
        """Initialize the Publication Service.

        Args:
            database: Database instance for storage operations
        """
        self.database = database
        logger.info("PublicationService initialized")

    async def create_entity(
        self,
        entity_type: Optional[EntityType] = None,
        entity_data: Optional[Dict[str, Any]] = None,
        author_id: Optional[str] = None,
        change_description: str = "Initial entity creation",
        entity_subtype: Optional[EntitySubType] = None,
        entity_prefix: Optional[str] = None,
    ) -> Entity:
        """Create a new entity with automatic versioning.

        Supports two calling conventions:
        1. New prefix style: create_entity(entity_prefix="organization/nepal_govt/moha", ...)
        2. Legacy style: create_entity(entity_type=EntityType.PERSON, ...)

        When entity_prefix is provided it takes precedence over entity_type/entity_subtype
        for ID generation. entity_type/entity_subtype are deprecated in favour of entity_prefix.

        Args:
            entity_type: Deprecated. Type of the entity (optional if entity_prefix or 'type' in entity_data)
            entity_data: Dictionary containing entity data
            author_id: ID of the author creating the entity
            change_description: Description of this change
            entity_subtype: Deprecated. Subtype of the entity (use entity_prefix instead)
            entity_prefix: N-level classification prefix (e.g. 'organization/nepal_govt/moha').
                When set, takes precedence over entity_type/entity_subtype.

        Returns:
            Created entity with version 1

        Raises:
            ValueError: If entity data is invalid or required fields are missing
        """
        # Validate required arguments
        if entity_data is None:
            raise ValueError("entity_data is required")
        if author_id is None:
            raise ValueError("author_id is required")

        from nes.core.identifiers import build_entity_id, build_entity_id_from_prefix

        # entity_prefix path: derive entity_type from first prefix segment
        if entity_prefix is not None:
            first_segment = entity_prefix.split("/")[0]
            entity_type = EntityType(first_segment)
            entity_data["entity_prefix"] = entity_prefix
            slug = entity_data.get("slug")
            if not slug:
                raise ValueError("Entity must have a 'slug' field")
            entity_id = build_entity_id_from_prefix(entity_prefix, slug)
        else:
            # Legacy path: resolve entity_type and entity_subtype
            if entity_type is None:
                if "type" not in entity_data:
                    raise ValueError(
                        "Entity must have a 'type' field, entity_type parameter, or entity_prefix"
                    )
                entity_type = EntityType(entity_data["type"])

            if entity_subtype is None and entity_data.get("sub_type"):
                entity_subtype = EntitySubType(entity_data["sub_type"])

            slug = entity_data.get("slug")
            if not slug:
                raise ValueError("Entity must have a 'slug' field")

            entity_id = build_entity_id(
                entity_type.value, entity_subtype.value if entity_subtype else None, slug
            )

        # Validate required fields
        if "slug" not in entity_data:
            raise ValueError("Entity must have a 'slug' field")
        if "names" not in entity_data or not entity_data["names"]:
            raise ValueError("Entity must have at least one name")

        # Validate that at least one name has kind='PRIMARY'
        has_primary = any(
            name.get("kind") == "PRIMARY" or name.get("kind") == NameKind.PRIMARY
            for name in entity_data["names"]
        )
        if not has_primary:
            raise ValueError("Entity must have at least one name with kind='PRIMARY'")

        # Get or create author
        author = await self._get_or_create_author(author_id)

        # Check if entity already exists
        existing = await self.database.get_entity(entity_id)
        if existing:
            raise ValueError(
                f"Entity with slug '{slug}' and type '{entity_type}' already exists"
            )

        # Create version summary
        version_summary = VersionSummary(
            entity_or_relationship_id=entity_id,
            type=VersionType.ENTITY,
            version_number=1,
            author=author,
            change_description=change_description,
            created_at=datetime.now(UTC),
        )

        # Add type, subtype, version summary and created_at to entity data
        entity_data["type"] = entity_type.value
        if entity_subtype:
            entity_data["sub_type"] = entity_subtype.value
        entity_data["version_summary"] = version_summary
        entity_data["created_at"] = datetime.now(UTC)

        # Create entity instance based on type
        entity = self._create_entity_instance(entity_data)

        # Store entity in database
        await self.database.put_entity(entity)

        # Create and store version with snapshot
        version = Version(
            entity_or_relationship_id=entity_id,
            type=VersionType.ENTITY,
            version_number=1,
            author=author,
            change_description=change_description,
            created_at=version_summary.created_at,
            snapshot=entity.model_dump(mode="json"),
        )
        await self.database.put_version(version)

        logger.info(f"Created entity {entity_id} version 1")
        return entity

    async def update_entity(
        self, entity: Entity, author_id: str, change_description: str
    ) -> Entity:
        """Update an existing entity and create a new version.

        Args:
            entity: Entity to update (with modifications)
            author_id: ID of the author updating the entity
            change_description: Description of this change

        Returns:
            Updated entity with incremented version number

        Raises:
            ValueError: If entity doesn't exist or update is invalid
        """
        # Verify entity exists
        existing = await self.database.get_entity(entity.id)
        if not existing:
            raise ValueError(f"Entity {entity.id} does not exist")

        # Get or create author
        author = await self._get_or_create_author(author_id)

        # Increment version number
        new_version_number = existing.version_summary.version_number + 1

        # Create new version summary
        version_summary = VersionSummary(
            entity_or_relationship_id=entity.id,
            type=VersionType.ENTITY,
            version_number=new_version_number,
            author=author,
            change_description=change_description,
            created_at=datetime.now(UTC),
        )

        # Update entity's version summary
        entity.version_summary = version_summary

        # Store updated entity
        await self.database.put_entity(entity)

        # Create and store version with snapshot
        version = Version(
            entity_or_relationship_id=entity.id,
            type=VersionType.ENTITY,
            version_number=new_version_number,
            author=author,
            change_description=change_description,
            created_at=version_summary.created_at,
            snapshot=entity.model_dump(mode="json"),
        )
        await self.database.put_version(version)

        logger.info(f"Updated entity {entity.id} to version {new_version_number}")
        return entity

    async def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Retrieve an entity by its ID.

        Args:
            entity_id: The unique identifier of the entity

        Returns:
            The entity if found, None otherwise
        """
        return await self.database.get_entity(entity_id)

    async def delete_entity(
        self, entity_id: str, author_id: str, change_description: str
    ) -> bool:
        """Delete an entity (hard delete).

        Args:
            entity_id: ID of the entity to delete
            author_id: ID of the author deleting the entity
            change_description: Description of this deletion

        Returns:
            True if entity was deleted, False if it didn't exist
        """
        # Delete the entity from database
        result = await self.database.delete_entity(entity_id)

        if result:
            logger.info(f"Deleted entity {entity_id}")

        return result

    async def create_relationship(
        self,
        source_entity_id: str,
        target_entity_id: str,
        relationship_type: str,
        author_id: str,
        change_description: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Relationship:
        """Create a new relationship with automatic versioning.

        Args:
            source_entity_id: ID of the source entity
            target_entity_id: ID of the target entity
            relationship_type: Type of relationship
            author_id: ID of the author creating the relationship
            change_description: Description of this change
            start_date: Optional start date of the relationship
            end_date: Optional end date of the relationship
            attributes: Optional additional attributes

        Returns:
            Created relationship with version 1

        Raises:
            ValueError: If entities don't exist or relationship data is invalid
        """
        # Validate entities exist
        source_entity = await self.database.get_entity(source_entity_id)
        if not source_entity:
            raise ValueError(f"Source entity {source_entity_id} does not exist")

        target_entity = await self.database.get_entity(target_entity_id)
        if not target_entity:
            raise ValueError(f"Target entity {target_entity_id} does not exist")

        # Validate temporal consistency
        if start_date and end_date and end_date < start_date:
            raise ValueError("Relationship end_date cannot be before start_date")

        # Validate relationship type
        valid_types = [
            "AFFILIATED_WITH",
            "EMPLOYED_BY",
            "MEMBER_OF",
            "PARENT_OF",
            "CHILD_OF",
            "SUPERVISES",
            "LOCATED_IN",
            "FUNDED_BY",
            "IMPLEMENTED_BY",
            "EXECUTED_BY",
            "OVERSEEN_BY",
        ]
        if relationship_type not in valid_types:
            raise ValueError(
                f"Invalid relationship type: {relationship_type}. Must be one of {valid_types}"
            )

        # Get or create author
        author = await self._get_or_create_author(author_id)

        # Create version summary
        # Note: We need to create the relationship first to get its ID
        relationship_data = {
            "source_entity_id": source_entity_id,
            "target_entity_id": target_entity_id,
            "type": relationship_type,
            "start_date": start_date,
            "end_date": end_date,
            "attributes": attributes,
            "created_at": datetime.now(UTC),
        }

        # Create temporary relationship to get ID
        temp_relationship = Relationship.model_validate(relationship_data)
        relationship_id = temp_relationship.id

        # Create version summary
        version_summary = VersionSummary(
            entity_or_relationship_id=relationship_id,
            type=VersionType.RELATIONSHIP,
            version_number=1,
            author=author,
            change_description=change_description,
            created_at=datetime.now(UTC),
        )

        # Add version summary to relationship data
        relationship_data["version_summary"] = version_summary

        # Create final relationship
        relationship = Relationship.model_validate(relationship_data)

        # Store relationship in database
        await self.database.put_relationship(relationship)

        # Create and store version with snapshot
        version = Version(
            entity_or_relationship_id=relationship_id,
            type=VersionType.RELATIONSHIP,
            version_number=1,
            author=author,
            change_description=change_description,
            created_at=version_summary.created_at,
            snapshot=relationship.model_dump(mode="json"),
        )
        await self.database.put_version(version)

        logger.info(f"Created relationship {relationship_id} version 1")
        return relationship

    async def update_relationship(
        self, relationship: Relationship, author_id: str, change_description: str
    ) -> Relationship:
        """Update an existing relationship and create a new version.

        Args:
            relationship: Relationship to update (with modifications)
            author_id: ID of the author updating the relationship
            change_description: Description of this change

        Returns:
            Updated relationship with incremented version number

        Raises:
            ValueError: If relationship doesn't exist or update is invalid
        """
        # Verify relationship exists
        existing = await self.database.get_relationship(relationship.id)
        if not existing:
            raise ValueError(f"Relationship {relationship.id} does not exist")

        # Validate temporal consistency
        if (
            relationship.start_date
            and relationship.end_date
            and relationship.end_date < relationship.start_date
        ):
            raise ValueError("Relationship end_date cannot be before start_date")

        # Get or create author
        author = await self._get_or_create_author(author_id)

        # Increment version number
        new_version_number = existing.version_summary.version_number + 1

        # Create new version summary
        version_summary = VersionSummary(
            entity_or_relationship_id=relationship.id,
            type=VersionType.RELATIONSHIP,
            version_number=new_version_number,
            author=author,
            change_description=change_description,
            created_at=datetime.now(UTC),
        )

        # Update relationship's version summary
        relationship.version_summary = version_summary

        # Store updated relationship
        await self.database.put_relationship(relationship)

        # Create and store version with snapshot
        version = Version(
            entity_or_relationship_id=relationship.id,
            type=VersionType.RELATIONSHIP,
            version_number=new_version_number,
            author=author,
            change_description=change_description,
            created_at=version_summary.created_at,
            snapshot=relationship.model_dump(mode="json"),
        )
        await self.database.put_version(version)

        logger.info(
            f"Updated relationship {relationship.id} to version {new_version_number}"
        )
        return relationship

    async def delete_relationship(
        self, relationship_id: str, author_id: str, change_description: str
    ) -> bool:
        """Delete a relationship.

        Args:
            relationship_id: ID of the relationship to delete
            author_id: ID of the author deleting the relationship
            change_description: Description of this deletion

        Returns:
            True if relationship was deleted, False if it didn't exist
        """
        # Delete the relationship from database
        result = await self.database.delete_relationship(relationship_id)

        if result:
            logger.info(f"Deleted relationship {relationship_id}")

        return result

    async def get_relationships_by_entity(
        self, entity_id: str, direction: str = "both"
    ) -> List[Relationship]:
        """Get all relationships for an entity.

        Args:
            entity_id: ID of the entity
            direction: Direction filter - "source", "target", or "both"

        Returns:
            List of relationships
        """
        return await self.database.list_relationships_by_entity(
            entity_id=entity_id, direction=direction, limit=1000
        )

    async def get_entity_versions(self, entity_id: str) -> List[Version]:
        """Get version history for an entity.

        Args:
            entity_id: ID of the entity

        Returns:
            List of versions ordered by version number
        """
        return await self.database.list_versions_by_entity(
            entity_or_relationship_id=entity_id, limit=1000, order="asc"
        )

    async def get_relationship_versions(self, relationship_id: str) -> List[Version]:
        """Get version history for a relationship.

        Args:
            relationship_id: ID of the relationship

        Returns:
            List of versions ordered by version number
        """
        return await self.database.list_versions_by_entity(
            entity_or_relationship_id=relationship_id, limit=1000, order="asc"
        )

    async def update_entity_with_relationships(
        self,
        entity: Entity,
        new_relationships: List[Dict[str, Any]],
        author_id: str,
        change_description: str,
    ) -> Dict[str, Any]:
        """Update an entity and create new relationships atomically.

        Args:
            entity: Entity to update
            new_relationships: List of relationship data dictionaries
            author_id: ID of the author performing the update
            change_description: Description of this change

        Returns:
            Dictionary with "entity" and "relationships" keys

        Raises:
            ValueError: If operation fails, rolls back all changes
        """
        # Store original entity state for rollback
        original_entity = await self.database.get_entity(entity.id)
        if not original_entity:
            raise ValueError(f"Entity {entity.id} does not exist")

        created_relationships = []

        try:
            # Update entity
            updated_entity = await self.update_entity(
                entity=entity,
                author_id=author_id,
                change_description=change_description,
            )

            # Create new relationships
            for rel_data in new_relationships:
                # Validate required fields
                if (
                    "source_entity_id" not in rel_data
                    or "target_entity_id" not in rel_data
                ):
                    raise ValueError(
                        "Relationship must have source_entity_id and target_entity_id"
                    )
                if "relationship_type" not in rel_data:
                    raise ValueError("Relationship must have relationship_type")

                relationship = await self.create_relationship(
                    source_entity_id=rel_data["source_entity_id"],
                    target_entity_id=rel_data["target_entity_id"],
                    relationship_type=rel_data["relationship_type"],
                    author_id=author_id,
                    change_description=change_description,
                    start_date=rel_data.get("start_date"),
                    end_date=rel_data.get("end_date"),
                    attributes=rel_data.get("attributes"),
                )
                created_relationships.append(relationship)

            return {"entity": updated_entity, "relationships": created_relationships}

        except Exception as e:
            # Rollback: restore original entity
            logger.error(f"Coordinated operation failed, rolling back: {e}")
            await self.database.put_entity(original_entity)

            # Delete any created relationships
            for relationship in created_relationships:
                await self.database.delete_relationship(relationship.id)

            raise ValueError(f"Coordinated operation failed: {e}")

    async def batch_create_entities(
        self,
        entities_data: List[Dict[str, Any]],
        author_id: str,
        change_description: str,
    ) -> List[Entity]:
        """Create multiple entities in batch.

        Args:
            entities_data: List of entity data dictionaries (must include 'type' and optionally 'sub_type')
            author_id: ID of the author creating the entities
            change_description: Description of this batch operation

        Returns:
            List of created entities

        Raises:
            ValueError: If any entity creation fails
        """
        entities = []
        for entity_data in entities_data:
            entity_type = EntityType(entity_data.get("type"))
            entity_subtype = (
                EntitySubType(entity_data.get("sub_type"))
                if entity_data.get("sub_type")
                else None
            )
            entity = await self.create_entity(
                entity_type=entity_type,
                entity_data=entity_data,
                author_id=author_id,
                change_description=change_description,
                entity_subtype=entity_subtype,
            )
            entities.append(entity)

        return entities

    # Helper methods

    async def _get_or_create_author(self, author_id: str) -> Author:
        """Get an existing author or create a new one.

        Args:
            author_id: ID of the author (format: author:slug")

        Returns:
            Author instance
        """
        # Try to get existing author
        author = await self.database.get_author(author_id)

        if author:
            return author

        # Create new author
        # Extract slug from author_id (format: author:slug")
        if ":" in author_id:
            slug = author_id.split(":", 1)[1]
        else:
            slug = author_id

        author = Author(slug=slug)
        await self.database.put_author(author)

        return author

    def _create_entity_instance(self, entity_data: Dict[str, Any]) -> Entity:
        """Create an entity instance of the appropriate type.

        Args:
            entity_data: Dictionary containing entity data

        Returns:
            Entity instance (Person, Organization, or Location)

        Raises:
            ValueError: If entity type is invalid
        """
        entity_type = entity_data.get("type")
        entity_subtype = entity_data.get("sub_type")

        if entity_type == "person" or entity_type == EntityType.PERSON:
            return Person.model_validate(entity_data)
        elif entity_type == "organization" or entity_type == EntityType.ORGANIZATION:
            if (
                entity_subtype == "political_party"
                or entity_subtype == EntitySubType.POLITICAL_PARTY
            ):
                return PoliticalParty.model_validate(entity_data)
            elif (
                entity_subtype == "government_body"
                or entity_subtype == EntitySubType.GOVERNMENT_BODY
            ):
                return GovernmentBody.model_validate(entity_data)
            elif (
                entity_subtype == "hospital" or entity_subtype == EntitySubType.HOSPITAL
            ):
                return Hospital.model_validate(entity_data)
            else:
                return Organization.model_validate(entity_data)
        elif entity_type == "location" or entity_type == EntityType.LOCATION:
            return Location.model_validate(entity_data)
        elif entity_type == "project" or entity_type == EntityType.PROJECT:
            return Project.model_validate(entity_data)
        else:
            raise ValueError(f"Unknown entity type: {entity_type}")
