"""Pure-Python in-process search backend.

This backend keeps documents in a dict and scores them in Python. It exists so
that:

- local development and the full test-suite run with no external engine, and
- the API can *gracefully degrade* to it when OpenSearch is unavailable.

It is not meant to match OpenSearch scores exactly or to scale to a million
documents; it implements the same :class:`SearchBackend` contract (multi-field
matching, prefix, fuzzy/typo tolerance, ranking, filters, accurate totals) so
the contract test-suite can validate both backends identically.
"""

import re
from difflib import SequenceMatcher
from typing import Any, Dict, Iterable, List, Optional, Tuple

from nes.search.backend import SearchBackend
from nes.search.models import FIELD_WEIGHTS, SearchHit, SearchQuery, SearchResults

# Shared canonical boost ladder (see nes.search.models.FIELD_WEIGHTS) keeps the
# in-process scorer aligned with the OpenSearch field boosts.
_TEXT_FIELD_WEIGHTS = FIELD_WEIGHTS

_FUZZY_THRESHOLD = 0.82  # min SequenceMatcher ratio to count as a typo match
_TOKEN_RE = re.compile(r"[^\wऀ-ॿ]+", re.UNICODE)


def _tokenize(text: str) -> List[str]:
    """Lowercase and split text into word tokens (Latin + Devanagari aware)."""
    if not text:
        return []
    return [t for t in _TOKEN_RE.split(text.lower()) if t]


def _field_texts(value: Any) -> List[str]:
    """Coerce a document field value into a list of strings."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [v for v in value if isinstance(v, str)]
    return []


class InProcessSearchBackend(SearchBackend):
    """A dict-backed, Python-scored implementation of :class:`SearchBackend`."""

    def __init__(self) -> None:
        self._docs: Dict[str, Dict[str, Any]] = {}

    async def ensure_index(self) -> None:
        return None

    async def health(self) -> bool:
        return True

    async def index(self, doc: Dict[str, Any]) -> None:
        entity_id = doc.get("id")
        if not entity_id:
            raise ValueError("document is missing required 'id' field")
        self._docs[entity_id] = doc

    async def index_bulk(self, docs: Iterable[Dict[str, Any]]) -> int:
        count = 0
        for doc in docs:
            await self.index(doc)
            count += 1
        return count

    async def delete(self, entity_id: str) -> bool:
        return self._docs.pop(entity_id, None) is not None

    async def search(self, query: SearchQuery) -> SearchResults:
        tokens = _tokenize(query.query) if query.query else []

        scored: List[Tuple[float, str, Dict[str, Any]]] = []
        for entity_id, doc in self._docs.items():
            if not self._passes_filters(doc, query):
                continue
            if not tokens:
                # Filter-only listing: everyone who passes filters matches.
                scored.append((0.0, entity_id, doc))
                continue
            score = self._score(doc, tokens, query.fuzzy)
            if score > 0:
                scored.append((score, entity_id, doc))

        # Stable ordering: score desc, then entity_id for determinism.
        scored.sort(key=lambda item: (-item[0], item[1]))

        total = len(scored)
        page = scored[query.offset : query.offset + query.limit]
        hits = [
            SearchHit(entity_id=eid, score=score, source=doc)
            for score, eid, doc in page
        ]
        return SearchResults(hits=hits, total=total)

    # ------------------------------------------------------------------ #
    # Filtering
    # ------------------------------------------------------------------ #

    def _passes_filters(self, doc: Dict[str, Any], query: SearchQuery) -> bool:
        if query.entity_type and doc.get("type") != query.entity_type:
            return False
        if query.sub_type and doc.get("sub_type") != query.sub_type:
            return False
        if query.entity_prefix:
            # Exact startswith semantics via precomputed ancestor list.
            ancestors = doc.get("entity_prefix_path") or []
            if query.entity_prefix not in ancestors:
                return False
        if query.tags:
            doc_tags = set(doc.get("tags") or [])
            if not all(tag in doc_tags for tag in query.tags):
                return False
        if query.attributes:
            attrs = doc.get("attributes") or {}
            for key, value in query.attributes:
                if attrs.get(key) != value:
                    return False
        return True

    # ------------------------------------------------------------------ #
    # Scoring
    # ------------------------------------------------------------------ #

    def _score(self, doc: Dict[str, Any], tokens: List[str], fuzzy: bool) -> float:
        """Sum per-field, per-token contributions.

        Exact-token matches outrank prefix matches, which outrank fuzzy
        matches; higher-weighted fields contribute more. Identifier *values*
        are matched exactly (case-insensitive) so an ID query lands precisely.
        """
        score = 0.0

        # Exact identifier-value match (e.g. searching by an ID number/handle).
        raw_query = " ".join(tokens)
        for ident in _field_texts(doc.get("identifiers")):
            if ident.lower() == raw_query:
                score += 12.0

        for field_name, weight in _TEXT_FIELD_WEIGHTS:
            field_tokens = self._field_token_set(doc, field_name)
            if not field_tokens:
                continue
            for token in tokens:
                score += weight * self._token_match(token, field_tokens, fuzzy)
        return score

    @staticmethod
    def _field_token_set(doc: Dict[str, Any], field_name: str) -> List[str]:
        tokens: List[str] = []
        for text in _field_texts(doc.get(field_name)):
            tokens.extend(_tokenize(text))
        return tokens

    @staticmethod
    def _token_match(token: str, field_tokens: List[str], fuzzy: bool) -> float:
        """Best per-token contribution against a field's tokens (0..1.0)."""
        best = 0.0
        for ft in field_tokens:
            if ft == token:
                return 1.0  # exact token match dominates
            if ft.startswith(token) or token.startswith(ft):
                best = max(best, 0.6)
            elif fuzzy and len(token) >= 3 and abs(len(ft) - len(token)) <= 3:
                ratio = SequenceMatcher(None, token, ft).ratio()
                if ratio >= _FUZZY_THRESHOLD:
                    best = max(best, 0.4 * ratio)
        return best
