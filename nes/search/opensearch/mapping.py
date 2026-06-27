"""OpenSearch index settings, mappings, and query construction.

Everything that defines *how* documents are analyzed, stored, and queried lives
here so the backend module stays thin. The document shape matches
:class:`nes.search.document.EntityDocumentBuilder` output.

Analyzers:
- ``en_text``  -- standard tokenizer + lowercase + asciifolding. Asciifolding
  folds diacritics so e.g. accented variants normalize.
- ``ne_text``  -- ICU normalization + tokenization for Devanagari when the
  ``analysis-icu`` plugin is present; the index falls back to the standard
  analyzer otherwise (Devanagari is whitespace-tokenized acceptably).
- ``prefix_index`` / ``prefix_search`` -- edge-ngram pair for as-you-type
  prefix matching on name fields, bounded to keep the index small.

Boost ladder (mirrored by the in-process backend):
    primary names ^10 > aliases ^5 > transliterations ^4 > misspellings ^3
    > slug/identifier_names ^2 > short_description ^1.5 > description ^1
Exact (``*.exact``) and prefix (``*.prefix``) clauses are higher-boosted and
non-fuzzy so exact/prefix matches always outrank fuzzy matches.
"""

from typing import Any, Dict, List

from nes.search.models import FIELD_WEIGHTS, SearchQuery

DEFAULT_INDEX = "nes-entities"

# OpenSearch rejects from + size beyond index.max_result_window (default 10000).
# We guard against this before querying so callers get a clear 400 rather than
# an opaque engine error. Deep pagination past this point needs search_after.
MAX_RESULT_WINDOW = 10000


def index_settings(use_icu: bool = True) -> Dict[str, Any]:
    """Return index settings with analyzers. ``use_icu`` toggles the ICU plugin."""
    ne_analyzer: Dict[str, Any]
    filters_ne: List[str]
    if use_icu:
        ne_analyzer = {
            "type": "custom",
            "tokenizer": "icu_tokenizer",
            "filter": ["icu_normalizer", "lowercase"],
        }
    else:
        ne_analyzer = {
            "type": "custom",
            "tokenizer": "standard",
            "filter": ["lowercase"],
        }

    return {
        "index": {
            # Single-node friendly defaults; tune for production cluster.
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "max_ngram_diff": 14,
        },
        "analysis": {
            "filter": {
                "edge_ngram_filter": {
                    "type": "edge_ngram",
                    "min_gram": 1,
                    "max_gram": 15,
                }
            },
            "normalizer": {
                # Case-insensitive keyword matching (e.g. identifiers/handles),
                # consistent with the in-process backend's lowercased compare.
                "lowercase_normalizer": {
                    "type": "custom",
                    "filter": ["lowercase"],
                }
            },
            "analyzer": {
                "en_text": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "asciifolding"],
                },
                "ne_text": ne_analyzer,
                "prefix_index": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "asciifolding", "edge_ngram_filter"],
                },
                "prefix_search": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "asciifolding"],
                },
            },
        },
    }


def _en_field() -> Dict[str, Any]:
    """English text field with exact + prefix subfields."""
    return {
        "type": "text",
        "analyzer": "en_text",
        "fields": {
            "exact": {"type": "keyword"},
            "prefix": {
                "type": "text",
                "analyzer": "prefix_index",
                "search_analyzer": "prefix_search",
            },
        },
    }


def _ne_field() -> Dict[str, Any]:
    """Devanagari text field with exact + prefix subfields.

    The ``.prefix`` subfield mirrors :func:`_en_field` so as-you-type prefix
    matching works for Devanagari names too (the prefix analyzers are
    script-agnostic: they tokenize on whitespace and edge-ngram the tokens).
    """
    return {
        "type": "text",
        "analyzer": "ne_text",
        "fields": {
            "exact": {"type": "keyword"},
            "prefix": {
                "type": "text",
                "analyzer": "prefix_index",
                "search_analyzer": "prefix_search",
            },
        },
    }


