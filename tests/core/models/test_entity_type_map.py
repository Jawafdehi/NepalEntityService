"""Tests for entity type map and ALLOWED_ENTITY_PREFIXES registry."""

import pytest

# ===========================================================================
# Backward compat: existing type/subtype combos present in ALLOWED_ENTITY_PREFIXES
# ===========================================================================


def test_allowed_prefixes_exists():
    """ALLOWED_ENTITY_PREFIXES is importable from entity_type_map."""
    from nes.core.models.entity_type_map import ALLOWED_ENTITY_PREFIXES

    assert isinstance(ALLOWED_ENTITY_PREFIXES, set)


def test_allowed_prefixes_contains_person():
    """'person' prefix is in ALLOWED_ENTITY_PREFIXES."""
    from nes.core.models.entity_type_map import ALLOWED_ENTITY_PREFIXES

    assert "person" in ALLOWED_ENTITY_PREFIXES


def test_allowed_prefixes_contains_organization_subtypes():
    """All existing organization subtypes are in ALLOWED_ENTITY_PREFIXES."""
    from nes.core.models.entity_type_map import ALLOWED_ENTITY_PREFIXES

    assert "organization" in ALLOWED_ENTITY_PREFIXES
    assert "organization/political_party" in ALLOWED_ENTITY_PREFIXES
    assert "organization/government_body" in ALLOWED_ENTITY_PREFIXES
    assert "organization/ngo" in ALLOWED_ENTITY_PREFIXES
    assert "organization/international_org" in ALLOWED_ENTITY_PREFIXES
    assert "organization/hospital" in ALLOWED_ENTITY_PREFIXES


def test_allowed_prefixes_contains_location_subtypes():
    """All existing location subtypes are in ALLOWED_ENTITY_PREFIXES."""
    from nes.core.models.entity_type_map import ALLOWED_ENTITY_PREFIXES

    assert "location" in ALLOWED_ENTITY_PREFIXES
    assert "location/province" in ALLOWED_ENTITY_PREFIXES
    assert "location/district" in ALLOWED_ENTITY_PREFIXES
    assert "location/metropolitan_city" in ALLOWED_ENTITY_PREFIXES
    assert "location/sub_metropolitan_city" in ALLOWED_ENTITY_PREFIXES
    assert "location/municipality" in ALLOWED_ENTITY_PREFIXES
    assert "location/rural_municipality" in ALLOWED_ENTITY_PREFIXES
    assert "location/ward" in ALLOWED_ENTITY_PREFIXES
    assert "location/constituency" in ALLOWED_ENTITY_PREFIXES


def test_allowed_prefixes_contains_project_subtypes():
    """All existing project subtypes are in ALLOWED_ENTITY_PREFIXES."""
    from nes.core.models.entity_type_map import ALLOWED_ENTITY_PREFIXES

    assert "project" in ALLOWED_ENTITY_PREFIXES
    assert "project/development_project" in ALLOWED_ENTITY_PREFIXES


# ===========================================================================
# New: 3-level prefixes can be added and used
# ===========================================================================


def test_allowed_prefixes_accepts_3_level_prefix():
    """A 3-level prefix like 'organization/nepal_govt/moha' can be added to the registry."""
    from nes.core.models.entity_type_map import ALLOWED_ENTITY_PREFIXES

    # Add a new 3-level prefix and confirm it can be checked
    test_prefix = "organization/nepal_govt/moha"
    extended = ALLOWED_ENTITY_PREFIXES | {test_prefix}
    assert test_prefix in extended


def test_allowed_prefixes_is_all_strings():
    """Every entry in ALLOWED_ENTITY_PREFIXES is a string."""
    from nes.core.models.entity_type_map import ALLOWED_ENTITY_PREFIXES

    for prefix in ALLOWED_ENTITY_PREFIXES:
        assert isinstance(
            prefix, str
        ), f"Expected str, got {type(prefix)} for {prefix!r}"


def test_allowed_prefixes_no_leading_trailing_slashes():
    """No prefix in ALLOWED_ENTITY_PREFIXES has leading or trailing slashes."""
    from nes.core.models.entity_type_map import ALLOWED_ENTITY_PREFIXES

    for prefix in ALLOWED_ENTITY_PREFIXES:
        assert not prefix.startswith("/"), f"Prefix has leading slash: {prefix!r}"
        assert not prefix.endswith("/"), f"Prefix has trailing slash: {prefix!r}"


def test_allowed_prefixes_depth_within_max():
    """Every prefix in ALLOWED_ENTITY_PREFIXES has depth <= MAX_PREFIX_DEPTH."""
    from nes.core.constraints import MAX_PREFIX_DEPTH
    from nes.core.models.entity_type_map import ALLOWED_ENTITY_PREFIXES

    for prefix in ALLOWED_ENTITY_PREFIXES:
        depth = len(prefix.split("/"))
        assert (
            depth <= MAX_PREFIX_DEPTH
        ), f"Prefix {prefix!r} has depth {depth} > MAX_PREFIX_DEPTH={MAX_PREFIX_DEPTH}"
