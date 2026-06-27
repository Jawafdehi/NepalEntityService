"""Tests for EntityDocumentBuilder -> searchable document conversion."""

import pytest

from nes.search.document import (
    EntityDocumentBuilder,
    _flatten_attributes,
    _prefix_ancestors,
)


@pytest.fixture
def builder():
    return EntityDocumentBuilder()


class TestPrefixHelpers:
    def test_prefix_ancestors_expands(self):
        assert _prefix_ancestors("organization/nepal_govt/moha") == [
            "organization",
            "organization/nepal_govt",
            "organization/nepal_govt/moha",
        ]

    def test_prefix_ancestors_single(self):
        assert _prefix_ancestors("person") == ["person"]

    def test_prefix_ancestors_none(self):
        assert _prefix_ancestors(None) == []


class TestFlattenAttributes:
    def test_flatten_nested_scalars(self):
        flat = _flatten_attributes({"a": {"b": "x", "c": 1}, "d": True})
        assert flat == {"a.b": "x", "a.c": 1, "d": True}

    def test_flatten_drops_lists(self):
        flat = _flatten_attributes({"a": [1, 2, 3], "b": "keep"})
        assert flat == {"b": "keep"}

    def test_flatten_empty(self):
        assert _flatten_attributes(None) == {}


class TestDocumentBuilder:
    @pytest.mark.asyncio
    async def test_primary_name_indexed(self, builder, make_entity):
        entity = await make_entity(
            "person",
            {
                "slug": "ram-chandra-poudel",
                "names": [
                    {
                        "kind": "PRIMARY",
                        "en": {
                            "full": "Ram Chandra Poudel",
                            "given": "Ram Chandra",
                            "family": "Poudel",
                        },
                        "ne": {"full": "राम चन्द्र पौडेल"},
                    }
                ],
            },
        )
        doc = builder.build(entity)

        assert doc["id"] == entity.id
        assert doc["type"] == "person"
        assert doc["entity_prefix"] == "person"
        assert doc["entity_prefix_path"] == ["person"]
        assert "Ram Chandra Poudel" in doc["name_primary_en"]
        # Variants from extract_name_variants are added.
        assert "Poudel" in doc["name_primary_en"]
        assert "राम चन्द्र पौडेल" in doc["name_primary_ne"]
        # Devanagari primary name produces a romanized cross-script form.
        assert doc["name_translit_roman"]

    @pytest.mark.asyncio
    async def test_alias_and_misspelled_names(self, builder, make_entity):
        entity = await make_entity(
            "person",
            {
                "slug": "kp-oli",
                "names": [
                    {"kind": "PRIMARY", "en": {"full": "KP Sharma Oli"}},
                    {"kind": "ALIAS", "en": {"full": "Khadga Prasad Oli"}},
                ],
                "misspelled_names": [
                    {"kind": "ALTERNATE", "en": {"full": "K P Olee"}},
                ],
            },
        )
        doc = builder.build(entity)

        assert "KP Sharma Oli" in doc["name_primary_en"]
        assert "Khadga Prasad Oli" in doc["name_alias_en"]
        assert "K P Olee" in doc["name_alias_en"]
        # Aliases must not leak into the primary bucket.
        assert "Khadga Prasad Oli" not in doc["name_primary_en"]

    @pytest.mark.asyncio
    async def test_identifiers_tags_descriptions(self, builder, make_entity):
        entity = await make_entity(
            "person",
            {
                "slug": "test-ident",
                "names": [{"kind": "PRIMARY", "en": {"full": "Test Person"}}],
                "tags": ["politician", "federal-election-2079-candidate"],
                "identifiers": [
                    {"scheme": "other", "value": "333745"},
                    {"scheme": "twitter", "value": "@testperson"},
                ],
                "short_description": {"en": {"value": "A test politician"}},
            },
        )
        doc = builder.build(entity)

        assert "333745" in doc["identifiers"]
        assert "@testperson" in doc["identifiers"]
        assert "politician" in doc["tags"]
        assert doc["short_description_en"] == "A test politician"

    @pytest.mark.asyncio
    async def test_subtype_prefix_path(self, builder, make_entity):
        entity = await make_entity(
            "organization/political_party",
            {
                "slug": "nepali-congress",
                "names": [{"kind": "PRIMARY", "en": {"full": "Nepali Congress"}}],
            },
        )
        doc = builder.build(entity)
        assert doc["entity_prefix"] == "organization/political_party"
        assert doc["entity_prefix_path"] == [
            "organization",
            "organization/political_party",
        ]
