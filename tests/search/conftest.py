"""Shared fixtures for search module tests."""

import pytest

from nes.database.file_database import FileDatabase
from nes.services.publication import PublicationService


@pytest.fixture
def make_entity(temp_db_path):
    """Return an async factory that persists and returns a valid Entity.

    Building through PublicationService guarantees the entity is valid and
    fully populated (version_summary, created_at, computed id) the same way
    production data is.
    """
    db = FileDatabase(base_path=str(temp_db_path))
    pub = PublicationService(database=db)

    async def _make(entity_prefix: str, entity_data: dict):
        return await pub.create_entity(
            entity_prefix, entity_data, "author:test", "test entity"
        )

    return _make
