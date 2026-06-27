"""Transliteration used at index time to enable EN<->Devanagari search.

The document builder calls a :class:`Transliterator` to generate cross-script
forms of names: the romanized form of every Devanagari name and the Devanagari
form of every romanized name. These are stored as additional searchable fields
so a query in either script can match an entity stored in the other.

The default :class:`StaticTransliterator` wraps the existing rule-based helpers
in :mod:`nes.core.utils.devanagari`. The Devanagari->Roman direction is decent;
the Roman->Devanagari direction is approximate. Because transliterated forms are
purely *additive* recall boosters (the real ``ne``/``en`` names are always
indexed from the source data), approximate output is acceptable here.

A higher-quality optional :class:`IndicTransliterator` (backed by the
``indic-transliteration`` library) can be substituted when that dependency is
installed; it improves the Devanagari->Roman direction.
"""

import logging
from typing import Protocol, runtime_checkable

from nes.core.utils.devanagari import (
    contains_devanagari,
    transliterate_to_devanagari,
    transliterate_to_roman,
)

logger = logging.getLogger(__name__)


@runtime_checkable
class Transliterator(Protocol):
    """Bidirectional transliteration between Roman and Devanagari scripts."""

    def to_roman(self, text: str) -> str:
        """Return the romanized form of ``text`` (empty string if not useful)."""
        ...

    def to_devanagari(self, text: str) -> str:
        """Return the Devanagari form of ``text`` (empty string if not useful)."""
        ...


class StaticTransliterator:
    """Default transliterator backed by the rule-based devanagari utilities."""

    def to_roman(self, text: str) -> str:
        if not text or not contains_devanagari(text):
            return ""
        try:
            romanized = transliterate_to_roman(text)
        except Exception:  # pragma: no cover - defensive; utils are pure
            logger.exception("romanization failed for %r", text)
            return ""
        # Only useful if it actually produced a Roman form different from input.
        return romanized if romanized and not contains_devanagari(romanized) else ""

    def to_devanagari(self, text: str) -> str:
        if not text or contains_devanagari(text):
            return ""
        try:
            deva = transliterate_to_devanagari(text)
        except Exception:  # pragma: no cover - defensive; utils are pure
            logger.exception("transliteration failed for %r", text)
            return ""
        return deva if deva and contains_devanagari(deva) else ""


class IndicTransliterator:
    """Higher-quality transliterator backed by ``indic-transliteration``.

    Improves the Devanagari->Roman direction over the rule-based char map.
    Only usable when the optional ``indic-transliteration`` dependency is
    installed; construction raises ImportError otherwise. The Roman->Devanagari
    direction reuses the static helper (synthesizing Devanagari from arbitrary
    romanized English is inherently lossy and only an additive recall booster).
    """

    def __init__(self) -> None:
        # Imported here so the module loads without the optional dependency.
        from indic_transliteration import sanscript  # noqa: F401

        self._sanscript = sanscript

    def to_roman(self, text: str) -> str:
        if not text or not contains_devanagari(text):
            return ""
        try:
            romanized = self._sanscript.transliterate(
                text, self._sanscript.DEVANAGARI, self._sanscript.IAST
            )
        except Exception:  # pragma: no cover - defensive
            logger.exception("indic romanization failed for %r", text)
            return ""
        return romanized if romanized and not contains_devanagari(romanized) else ""

    def to_devanagari(self, text: str) -> str:
        return StaticTransliterator().to_devanagari(text)
