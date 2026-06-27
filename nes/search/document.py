"""Build a flat, searchable document from an :class:`Entity`.

This is the single place that decides *what* is searchable. It is pure and
synchronous (no I/O, no network, no LLM) so it is trivially unit-testable and
safe to call inside the write path for live indexing.

The output is a plain ``dict`` shared by all backends. Field groups:

- ``name_primary_en`` / ``name_primary_ne`` -- highest-boost name fields, from
  names with ``kind == PRIMARY``.
- ``name_alias_en`` / ``name_alias_ne`` -- other names (ALIAS/ALTERNATE/BIRTH)
  plus ``misspelled_names`` and name variants (last-name-only, first+last...).
- ``name_translit_roman`` / ``name_translit_devanagari`` -- index-time
  cross-script forms enabling EN<->Devanagari search.
- ``identifiers`` (exact values) / ``identifier_names`` (their human names).
- ``tags``, ``slug``, ``short_description_*``, ``description_*``.
- Filter fields: ``type``, ``sub_type``, ``entity_prefix``,
  ``entity_prefix_path`` (all ancestor prefixes for exact startswith filtering)
  and ``attributes`` (flattened scalar leaves, filter-only).
"""

from typing import Any, Dict, List, Optional

from nes.core.models.base import NameKind
from nes.core.models.entity import Entity
from nes.core.utils.multilingual import extract_name_variants
from nes.search.translit import StaticTransliterator, Transliterator

# Name-part fields searched on each NameParts object, in priority order.
_NAME_PART_FIELDS = ("full", "given", "middle", "family", "prefix", "suffix")


class EntityDocumentBuilder:
    """Convert :class:`Entity` instances into searchable documents."""

    def __init__(self, transliterator: Optional[Transliterator] = None):
        self.transliterator = transliterator or StaticTransliterator()

    def build(self, entity: Entity) -> Dict[str, Any]:
        """Return the searchable document for ``entity`` (keyed by ``id``)."""
        primary_en: List[str] = []
        primary_ne: List[str] = []
        alias_en: List[str] = []
        alias_ne: List[str] = []
        translit_roman: List[str] = []
        translit_devanagari: List[str] = []

        # Primary names (highest boost) vs everything else (aliases).
        for name in entity.names or []:
            is_primary = _name_kind(name) == NameKind.PRIMARY
            self._collect_name(
                name,
                primary_en if is_primary else alias_en,
                primary_ne if is_primary else alias_ne,
                translit_roman,
                translit_devanagari,
            )

        # Misspelled / alternative names always count as aliases.
        for name in entity.misspelled_names or []:
            self._collect_name(
                name, alias_en, alias_ne, translit_roman, translit_devanagari
            )

        # Identifiers: exact values (keyword) plus their human-readable names.
        identifier_values: List[str] = []
        identifier_names: List[str] = []
        for ident in entity.identifiers or []:
            if ident.value:
                identifier_values.append(ident.value)
            if ident.name:
                identifier_names.extend(_lang_text_values(ident.name))

        doc: Dict[str, Any] = {
            "id": entity.id,
            "type": _enum_value(entity.type),
            "sub_type": _enum_value(entity.sub_type),
            "entity_prefix": _effective_prefix(entity),
            "entity_prefix_path": _prefix_ancestors(_effective_prefix(entity)),
            "slug": entity.slug,
            "name_primary_en": _dedupe(primary_en),
            "name_primary_ne": _dedupe(primary_ne),
            "name_alias_en": _dedupe(alias_en),
            "name_alias_ne": _dedupe(alias_ne),
            "name_translit_roman": _dedupe(translit_roman),
            "name_translit_devanagari": _dedupe(translit_devanagari),
            "identifiers": _dedupe(identifier_values),
            "identifier_names": _dedupe(identifier_names),
            "tags": list(entity.tags or []),
            "short_description_en": _lang_text_value(entity.short_description, "en"),
            "short_description_ne": _lang_text_value(entity.short_description, "ne"),
            "description_en": _lang_text_value(entity.description, "en"),
            "description_ne": _lang_text_value(entity.description, "ne"),
            "attributes": _flatten_attributes(entity.attributes),
        }
        return doc

    def _collect_name(
        self,
        name,
        out_en: List[str],
        out_ne: List[str],
        out_roman: List[str],
        out_devanagari: List[str],
    ) -> None:
        """Extract parts + variants from one Name into the target buckets."""
        if name.en:
            for part in _name_part_values(name.en):
                out_en.append(part)
            full = getattr(name.en, "full", None)
            if full:
                out_en.extend(extract_name_variants(full))
                # English -> Devanagari (approximate, additive recall).
                deva = self.transliterator.to_devanagari(full)
                if deva:
                    out_devanagari.append(deva)
        if name.ne:
            for part in _name_part_values(name.ne):
                out_ne.append(part)
            full = getattr(name.ne, "full", None)
            if full:
                # Devanagari -> Roman (good quality, high value).
                roman = self.transliterator.to_roman(full)
                if roman:
                    out_roman.append(roman)
                    out_roman.extend(extract_name_variants(roman))


