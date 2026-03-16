"""In-memory cached read-only database adaptor for nes.

This module provides a read-only database wrapper that maintains a full
in-memory cache of entities and relationships. The cache is automatically
warmed at instantiation and does not support write operations.
"""

from typing import Dict, List, Optional, Tuple, Union

from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options

from nes.core.models.entity import Entity
from nes.core.models.relationship import Relationship
from nes.core.models.version import Author, Version

from .entity_database import EntityDatabase


class InMemoryCachedReadDatabase(EntityDatabase):
    """Read-only database with full in-memory cache.

    This adaptor wraps an underlying EntityDatabase and maintains a complete
    in-memory cache of all entities and relationships. The cache is warmed
    automatically at instantiation. Write operations are not permitted.

    **Important:** This implementation assumes the underlying database will NOT
    be modified during runtime. The cache is loaded once at initialization and
    never refreshed. Any changes to the underlying database after initialization
    will not be reflected in this cached instance.

    Features:
    - Full in-memory cache of entities and relationships
    - Automatic cache warming at initialization
    - Beaker cache for CPU-heavy operations (search, list with filters)
    - Read-only operations (write operations raise ValueError)
    - No cache invalidation or updates needed
    - Static snapshot of database state at initialization time

    Use Cases:
    - Production read-only API servers with static data
    - High-performance query services
    - Environments where database is updated via separate deployment/restart

    Not Suitable For:
    - Applications requiring real-time data updates
    - Environments where underlying database is modified during runtime
    - Long-running processes with frequently changing data
    """

    def __init__(self, underlying_db: EntityDatabase, cache_size: int = 128):
        """Initialize with automatic cache warming.

        Args:
            underlying_db: The underlying database to cache
            cache_size: Size of Beaker cache for CPU-heavy operations (default: 128)
        """
        self.underlying_db = underlying_db
        self._entity_cache: Dict[str, Entity] = {}
        self._relationship_cache: Dict[str, Relationship] = {}
        self._tags_cache: List[str] = []
        self._cache_warmed = False

        # Configure Beaker cache for CPU-heavy operations
        cache_opts = {
            "cache.type": "memory",
            "cache.lock_dir": "/tmp/cache/lock",
        }
        self._cache_manager = CacheManager(**parse_cache_config_options(cache_opts))
        self._query_cache = self._cache_manager.get_cache(
            f"in_memory_db_queries_{id(self)}",
            expire=3600,  # 1 hour expiration
        )

    async def _ensure_cache_warmed(self):
        """Ensure cache is warmed before any operation."""
        if not self._cache_warmed:
            # Load all entities
            entities = await self.underlying_db.list_entities(limit=999999)
            for entity in entities:
                self._entity_cache[entity.id] = entity

            # Load all relationships
            relationships = await self.underlying_db.list_relationships(limit=999999)
            for relationship in relationships:
                self._relationship_cache[relationship.id] = relationship

            # Compute available tags once during warming
            tags: set[str] = set()
            for entity in self._entity_cache.values():
                if entity.tags:
                    for tag in entity.tags:
                        if isinstance(tag, str):
                            tags.add(tag)
            self._tags_cache = sorted(tags)

            self._cache_warmed = True

    def _entity_matches_tags(self, entity: Entity, tags: Tuple[str, ...]) -> bool:
        """Check if entity has all specified tags (AND logic).

        Args:
            entity: Entity to check
            tags: Tuple of tags that entity must have

        Returns:
            True if entity has ALL specified tags, False otherwise
        """
        entity_tags = entity.tags or []
        return all(tag in entity_tags for tag in tags)

    async def put_entity(self, entity: Entity) -> Entity:
        """Not supported - read-only database."""
        raise ValueError("Read-only database does not support write operations")

    async def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Retrieve an entity from cache."""
        await self._ensure_cache_warmed()
        return self._entity_cache.get(entity_id)

    async def get_all_tags(self) -> List[str]:
        """Return all unique tag values across all entities, sorted."""
        await self._ensure_cache_warmed()
        return list(self._tags_cache)

    async def delete_entity(self, entity_id: str) -> bool:
        """Not supported - read-only database."""
        raise ValueError("Read-only database does not support write operations")

    def _list_entities_impl(
        self,
        limit: int,
        offset: int,
        entity_type: Optional[str],
        sub_type: Optional[str],
        attr_filters_tuple: Optional[
            Tuple[Tuple[str, Union[str, int, float, bool]], ...]
        ],
    ) -> Tuple[Entity, ...]:
        """Internal implementation of list_entities with hashable parameters.

        Returns tuple for immutability (required for LRU cache).
        """
        entities = list(self._entity_cache.values())

        # Apply entity_type filter
        if entity_type:
            entities = [
                e
                for e in entities
                if (e.type.value if hasattr(e.type, "value") else e.type) == entity_type
            ]

        # Apply sub_type filter
        if sub_type:
            entities = [
                e
                for e in entities
                if e.sub_type
                and (e.sub_type.value if hasattr(e.sub_type, "value") else e.sub_type)
                == sub_type
            ]

        # Apply attribute filters
        if attr_filters_tuple:
            for key, value in attr_filters_tuple:
                entities = [
                    e
                    for e in entities
                    if e.attributes and e.attributes.get(key) == value
                ]

        # Apply pagination and return as tuple
        return tuple(entities[offset : offset + limit])

    async def list_entities(
        self,
        limit: int = 100,
        offset: int = 0,
        entity_type: Optional[str] = None,
        sub_type: Optional[str] = None,
        attr_filters: Optional[Dict[str, Union[str, int, float, bool]]] = None,
    ) -> List[Entity]:
        """List entities from cache with filtering (Beaker cached)."""
        await self._ensure_cache_warmed()

        # Convert attr_filters dict to tuple for hashability
        attr_filters_tuple = None
        if attr_filters:
            attr_filters_tuple = tuple(sorted(attr_filters.items()))

        # Create cache key
        cache_key = f"list_entities:{limit}:{offset}:{entity_type}:{sub_type}:{attr_filters_tuple}"

        # Try to get from cache
        def create_value():
            return self._list_entities_impl(
                limit, offset, entity_type, sub_type, attr_filters_tuple
            )

        result_tuple = self._query_cache.get(key=cache_key, createfunc=create_value)

        # Convert back to list
        return list(result_tuple)

    def _search_entities_impl(
        self,
        query: Optional[str],
        entity_type: Optional[str],
        sub_type: Optional[str],
        attr_filters_tuple: Optional[
            Tuple[Tuple[str, Union[str, int, float, bool]], ...]
        ],
        tags_tuple: Optional[Tuple[str, ...]],
        entity_prefix: Optional[str],
        limit: int,
        offset: int,
    ) -> Tuple[Entity, ...]:
        """Internal implementation of search_entities with hashable parameters.

        Returns tuple for immutability (required for LRU cache).
        """
        entities = list(self._entity_cache.values())

        # Apply text search on names
        if query:
            query_lower = query.lower()
            matching_entities = []
            for entity in entities:
                # Search in all names
                for name in entity.names:
                    # Search in all language variants
                    for lang_text in [name.en, name.ne]:
                        if lang_text:
                            # Check all text fields in the LangText
                            text_values = []
                            if hasattr(lang_text, "full") and lang_text.full:
                                text_values.append(lang_text.full)
                            if hasattr(lang_text, "given") and lang_text.given:
                                text_values.append(lang_text.given)
                            if hasattr(lang_text, "family") and lang_text.family:
                                text_values.append(lang_text.family)

                            if any(query_lower in text.lower() for text in text_values):
                                matching_entities.append(entity)
                                break
                    else:
                        continue
                    break
            entities = matching_entities

        # Apply entity_type filter
        if entity_type:
            entities = [
                e
                for e in entities
                if (e.type.value if hasattr(e.type, "value") else e.type) == entity_type
            ]

        # Apply sub_type filter
        if sub_type:
            entities = [
                e
                for e in entities
                if e.sub_type
                and (e.sub_type.value if hasattr(e.sub_type, "value") else e.sub_type)
                == sub_type
            ]

        # Apply attribute filters
        if attr_filters_tuple:
            for key, value in attr_filters_tuple:
                entities = [
                    e
                    for e in entities
                    if e.attributes and e.attributes.get(key) == value
                ]

        # Apply tag filters (AND logic - entity must have ALL specified tags)
        if tags_tuple:
            entities = [e for e in entities if self._entity_matches_tags(e, tags_tuple)]

        # Apply entity_prefix filter (startswith logic)
        if entity_prefix:
            entities = [
                e
                for e in entities
                if e.entity_prefix is not None
                and (
                    e.entity_prefix == entity_prefix
                    or e.entity_prefix.startswith(entity_prefix + "/")
                )
            ]

        # Apply pagination and return as tuple
        return tuple(entities[offset : offset + limit])

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
        """Search entities from cache (Beaker cached)."""
        await self._ensure_cache_warmed()

        # Convert attr_filters dict to tuple for hashability
        attr_filters_tuple = None
        if attr_filters:
            attr_filters_tuple = tuple(sorted(attr_filters.items()))

        # Convert tags list to tuple for hashability
        tags_tuple = None
        if tags and len(tags) > 0:
            tags_tuple = tuple(tags)

        # Create cache key
        cache_key = f"search_entities:{query}:{entity_prefix}:{attr_filters_tuple}:{tags_tuple}:{limit}:{offset}"

        # Try to get from cache
        def create_value():
            return self._search_entities_impl(
                query,
                entity_type,
                sub_type,
                attr_filters_tuple,
                tags_tuple,
                entity_prefix,
                limit,
                offset,
            )

        result_tuple = self._query_cache.get(key=cache_key, createfunc=create_value)

        # Convert back to list
        return list(result_tuple)

    async def put_relationship(self, relationship: Relationship) -> Relationship:
        """Not supported - read-only database."""
        raise ValueError("Read-only database does not support write operations")

    async def get_relationship(self, relationship_id: str) -> Optional[Relationship]:
        """Retrieve a relationship from cache."""
        await self._ensure_cache_warmed()
        return self._relationship_cache.get(relationship_id)

    async def delete_relationship(self, relationship_id: str) -> bool:
        """Not supported - read-only database."""
        raise ValueError("Read-only database does not support write operations")

    async def list_relationships(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Relationship]:
        """List relationships from cache."""
        await self._ensure_cache_warmed()
        relationships = list(self._relationship_cache.values())
        return relationships[offset : offset + limit]

    async def put_version(self, version: Version) -> Version:
        """Not supported - read-only database."""
        raise ValueError("Read-only database does not support write operations")

    async def get_version(self, version_id: str) -> Optional[Version]:
        """Delegate to underlying database - versions not cached."""
        return await self.underlying_db.get_version(version_id)

    async def delete_version(self, version_id: str) -> bool:
        """Not supported - read-only database."""
        raise ValueError("Read-only database does not support write operations")

    async def list_versions(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Version]:
        """Delegate to underlying database - versions not cached."""
        return await self.underlying_db.list_versions(limit=limit, offset=offset)

    async def put_author(self, author: Author) -> Author:
        """Not supported - read-only database."""
        raise ValueError("Read-only database does not support write operations")

    async def get_author(self, author_id: str) -> Optional[Author]:
        """Delegate to underlying database - authors not cached."""
        return await self.underlying_db.get_author(author_id)

    async def delete_author(self, author_id: str) -> bool:
        """Not supported - read-only database."""
        raise ValueError("Read-only database does not support write operations")

    async def list_authors(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Author]:
        """Delegate to underlying database - authors not cached."""
        return await self.underlying_db.list_authors(limit=limit, offset=offset)
