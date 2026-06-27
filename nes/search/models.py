"""Query and result models for the search module.

These dataclasses form the backend-agnostic contract between the
``SearchService``/API layer and the concrete :class:`SearchBackend`
implementations (in-process fallback and OpenSearch).

They are intentionally plain dataclasses (not Pydantic models) so that
``SearchQuery`` can be hashable/frozen for caching and so the search
package has no hard dependency on the API layer.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

# Scalar values accepted as attribute filter values.
AttrValue = Union[str, int, float, bool]

# Canonical relevance boost ladder for full-text search, shared by both
# backends so their ranking stays aligned (the contract tests assert parity).
# Higher weight = stronger contribution to the score. Keep this as the single
# source of truth; the OpenSearch mapping and the in-process scorer both
# consume it.
FIELD_WEIGHTS: Tuple[Tuple[str, float], ...] = (
    ("name_primary_en", 10.0),
    ("name_primary_ne", 10.0),
    ("name_alias_en", 5.0),
    ("name_alias_ne", 5.0),
    ("name_translit_roman", 4.0),
    ("name_translit_devanagari", 4.0),
    ("identifier_names", 2.0),
    ("slug", 2.0),
    ("short_description_en", 1.5),
    ("short_description_ne", 1.5),
    ("description_en", 1.0),
    ("description_ne", 1.0),
)


@dataclass(frozen=True)
class SearchQuery:
    """A normalized, backend-agnostic entity search request.

    Attributes:
        query: Free-text query matched across multiple fields. ``None`` or
            empty means "match everything" (filter-only listing).
        entity_type: Optional ``type`` filter (e.g. ``person``).
        sub_type: Optional ``sub_type`` filter.
        entity_prefix: Optional N-level prefix filter using startswith
            semantics (e.g. ``organization/nepal_govt`` matches children).
        attributes: Attribute equality filters combined with AND logic.
        tags: Tag filters combined with AND logic (entity must have ALL).
        limit: Maximum number of hits to return.
        offset: Number of leading hits to skip (pagination).
        fuzzy: When True, allow typo-tolerant matching. When False, only
            exact/prefix/token matches are considered.
        highlight: When True, backends that support it return matched
            snippets per hit.
    """

    query: Optional[str] = None
    entity_type: Optional[str] = None
    sub_type: Optional[str] = None
    entity_prefix: Optional[str] = None
    attributes: Optional[Tuple[Tuple[str, AttrValue], ...]] = None
    tags: Optional[Tuple[str, ...]] = None
    limit: int = 100
    offset: int = 0
    fuzzy: bool = True
    highlight: bool = False

    @classmethod
    def build(
        cls,
        query: Optional[str] = None,
        entity_type: Optional[str] = None,
        sub_type: Optional[str] = None,
        entity_prefix: Optional[str] = None,
        attributes: Optional[Dict[str, AttrValue]] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0,
        fuzzy: bool = True,
        highlight: bool = False,
    ) -> "SearchQuery":
        """Construct a SearchQuery from the loose dict/list shapes the API uses.

        Normalizes ``attributes`` (dict) and ``tags`` (list) into hashable
        tuples so the resulting query is frozen/hashable and safe to cache.
        """
        attrs: Optional[Tuple[Tuple[str, AttrValue], ...]] = None
        if attributes:
            attrs = tuple(sorted(attributes.items()))

        tags_tuple: Optional[Tuple[str, ...]] = None
        if tags:
            cleaned = [t for t in tags if t]
            if cleaned:
                tags_tuple = tuple(cleaned)

        return cls(
            query=query or None,
            entity_type=entity_type,
            sub_type=sub_type,
            entity_prefix=entity_prefix,
            attributes=attrs,
            tags=tags_tuple,
            limit=limit,
            offset=offset,
            fuzzy=fuzzy,
            highlight=highlight,
        )

    @property
    def attributes_dict(self) -> Optional[Dict[str, AttrValue]]:
        """Return attribute filters as a plain dict (or None)."""
        if self.attributes is None:
            return None
        return dict(self.attributes)

    @property
    def tags_list(self) -> Optional[List[str]]:
        """Return tag filters as a plain list (or None)."""
        if self.tags is None:
            return None
        return list(self.tags)


@dataclass
class SearchHit:
    """A single search result.

    Attributes:
        entity_id: The matched entity's canonical ID.
        score: Relevance score (higher is better). Comparable only within a
            single backend/query, not across backends.
        source: The indexed document for the hit. Useful for debugging and as
            a fallback payload; the API re-hydrates the canonical entity from
            the database using ``entity_id``.
        highlights: Optional per-field matched snippets (when requested and
            supported by the backend).
    """

    entity_id: str
    score: float
    source: Dict[str, Any] = field(default_factory=dict)
    highlights: Optional[Dict[str, List[str]]] = None


@dataclass
class SearchResults:
    """The result of a search.

    Attributes:
        hits: Ordered list of hits for the requested page.
        total: Accurate count of ALL matching entities (not just this page).
            This is what lets the API report an honest ``total``.
    """

    hits: List[SearchHit] = field(default_factory=list)
    total: int = 0

    @property
    def entity_ids(self) -> List[str]:
        """Return the ordered entity IDs for this page of hits."""
        return [h.entity_id for h in self.hits]
