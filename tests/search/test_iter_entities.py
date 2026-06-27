"""Tests for streaming entity iteration used by bulk reindex."""

import pytest

from nes.database.file_database import FileDatabase
from nes.services.publication import PublicationService


@pytest.mark.asyncio
async def test_iter_entities_streams_all(temp_db_path):
    db = FileDatabase(base_path=str(temp_db_path))
    pub = PublicationService(database=db)

    expected_ids = set()
    for i in range(7):
        entity = await pub.create_entity(
            "person",
            {
                "slug": f"person-{i}",
                "names": [{"kind": "PRIMARY", "en": {"full": f"Person {i}"}}],
            },
            "author:test",
            "seed",
        )
        expected_ids.add(entity.id)

    # Small batch size to exercise multiple chunks.
    seen = [e.id async for e in db.iter_entities(batch_size=3)]

    assert set(seen) == expected_ids
    assert len(seen) == len(expected_ids)  # no duplicates


@pytest.mark.asyncio
async def test_iter_entities_empty(temp_db_path):
    db = FileDatabase(base_path=str(temp_db_path))
    seen = [e async for e in db.iter_entities()]
    assert seen == []
