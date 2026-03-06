"""Configuration for Nepal Entity Service v2."""

import logging
import os
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
from urllib.request import url2pathname

logger = logging.getLogger(__name__)


class Config:
    """Configuration class for nes."""

    # Global instances for database and services
    _database: Optional[object] = None  # type: EntityDatabase
    _search_service: Optional[object] = None  # type: SearchService
    _publication_service: Optional[object] = None  # type: PublicationService

    @classmethod
    def get_db_path(cls, override_path: Optional[str] = None) -> Path:
        """Get the database path.

        Supports multiple configuration methods in order of precedence:
        1. override_path parameter
        2. NES_DB_URL environment variable (file:// or file+memcached:// protocol)

        Args:
            override_path: Optional path to override the default database path

        Returns:
            Path object for the database directory

        Raises:
            ValueError: If NES_DB_URL uses unsupported protocol or is not set
        """
        if override_path:
            return Path(override_path)

        # Check for NES_DB_URL environment variable
        database_url = os.getenv("NES_DB_URL")
        if not database_url:
            raise ValueError(
                "NES_DB_URL environment variable must be set. "
                "The database is managed separately from the codebase. "
                "Examples:\n"
                "  file:///absolute/path/to/nes-db/v2\n"
                "  file+memcached:///absolute/path/to/nes-db/v2"
            )

        parsed = urlparse(database_url)
        # Support both file:// and file+memcached:// protocols
        if parsed.scheme not in ("file", "file+memcached"):
            raise ValueError(
                f"NES_DB_URL must use 'file://' or 'file+memcached://' protocol, got '{parsed.scheme}://'. "
                f"Examples:\n"
                f"  file:///absolute/path/to/nes-db/v2\n"
                f"  file+memcached:///absolute/path/to/nes-db/v2"
            )

        if parsed.netloc:
            raise ValueError(f"NES_DB_URL should not have an authority/hostname, got '{parsed.netloc}'. Ensure you use 'file:///' (three slashes) for absolute paths.")

        # Extract path from URL
        db_path = url2pathname(parsed.path)
        logger.info(f"Using NES_DB_URL: {database_url} -> {db_path}")
        return Path(db_path)

    @classmethod
    def get_db_protocol(cls) -> str:
        """Get the database protocol from NES_DB_URL.

        Returns:
            Protocol string ('file' or 'file+memcached')
        """
        database_url = os.getenv("NES_DB_URL")
        if not database_url:
            raise ValueError(
                "NES_DB_URL environment variable must be set. "
                "The database is managed separately from the codebase. Examples:\n"
                "  file:///absolute/path/to/nes-db/v2\n"
                "  file+memcached:///absolute/path/to/nes-db/v2"
            )

        parsed = urlparse(database_url)
        if parsed.scheme not in ("file", "file+memcached"):
            raise ValueError(
                f"NES_DB_URL must use 'file://' or 'file+memcached://' protocol, got '{parsed.scheme}://'. "
                f"Examples:\n"
                f"  file:///absolute/path/to/nes-db/v2\n"
                f"  file+memcached:///absolute/path/to/nes-db/v2"
            )
        return parsed.scheme

    @classmethod
    def ensure_db_path_exists(cls, db_path: Optional[Path] = None) -> Path:
        """Ensure the database path exists, creating it if necessary.

        Args:
            db_path: Optional database path, uses default if not provided

        Returns:
            Path object for the database directory
        """
        if db_path is None:
            db_path = cls.get_db_path()

        db_path.mkdir(parents=True, exist_ok=True)
        return db_path

    @classmethod
    def initialize_database(cls, base_path: Optional[str] = None) -> "EntityDatabase":
        """Initialize the global database instance.

        Supports different database implementations based on NES_DB_URL protocol:
        - file:// - Standard FileDatabase
        - file+memcached:// - InMemoryCachedReadDatabase (read-only with full cache)

        Args:
            base_path: Optional path to the database directory. Uses NES_DB_URL if not provided.

        Returns:
            Initialized database instance
        """
        if base_path is None:
            base_path = str(cls.get_db_path())

        protocol = cls.get_db_protocol()

        if protocol == "file+memcached":
            from nes.database.file_database import FileDatabase
            from nes.database.in_memory_cached_read_database import (
                InMemoryCachedReadDatabase,
            )

            # Create underlying FileDatabase
            underlying_db = FileDatabase(base_path=base_path)

            # Wrap with in-memory cache
            cls._database = InMemoryCachedReadDatabase(underlying_db)
            logger.info(f"In-memory cached read database initialized at {base_path}")
        else:
            from nes.database.file_database import FileDatabase

            cls._database = FileDatabase(base_path=base_path)
            logger.info(f"Database initialized at {base_path}")

        return cls._database

    @classmethod
    def get_database(cls) -> "EntityDatabase":
        """Get the global database instance.

        Returns:
            EntityDatabase instance

        Raises:
            RuntimeError: If database is not initialized
        """
        if cls._database is None:
            raise RuntimeError(
                "Database not initialized. Call initialize_database() first."
            )
        return cls._database

    @classmethod
    def get_search_service(cls) -> "SearchService":
        """Get or create the global search service instance.

        Returns:
            SearchService instance
        """
        if cls._search_service is None:
            from nes.services.search import SearchService

            db = cls.get_database()
            cls._search_service = SearchService(database=db)
            logger.info("Search service initialized")

        return cls._search_service

    @classmethod
    def get_publication_service(cls) -> "PublicationService":
        """Get or create the global publication service instance.

        Returns:
            PublicationService instance
        """
        if cls._publication_service is None:
            from nes.services.publication import PublicationService

            db = cls.get_database()
            cls._publication_service = PublicationService(database=db)
            logger.info("Publication service initialized")

        return cls._publication_service

    @classmethod
    def cleanup(cls):
        """Clean up global instances on shutdown."""
        logger.info("Cleaning up global instances")
        cls._database = None
        cls._search_service = None
        cls._publication_service = None


# Global configuration instance
config = Config()