# --------------------------------------------------------------------------- #
# Module-level helpers (pure functions, easy to test in isolation).
# --------------------------------------------------------------------------- #


def _enum_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    return value.value if hasattr(value, "value") else value


def _name_kind(name) -> Any:
    return name.kind


def _name_part_values(parts) -> List[str]:
    """Return the non-empty text values from a NameParts object."""
    values: List[str] = []
    for field_name in _NAME_PART_FIELDS:
        val = getattr(parts, field_name, None)
        if val:
            values.append(val)
    return values


def _lang_text_value(lang_text, lang: str) -> Optional[str]:
    """Return ``lang_text.<lang>.value`` if present, else None."""
    if lang_text is None:
        return None
    sub = getattr(lang_text, lang, None)
    if sub is None:
        return None
    value = getattr(sub, "value", None)
    return value or None


def _lang_text_values(lang_text) -> List[str]:
    """Return both en/ne values from a LangText, skipping empties."""
    out: List[str] = []
    for lang in ("en", "ne"):
        val = _lang_text_value(lang_text, lang)
        if val:
            out.append(val)
    return out


def _effective_prefix(entity: Entity) -> Optional[str]:
    """Resolve the entity_prefix, falling back to type/sub_type for legacy data."""
    if entity.entity_prefix is not None:
        return entity.entity_prefix
    type_val = _enum_value(entity.type)
    sub_val = _enum_value(entity.sub_type)
    if type_val is None:
        return None
    return type_val if sub_val is None else f"{type_val}/{sub_val}"


def _prefix_ancestors(prefix: Optional[str]) -> List[str]:
    """Expand ``a/b/c`` into ``['a', 'a/b', 'a/b/c']`` for exact prefix filters."""
    if not prefix:
        return []
    segments = prefix.split("/")
    return ["/".join(segments[: i + 1]) for i in range(len(segments))]


def _flatten_attributes(attributes: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Flatten nested attribute dicts into dotted scalar keys for filtering.

    Lists and non-scalar leaves are dropped; attributes are used only for
    equality filtering, not full-text search.
    """
    if not attributes:
        return {}
    flat: Dict[str, Any] = {}

    def _walk(prefix: str, value: Any) -> None:
        if isinstance(value, dict):
            for k, v in value.items():
                _walk(f"{prefix}.{k}" if prefix else k, v)
        elif isinstance(value, (str, int, float, bool)):
            flat[prefix] = value

    _walk("", attributes)
    return flat


def _dedupe(values: List[str]) -> List[str]:
    """Order-preserving de-duplication of non-empty strings."""
    seen = set()
    out: List[str] = []
    for v in values:
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out
