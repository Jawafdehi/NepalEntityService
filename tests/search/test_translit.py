"""Tests for the index-time transliterator."""

from nes.core.utils.devanagari import contains_devanagari
from nes.search.translit import StaticTransliterator, Transliterator


class TestStaticTransliterator:
    def setup_method(self):
        self.t = StaticTransliterator()

    def test_satisfies_protocol(self):
        assert isinstance(self.t, Transliterator)

    def test_to_roman_converts_devanagari(self):
        roman = self.t.to_roman("नेपाल")
        assert roman  # produced something
        assert not contains_devanagari(roman)

    def test_to_roman_ignores_roman_input(self):
        # Already-Roman input yields no new transliteration.
        assert self.t.to_roman("Kathmandu") == ""

    def test_to_roman_empty(self):
        assert self.t.to_roman("") == ""

    def test_to_devanagari_converts_roman(self):
        deva = self.t.to_devanagari("nepal")
        assert deva
        assert contains_devanagari(deva)

    def test_to_devanagari_ignores_devanagari_input(self):
        assert self.t.to_devanagari("नेपाल") == ""

    def test_to_devanagari_empty(self):
        assert self.t.to_devanagari("") == ""
