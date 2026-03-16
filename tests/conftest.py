"""Pytest configuration and fixtures for nes tests."""

import shutil
import tempfile
from pathlib import Path

import pytest

_STANDARD_PREFIXES = {
    "person",
    "organization",
    "organization/political_party",
    "organization/government_body",
    "organization/ngo",
    "organization/international_org",
    "organization/hospital",
    "location",
    "location/province",
    "location/district",
    "location/metropolitan_city",
    "location/sub_metropolitan_city",
    "location/municipality",
    "location/rural_municipality",
    "location/ward",
    "location/constituency",
    "project",
    "project/development_project",
}


@pytest.fixture(autouse=True)
def seed_allowed_entity_prefixes():
    """Seed ALLOWED_ENTITY_PREFIXES with standard prefixes for the duration of each test."""
    from nes.core.models.entity_type_map import ALLOWED_ENTITY_PREFIXES

    original = set(ALLOWED_ENTITY_PREFIXES)
    ALLOWED_ENTITY_PREFIXES.update(_STANDARD_PREFIXES)
    yield
    ALLOWED_ENTITY_PREFIXES.clear()
    ALLOWED_ENTITY_PREFIXES.update(original)


@pytest.fixture
def temp_db_path():
    """Create a temporary database directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_nepali_person():
    """Sample Nepali politician entity data."""
    return {
        "slug": "ram-chandra-poudel",
        "type": "person",
        "sub_type": None,
        "names": [
            {
                "kind": "PRIMARY",
                "en": {
                    "full": "Ram Chandra Poudel",
                    "given": "Ram Chandra",
                    "family": "Poudel",
                },
                "ne": {"full": "राम चन्द्र पौडेल", "given": "राम चन्द्र", "family": "पौडेल"},
            }
        ],
        "attributes": {
            "party": "nepali-congress",
            "constituency": "Tanahun-1",
            "role": "politician",
        },
    }


@pytest.fixture
def sample_nepali_organization():
    """Sample Nepali political party entity data."""
    return {
        "slug": "nepali-congress",
        "type": "organization",
        "sub_type": "political_party",
        "names": [
            {
                "kind": "PRIMARY",
                "en": {"full": "Nepali Congress"},
                "ne": {"full": "नेपाली कांग्रेस"},
            }
        ],
        "attributes": {"founded": "1947", "ideology": "social-democracy"},
    }


@pytest.fixture
def sample_nepali_location():
    """Sample Nepali location entity data."""
    return {
        "slug": "kathmandu-metropolitan-city",
        "type": "location",
        "sub_type": "metropolitan_city",
        "names": [
            {
                "kind": "PRIMARY",
                "en": {"full": "Kathmandu Metropolitan City"},
                "ne": {"full": "काठमाडौं महानगरपालिका"},
            }
        ],
        "attributes": {"province": "Bagmati", "district": "Kathmandu"},
    }


@pytest.fixture
def sample_relationship():
    """Sample relationship between entities."""
    return {
        "source_entity_id": "entity:person/ram-chandra-poudel",
        "target_entity_id": "entity:organization/political_party/nepali-congress",
        "type": "MEMBER_OF",
        "start_date": "2000-01-01",
        "attributes": {"position": "President"},
    }


@pytest.fixture
def sample_version():
    """Sample version metadata."""
    return {
        "entity_id": "entity:person/ram-chandra-poudel",
        "version": 1,
        "created_at": "2024-01-01T00:00:00Z",
        "created_by": "author:system:csv-importer",
        "change_description": "Initial import",
    }


@pytest.fixture
def authentic_nepali_politicians():
    """List of authentic Nepali politician names for testing."""
    from tests.fixtures.nepali_data import NEPALI_POLITICIANS

    return NEPALI_POLITICIANS


@pytest.fixture
def authentic_nepali_parties():
    """List of authentic Nepali political parties for testing."""
    from tests.fixtures.nepali_data import NEPALI_POLITICAL_PARTIES

    return NEPALI_POLITICAL_PARTIES


@pytest.fixture
def authentic_nepali_locations():
    """List of authentic Nepali administrative divisions for testing."""
    from tests.fixtures.nepali_data import (
        NEPALI_DISTRICTS,
        NEPALI_MUNICIPALITIES,
        NEPALI_PROVINCES,
    )

    return {
        "provinces": NEPALI_PROVINCES,
        "districts": NEPALI_DISTRICTS,
        "municipalities": NEPALI_MUNICIPALITIES,
    }


@pytest.fixture
def authentic_nepali_government_bodies():
    """List of authentic Nepali government bodies for testing."""
    from tests.fixtures.nepali_data import NEPALI_GOVERNMENT_BODIES

    return NEPALI_GOVERNMENT_BODIES


@pytest.fixture
def authentic_nepali_constituencies():
    """List of authentic Nepali electoral constituencies for testing."""
    from tests.fixtures.nepali_data import NEPALI_CONSTITUENCIES

    return NEPALI_CONSTITUENCIES
