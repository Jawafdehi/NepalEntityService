"""Tests for identifier validators in nes."""

import pytest

from nes.core.models.entity_type_map import ALLOWED_ENTITY_PREFIXES

# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def register_moha_prefix():
    """Register 3-level prefix for testing and clean up after."""
    test_prefix = "organization/nepal_govt/moha"
    ALLOWED_ENTITY_PREFIXES.add(test_prefix)
    yield test_prefix
    ALLOWED_ENTITY_PREFIXES.discard(test_prefix)


# ===========================================================================
# Backward compat: existing entity IDs still validate
# ===========================================================================


def test_validate_entity_id_valid():
    """Test validating valid entity IDs."""
    from nes.core.identifiers.validators import is_valid_entity_id, validate_entity_id

    # Valid with subtype
    entity_id = "entity:person/ram-chandra-poudel"
    assert is_valid_entity_id(entity_id)
    assert validate_entity_id(entity_id) == entity_id

    # Valid without subtype
    entity_id = "entity:person/ram-chandra-poudel"
    assert is_valid_entity_id(entity_id)
    assert validate_entity_id(entity_id) == entity_id


def test_validate_entity_id_invalid_format():
    """Test validating invalid entity ID formats."""
    from nes.core.identifiers.validators import is_valid_entity_id

    # Missing entity: prefix
    assert not is_valid_entity_id("person/ram-chandra-poudel")

    # Invalid slug (uppercase)
    assert not is_valid_entity_id("entity:person/Ram-Chandra-Poudel")

    # Slug too short
    assert not is_valid_entity_id("entity:person/ab")


def test_validate_existing_2_segment_ids_pass():
    """Existing 2-segment entity IDs continue to pass validation — backward compat regression."""
    from nes.core.identifiers.validators import validate_entity_id

    # Real entity IDs from the database
    assert (
        validate_entity_id("entity:person/rabi-lamichhane")
        == "entity:person/rabi-lamichhane"
    )
    assert (
        validate_entity_id(
            "entity:organization/political_party/national-independent-party"
        )
        == "entity:organization/political_party/national-independent-party"
    )
    assert (
        validate_entity_id("entity:location/district/kathmandu")
        == "entity:location/district/kathmandu"
    )
    assert (
        validate_entity_id("entity:location/constituency/acham-1")
        == "entity:location/constituency/acham-1"
    )
    assert (
        validate_entity_id(
            "entity:organization/government_body/accham-district-development-committee"
        )
        == "entity:organization/government_body/accham-district-development-committee"
    )


# ===========================================================================
# New: 3-segment prefix validation
# ===========================================================================


def test_validate_3_segment_prefix_in_registry_passes(register_moha_prefix):
    """A 3-segment entity ID passes validation when its prefix is in ALLOWED_ENTITY_PREFIXES."""
    from nes.core.identifiers.validators import validate_entity_id

    result = validate_entity_id(
        f"entity:{register_moha_prefix}/department-of-immigration"
    )
    assert result == f"entity:{register_moha_prefix}/department-of-immigration"


def test_validate_unknown_prefix_raises():
    """validate_entity_id raises ValueError for a prefix not in ALLOWED_ENTITY_PREFIXES."""
    from nes.core.identifiers.validators import validate_entity_id

    with pytest.raises(ValueError, match=r"not.*allowed|unknown|unsupported|invalid"):
        validate_entity_id("entity:organization/unknown_category/some-org")


def test_validate_unknown_top_level_type_raises():
    """validate_entity_id raises ValueError for an unknown top-level type."""
    from nes.core.identifiers.validators import validate_entity_id

    with pytest.raises(ValueError):
        validate_entity_id("entity:unicorn/rabi-lamichhane")


def test_validate_prefix_exceeding_max_depth_raises():
    """validate_entity_id raises ValueError when prefix depth exceeds MAX_PREFIX_DEPTH."""
    from nes.core.identifiers.validators import validate_entity_id

    with pytest.raises(ValueError):
        validate_entity_id("entity:a/b/c/d/some-slug")


def test_validate_relationship_id_valid():
    """Test validating valid relationship IDs."""
    from nes.core.identifiers.validators import (
        is_valid_relationship_id,
        validate_relationship_id,
    )

    rel_id = "relationship:person/ram-chandra-poudel:organization/political_party/nepali-congress:MEMBER_OF"
    assert is_valid_relationship_id(rel_id)
    assert validate_relationship_id(rel_id) == rel_id


def test_validate_version_id_valid():
    """Test validating valid version IDs."""
    from nes.core.identifiers.validators import is_valid_version_id, validate_version_id

    version_id = "version:entity:person/ram-chandra-poudel:1"
    assert is_valid_version_id(version_id)
    assert validate_version_id(version_id) == version_id


def test_validate_author_id_valid():
    """Test validating valid author IDs."""
    from nes.core.identifiers.validators import is_valid_author_id, validate_author_id

    author_id = "author:csv-importer"
    assert is_valid_author_id(author_id)
    assert validate_author_id(author_id) == author_id

    # Invalid slug (too short)
    assert not is_valid_author_id("author:ab")
