"""Unit tests for OpenSearch mapping + query construction.

These run without an OpenSearch instance: they validate the pure functions that
build index settings/mappings and translate a SearchQuery into a request body,
plus the backend's deep-pagination guard (using a stub client).
"""

import pytest

from nes.search.models import SearchQuery
from nes.search.opensearch.backend import OpenSearchBackend
from nes.search.opensearch.mapping import (
    MAX_RESULT_WINDOW,
    build_query_body,
    index_mappings,
    index_settings,
)


class TestIndexDefinition:
    def test_settings_have_analyzers(self):
        settings = index_settings(use_icu=True)
        analyzers = settings["analysis"]["analyzer"]
        assert "en_text" in analyzers
        assert "ne_text" in analyzers
        assert "prefix_index" in analyzers
        assert (
            settings["analysis"]["analyzer"]["ne_text"]["tokenizer"] == "icu_tokenizer"
        )

    def test_settings_without_icu_fall_back(self):
        settings = index_settings(use_icu=False)
        assert settings["analysis"]["analyzer"]["ne_text"]["tokenizer"] == "standard"

    def test_mappings_cover_searchable_fields(self):
        props = index_mappings()["properties"]
        for field in [
            "name_primary_en",
            "name_primary_ne",
            "name_alias_en",
            "name_translit_roman",
            "identifiers",
            "tags",
            "entity_prefix_path",
            "attributes",
        ]:
            assert field in props
        # Names carry a prefix subfield for as-you-type.
        assert "prefix" in props["name_primary_en"]["fields"]


class TestQueryBody:
    def test_match_all_when_no_query(self):
        body = build_query_body(SearchQuery.build(limit=10, offset=5))
        assert body["from"] == 5
        assert body["size"] == 10
        assert body["track_total_hits"] is True
        assert "match_all" in body["query"]

    def test_filter_only_query(self):
        body = build_query_body(
            SearchQuery.build(entity_type="person", tags=["politician"])
        )
        filters = body["query"]["bool"]["filter"]
        assert {"term": {"type": "person"}} in filters
        assert {"term": {"tags": "politician"}} in filters

    def test_fulltext_query_includes_fuzzy(self):
        body = build_query_body(SearchQuery.build(query="poudel", fuzzy=True))
        should = body["query"]["bool"]["should"]
        multi = [s for s in should if "multi_match" in s][0]["multi_match"]
        assert multi["fuzziness"] == "AUTO"
        assert body["track_total_hits"] is True

    def test_fulltext_query_without_fuzzy(self):
        body = build_query_body(SearchQuery.build(query="poudel", fuzzy=False))
        should = body["query"]["bool"]["should"]
        best = [
            s["multi_match"]
            for s in should
            if s.get("multi_match", {}).get("type") == "best_fields"
        ][0]
        assert "fuzziness" not in best

    def test_prefix_clause_present_for_devanagari(self):
        # Devanagari name fields now carry a `.prefix` subfield, so as-you-type
        # prefix matching applies to Devanagari queries too.
        body = build_query_body(SearchQuery.build(query="पौडेल"))
        should = body["query"]["bool"]["should"]
        types = [s.get("multi_match", {}).get("type") for s in should]
        assert "bool_prefix" in types

    def test_identifier_term_is_lowercased(self):
        # identifiers field uses a lowercase normalizer; the term query must
        # lowercase the input to match case-insensitively.
        body = build_query_body(SearchQuery.build(query="ABC123"))
        should = body["query"]["bool"]["should"]
        ident_terms = [
            s["term"]["identifiers"]["value"]
            for s in should
            if "term" in s and "identifiers" in s.get("term", {})
        ]
        assert ident_terms == ["abc123"]

    def test_entity_prefix_uses_ancestor_term(self):
        body = build_query_body(
            SearchQuery.build(query="x", entity_prefix="organization/political_party")
        )
        filters = body["query"]["bool"]["filter"]
        assert {
            "term": {"entity_prefix_path": "organization/political_party"}
        } in filters


class TestPaginationGuard:
    @pytest.mark.asyncio
    async def test_deep_pagination_raises_value_error(self):
        # No real client needed: the guard runs before any client call.
        backend = OpenSearchBackend(client=object(), index="test")
        query = SearchQuery.build(query="x", offset=MAX_RESULT_WINDOW, limit=1000)
        with pytest.raises(ValueError, match="Pagination window too large"):
            await backend.search(query)

    @pytest.mark.asyncio
    async def test_within_window_does_not_raise_guard(self):
        # offset+limit just under the window passes the guard (then would call
        # the client, which we don't stub here — assert only the guard).
        backend = OpenSearchBackend(client=object(), index="test")
        query = SearchQuery.build(query="x", offset=MAX_RESULT_WINDOW - 100, limit=100)
        # The guard allows it; the subsequent client.search on a bare object()
        # raises AttributeError, proving we got past the ValueError guard.
        with pytest.raises(AttributeError):
            await backend.search(query)
