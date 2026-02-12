"""Tests for broken hyphenation repair in Italian text.

Verifies that PDF extraction artifacts like "contri- buto" are
correctly rejoined into "contributo" while preserving legitimate
hyphens in compound words like "decreto-legge".
"""

from app.core.text.hyphenation import repair_broken_hyphenation


class TestRepairBrokenHyphenation:
    """Tests for repair_broken_hyphenation()."""

    def test_rejoins_broken_word(self) -> None:
        """Single broken hyphenation is repaired."""
        assert repair_broken_hyphenation("contri- buto") == "contributo"

    def test_multiple_breaks(self) -> None:
        """Multiple broken hyphenations in the same string."""
        text = "contri- buto previ- denziale"
        assert repair_broken_hyphenation(text) == "contributo previdenziale"

    def test_accented_chars(self) -> None:
        """Accented Italian characters are handled."""
        assert repair_broken_hyphenation("attività- economica") == "attivitàeconomica"

    def test_preserves_decreto_legge(self) -> None:
        """Legitimate compound 'decreto-legge' is not modified (no space after hyphen)."""
        assert repair_broken_hyphenation("decreto-legge") == "decreto-legge"

    def test_preserves_compound(self) -> None:
        """Legitimate compound 'socio-economico' is not modified."""
        assert repair_broken_hyphenation("socio-economico") == "socio-economico"

    def test_empty_string(self) -> None:
        """Empty string returns empty string."""
        assert repair_broken_hyphenation("") == ""

    def test_no_hyphens(self) -> None:
        """Text without hyphens is unchanged."""
        assert repair_broken_hyphenation("testo normale") == "testo normale"

    def test_hyphen_at_end_of_line(self) -> None:
        """Hyphen followed by newline and word is handled."""
        assert repair_broken_hyphenation("contri-\n buto") == "contri-\n buto"

    def test_mixed_content(self) -> None:
        """Mixed legitimate and broken hyphens in same text."""
        text = "il decreto-legge sul contri- buto"
        assert repair_broken_hyphenation(text) == "il decreto-legge sul contributo"
