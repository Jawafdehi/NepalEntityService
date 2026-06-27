"""Backend contract suite.

These tests assert the behavioral contract every :class:`SearchBackend` must
satisfy: multi-field matching, prefix, fuzzy/typo tolerance, filtering, accurate
totals, pagination, and delete. They run against the in-process backend always,
and against the OpenSearch backend when ``OPENSEARCH_URL`` is set in the
environment (skipped otherwise).

The suite asserts ordering/recall *properties*, not exact scores, so the two
backends can differ in scoring detail while still being correct.
"""

import os

import pytest
import pytest_asyncio

from nes.search.document import EntityDocumentBuilder
from nes.search.fallback import InProcessSearchBackend
from nes.search.models import SearchQuery


def _backend_params():
    params = [pytest.param("inprocess", id="inprocess")]
    if os.getenv("OPENSEARCH_URL"):
        params.append(pytest.param("opensearch", id="opensearch"))
    return params


@pytest_asyncio.fixture(params=_backend_params())
async def backend(request):
    if request.param == "inprocess":
        be = InProcessSearchBackend()
        await be.ensure_index()
        yield be
        return

    # OpenSearch path: use an isolated, per-test index, and clean it up.
    from nes.search.opensearch.backend import OpenSearchBackend

    index = "nes-entities-contract-test"
    be = OpenSearchBackend.from_env(url=os.environ["OPENSEARCH_URL"], index=index)
    await be.delete_index()
    await be.ensure_index()
    try:
        yield be
    finally:
        await be.delete_index()
        await be.close()


@pytest.fixture
def builder():
    return EntityDocumentBuilder()


async def _index_entities(backend, make_entity, builder, specs):
    """Create entities from specs, index them, and refresh if needed."""
    entities = []
    for prefix, data in specs:
        entity = await make_entity(prefix, data)
        await backend.index(builder.build(entity))
        entities.append(entity)
    # OpenSearch is near-real-time; force a refresh so docs are searchable.
    refresh = getattr(backend, "refresh", None)
    if refresh:
        await refresh()
    return entities


PERSON_SPECS = [
    (
        "person",
        {
            "slug": "ram-chandra-poudel",
            "names": [
                {
                    "kind": "PRIMARY",
                    "en": {"full": "Ram Chandra Poudel", "family": "Poudel"},
                    "ne": {"full": "राम चन्द्र पौडेल"},
                }
            ],
            "tags": ["politician"],
            "identifiers": [{"scheme": "other", "value": "333745"}],
        },
    ),
    (
        "person",
        {
            "slug": "sher-bahadur-deuba",
            "names": [{"kind": "PRIMARY", "en": {"full": "Sher Bahadur Deuba"}}],
            "tags": ["politician"],
        },
    ),
    (
        "organization/political_party",
        {
            "slug": "nepali-congress",
            "names": [{"kind": "PRIMARY", "en": {"full": "Nepali Congress"}}],
        },
    ),
]


@pytest.mark.asyncio
class TestBackendContract:
    async def test_exact_name_match(self, backend, make_entity, builder):
        await _index_entities(backend, make_entity, builder, PERSON_SPECS)
        res = await backend.search(SearchQuery.build(query="poudel"))
        assert res.total == 1
        assert res.hits[0].entity_id == "entity:person/ram-chandra-poudel"

    async def test_prefix_match(self, backend, make_entity, builder):
        await _index_entities(backend, make_entity, builder, PERSON_SPECS)
        # "ram" is a prefix of "Ram" in the primary name.
        res = await backend.search(SearchQuery.build(query="ram"))
        ids = [h.entity_id for h in res.hits]
        assert "entity:person/ram-chandra-poudel" in ids

    async def test_fuzzy_typo_match(self, backend, make_entity, builder):
        await _index_entities(backend, make_entity, builder, PERSON_SPECS)
        # "paudel" is a common misspelling of "Poudel".
        res = await backend.search(SearchQuery.build(query="paudel", fuzzy=True))
        ids = [h.entity_id for h in res.hits]
        assert "entity:person/ram-chandra-poudel" in ids

    async def test_fuzzy_off_excludes_typo(self, backend, make_entity, builder):
        await _index_entities(backend, make_entity, builder, PERSON_SPECS)
        res = await backend.search(SearchQuery.build(query="paudel", fuzzy=False))
        ids = [h.entity_id for h in res.hits]
        assert "entity:person/ram-chandra-poudel" not in ids

    async def test_identifier_value_match(self, backend, make_entity, builder):
        await _index_entities(backend, make_entity, builder, PERSON_SPECS)
        res = await backend.search(SearchQuery.build(query="333745"))
        ids = [h.entity_id for h in res.hits]
        assert "entity:person/ram-chandra-poudel" in ids

    async def test_type_filter(self, backend, make_entity, builder):
        await _index_entities(backend, make_entity, builder, PERSON_SPECS)
        res = await backend.search(SearchQuery.build(entity_type="organization"))
        assert res.total == 1
        assert res.hits[0].entity_id.startswith("entity:organization/")

    async def test_prefix_filter(self, backend, make_entity, builder):
        await _index_entities(backend, make_entity, builder, PERSON_SPECS)
        res = await backend.search(SearchQuery.build(entity_prefix="organization"))
        assert res.total == 1

    async def test_tag_filter(self, backend, make_entity, builder):
        await _index_entities(backend, make_entity, builder, PERSON_SPECS)
        res = await backend.search(SearchQuery.build(tags=["politician"]))
        assert res.total == 2

    async def test_pagination_and_total(self, backend, make_entity, builder):
        await _index_entities(backend, make_entity, builder, PERSON_SPECS)
        # No query -> match all; total reflects ALL matches, not the page.
        page1 = await backend.search(SearchQuery.build(limit=2, offset=0))
        assert page1.total == 3
        assert len(page1.hits) == 2
        page2 = await backend.search(SearchQuery.build(limit=2, offset=2))
        assert page2.total == 3
        assert len(page2.hits) == 1

    async def test_delete_removes(self, backend, make_entity, builder):
        await _index_entities(backend, make_entity, builder, PERSON_SPECS)
        removed = await backend.delete("entity:person/ram-chandra-poudel")
        assert removed is True
        refresh = getattr(backend, "refresh", None)
        if refresh:
            await refresh()
        res = await backend.search(SearchQuery.build(query="poudel"))
        assert res.total == 0

    async def test_cross_script_devanagari_query(self, backend, make_entity, builder):
        await _index_entities(backend, make_entity, builder, PERSON_SPECS)
        # Querying the Devanagari name should find the entity.
        res = await backend.search(SearchQuery.build(query="पौडेल"))
        ids = [h.entity_id for h in res.hits]
        assert "entity:person/ram-chandra-poudel" in ids
