"""Abstract EntityDatabase class for CRUD operations in nes.

This module defines the abstract interface that all database implementations
must follow. It provides a consistent API for entity, relationship, version,
and author operations.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union

from nes.core.models.entity import Entity
from nes.core.models.relationship import Relationship
from nes.core.models.version import Author, Version


class EntityDatabase(ABC):
    """Abstract base class for entity database operations.

    All database implementations must inherit from this class and implement
    all abstract methods. This ensures a consistent interface across different
    storage backends (file-based, SQL, NoSQL, etc.).
    """

    @abstractmethod
    async def put_entity(self, entity: Entity) -> Entity:
        """Store an entity in the database.

        Args:
            entity: The entity to store

        Returns:
            The stored entity
        """
        pass

    @abstractmethod
    async def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Retrieve an entity by its ID.

        Args:
            entity_id: The unique identifier of the entity

        Returns:
            The entity if found, None otherwise
        """
        pass

    @abstractmethod
    async def delete_entity(self, entity_id: str) -> bool:
        """Delete an entity from the database.

        Args:
            entity_id: The unique identifier of the entity to delete

        Returns:
            True if the entity was deleted, False if it didn't exist
        """
        pass

    @abstractmethod
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
        """
        pass

    @abstractmethod
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
        pass

    async def get_all_tags(self) -> List[str]:
        """Return all unique tag values across all entities, sorted."""
        entities = await self.list_entities(limit=999999)
        tags: set = set()
        for entity in entities:
            if entity.tags:
                for tag in entity.tags:
                    if isinstance(tag, str):
                        tags.add(tag)
        return sorted(tags)

    @abstractmethod
    async def put_relationship(self, relationship: Relationship) -> Relationship:
        """Store a relationship in the database.

        Args:
            relationship: The relationship to store

        Returns:
            The stored relationship
        """
        pass

    @abstractmethod
    async def get_relationship(self, relationship_id: str) -> Optional[Relationship]:
        """Retrieve a relationship by its ID.

        Args:
            relationship_id: The unique identifier of the relationship

        Returns:
            The relationship if found, None otherwise
        """
        pass

    @abstractmethod
    async def delete_relationship(self, relationship_id: str) -> bool:
        """Delete a relationship from the database.

        Args:
            relationship_id: The unique identifier of the relationship to delete

        Returns:
            True if the relationship was deleted, False if it didn't exist
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def put_version(self, version: Version) -> Version:
        """Store a version in the database.

        Args:
            version: The version to store

        Returns:
            The stored version
        """
        pass

    @abstractmethod
    async def get_version(self, version_id: str) -> Optional[Version]:
        """Retrieve a version by its ID.

        Args:
            version_id: The unique identifier of the version

        Returns:
            The version if found, None otherwise
        """
        pass

    @abstractmethod
    async def delete_version(self, version_id: str) -> bool:
        """Delete a version from the database.

        Args:
            version_id: The unique identifier of the version to delete

        Returns:
            True if the version was deleted, False if it didn't exist
        """
        pass

    @abstractmethod
    async def list_versions(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Version]:
        """List versions with pagination.

        Note: This method will be enhanced in future tasks to require
        entity_id or relationship_id parameter for filtering.

        Args:
            limit: Maximum number of versions to return
            offset: Number of versions to skip

        Returns:
            List of versions
        """
        pass

    @abstractmethod
    async def put_author(self, author: Author) -> Author:
        """Store an author in the database.

        Args:
            author: The author to store

        Returns:
            The stored author
        """
        pass

    @abstractmethod
    async def get_author(self, author_id: str) -> Optional[Author]:
        """Retrieve an author by its ID.

        Args:
            author_id: The unique identifier of the author

        Returns:
            The author if found, None otherwise
        """
        pass

    @abstractmethod
    async def delete_author(self, author_id: str) -> bool:
        """Delete an author from the database.

        Args:
            author_id: The unique identifier of the author to delete

        Returns:
            True if the author was deleted, False if it didn't exist
        """
        pass

    @abstractmethod
    async def list_authors(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Author]:
        """List authors with pagination.

        Args:
            limit: Maximum number of authors to return
            offset: Number of authors to skip

        Returns:
            List of authors
        """
        pass