def index_mappings() -> Dict[str, Any]:
    """Return the field mappings for the entity index."""
    return {
        "dynamic": False,
        "properties": {
            "id": {"type": "keyword"},
            "type": {"type": "keyword"},
            "sub_type": {"type": "keyword"},
            "entity_prefix": {"type": "keyword"},
            "entity_prefix_path": {"type": "keyword"},
            "slug": {
                "type": "text",
                "analyzer": "en_text",
                "fields": {"exact": {"type": "keyword"}},
            },
            "name_primary_en": _en_field(),
            "name_primary_ne": _ne_field(),
            "name_alias_en": _en_field(),
            "name_alias_ne": _ne_field(),
            "name_translit_roman": _en_field(),
            "name_translit_devanagari": _ne_field(),
            "identifiers": {
                "type": "keyword",
                "normalizer": "lowercase_normalizer",
            },
            "identifier_names": {"type": "text", "analyzer": "en_text"},
            "tags": {"type": "keyword"},
            "short_description_en": {"type": "text", "analyzer": "en_text"},
            "short_description_ne": {"type": "text", "analyzer": "ne_text"},
            "description_en": {"type": "text", "analyzer": "en_text"},
            "description_ne": {"type": "text", "analyzer": "ne_text"},
            # OpenSearch's flat_object indexes arbitrary nested keys without a
            # mapping explosion; used for attribute equality filters only.
            "attributes": {"type": "flat_object"},
        },
    }


# Field boosts for the full-text query, shared with the in-process backend via
# the canonical ladder. Devanagari and Roman name fields are searched together;
# the analyzer picks the right tokenization per field.
_FULLTEXT_FIELDS = FIELD_WEIGHTS

# Name fields that also carry a `.prefix` subfield for as-you-type matching.
_PREFIX_FIELDS = [
    "name_primary_en^8",
    "name_primary_ne^8",
    "name_alias_en^4",
    "name_alias_ne^4",
    "name_translit_roman^3",
]


def build_query_body(query: SearchQuery) -> Dict[str, Any]:
    """Translate a :class:`SearchQuery` into an OpenSearch request body."""
    filters = _build_filters(query)

    if not query.query:
        # Filter-only listing; constant score, stable order by id.
        bool_query: Dict[str, Any] = {"filter": filters} if filters else {}
        body: Dict[str, Any] = {
            "query": {"bool": bool_query} if bool_query else {"match_all": {}},
            "from": query.offset,
            "size": query.limit,
            "track_total_hits": True,
            "sort": ["_doc"],
        }
        return body

    text = query.query
    should: List[Dict[str, Any]] = []

    # Token/full-text match across all weighted fields (fuzzy optional).
    multi_match: Dict[str, Any] = {
        "query": text,
        "type": "best_fields",
        "fields": [f"{name}^{boost}" for name, boost in _FULLTEXT_FIELDS],
    }
    if query.fuzzy:
        multi_match.update(
            {"fuzziness": "AUTO", "prefix_length": 1, "max_expansions": 50}
        )
    should.append({"multi_match": multi_match})

    # Higher-boosted exact phrase match (non-fuzzy) so exact wins.
    should.append(
        {
            "multi_match": {
                "query": text,
                "type": "phrase",
                "fields": [f"{name}^{boost * 2}" for name, boost in _FULLTEXT_FIELDS],
            }
        }
    )

    # As-you-type prefix match on name fields. The `.prefix` subfields exist on
    # both en and ne name fields and are script-agnostic, so this works for
    # Devanagari input too.
    should.append(
        {
            "multi_match": {
                "query": text,
                "type": "bool_prefix",
                "fields": [f"{f}.prefix" for f in _strip_boost(_PREFIX_FIELDS)],
            }
        }
    )

    # Exact identifier value (e.g. an ID number or social handle). The
    # identifiers field is normalized to lowercase, so match case-insensitively.
    should.append({"term": {"identifiers": {"value": text.lower(), "boost": 12.0}}})

    bool_query = {"should": should, "minimum_should_match": 1}
    if filters:
        bool_query["filter"] = filters

    return {
        "query": {"bool": bool_query},
        "from": query.offset,
        "size": query.limit,
        "track_total_hits": True,
    }


def _strip_boost(fields: List[str]) -> List[str]:
    """Drop ``^boost`` suffixes; prefix matching uses its own field boosts."""
    return [f.split("^", 1)[0] for f in fields]


def _build_filters(query: SearchQuery) -> List[Dict[str, Any]]:
    """Build the non-scoring filter clauses for a query."""
    filters: List[Dict[str, Any]] = []
    if query.entity_type:
        filters.append({"term": {"type": query.entity_type}})
    if query.sub_type:
        filters.append({"term": {"sub_type": query.sub_type}})
    if query.entity_prefix:
        # Exact startswith via the precomputed ancestor list.
        filters.append({"term": {"entity_prefix_path": query.entity_prefix}})
    if query.tags:
        # AND semantics: one term filter per tag.
        for tag in query.tags:
            filters.append({"term": {"tags": tag}})
    if query.attributes:
        for key, value in query.attributes:
            filters.append({"term": {f"attributes.{key}": value}})
    return filters
