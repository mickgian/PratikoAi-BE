"""Tests for centralized Italian stop word list.

DEV-245 Phase 5.14: Centralized stop word module tests.
Ensures stop word lists are comprehensive and don't filter domain terms.
"""

import pytest

from app.services.italian_stop_words import STOP_WORDS, STOP_WORDS_MINIMAL


class TestStopWordListsCompleteness:
    """Test stop word list completeness for common patterns."""

    def test_recepira_is_filtered(self):
        """DEV-245 Phase 5.14: The 'recepira' problem must be fixed.

        Production issue: "la regione sicilia recepira' la rottamazione dell'irap?"
        extracted "recepira" as a keyword when it should have been filtered.

        Note: Users often type "recepira'" (apostrophe) instead of "recepirà" (accent),
        so we need BOTH the accented and non-accented forms in the stop word list.
        """
        # Accented form
        assert "recepirà" in STOP_WORDS
        # Non-accented form (THE FIX for the production issue!)
        assert "recepira" in STOP_WORDS
        # Other conjugations
        assert "recepiranno" in STOP_WORDS
        assert "recepire" in STOP_WORDS
        assert "recepisce" in STOP_WORDS
        assert "recepirebbe" in STOP_WORDS

    def test_future_tense_verbs_filtered(self):
        """Future tense verbs should be stop words."""
        future_verbs = [
            "sarà",
            "saranno",  # essere
            "avrà",
            "avranno",  # avere
            "potrà",
            "potranno",  # potere
            "dovrà",
            "dovranno",  # dovere
            "farà",
            "faranno",  # fare
            "vorrà",
            "vorranno",  # volere
        ]
        for verb in future_verbs:
            assert verb in STOP_WORDS, f"{verb} missing from STOP_WORDS"

    def test_conditional_verbs_filtered(self):
        """Conditional verbs should be stop words."""
        conditional_verbs = [
            "sarebbe",
            "sarebbero",  # essere
            "avrebbe",
            "avrebbero",  # avere
            "potrebbe",
            "potrebbero",  # potere
            "dovrebbe",
            "dovrebbero",  # dovere
            "vorrei",
            "vorresti",
            "vorrebbe",
            "vorrebbero",  # volere
            "potrei",
            "potresti",  # potere
            "dovrei",
            "dovresti",  # dovere
        ]
        for verb in conditional_verbs:
            assert verb in STOP_WORDS, f"{verb} missing from STOP_WORDS"

    def test_imperative_request_forms_filtered(self):
        """Imperative/request forms should be stop words."""
        imperatives = [
            "dimmi",
            "dammi",
            "fammi",
            "parlami",
            "spiegami",
            "raccontami",
            "indicami",
            "mostrami",
            "elencami",
        ]
        for verb in imperatives:
            assert verb in STOP_WORDS, f"{verb} missing from STOP_WORDS"

    def test_common_verbs_all_forms_filtered(self):
        """Common verbs (essere, avere, potere, dovere) should have all forms."""
        # Essere (to be)
        essere_forms = ["essere", "è", "sono", "era", "erano", "sarà", "sarebbe"]
        for form in essere_forms:
            assert form in STOP_WORDS, f"essere form '{form}' missing"

        # Avere (to have)
        avere_forms = ["avere", "ha", "ho", "hanno", "aveva", "avrà", "avrebbe"]
        for form in avere_forms:
            assert form in STOP_WORDS, f"avere form '{form}' missing"

    def test_articles_and_prepositions_filtered(self):
        """All Italian articles and prepositions should be stop words."""
        articles = ["il", "lo", "la", "i", "gli", "le", "un", "uno", "una"]
        prepositions = ["di", "a", "da", "in", "con", "su", "per", "tra", "fra"]

        for word in articles + prepositions:
            assert word in STOP_WORDS, f"'{word}' missing from STOP_WORDS"
            assert word in STOP_WORDS_MINIMAL, f"'{word}' missing from STOP_WORDS_MINIMAL"

    def test_preposition_contractions_filtered(self):
        """Preposition contractions (del, nel, etc.) should be stop words."""
        contractions = [
            "del",
            "dello",
            "della",
            "dei",
            "degli",
            "delle",
            "al",
            "allo",
            "alla",
            "ai",
            "agli",
            "alle",
            "dal",
            "dallo",
            "dalla",
            "dai",
            "dagli",
            "dalle",
            "nel",
            "nello",
            "nella",
            "nei",
            "negli",
            "nelle",
            "sul",
            "sullo",
            "sulla",
            "sui",
            "sugli",
            "sulle",
            # Apostrophe stems
            "dell",
            "all",
            "nell",
            "sull",
            "dall",
        ]
        for word in contractions:
            assert word in STOP_WORDS, f"contraction '{word}' missing"


class TestDomainTermsNotFiltered:
    """Test that fiscal domain terms are NOT filtered."""

    def test_fiscal_terms_not_filtered(self):
        """Core fiscal terms must NOT be stop words."""
        fiscal_terms = [
            "rottamazione",
            "quinquies",
            "quater",
            "ter",
            "irap",
            "irpef",
            "iva",
            "imu",
            "tari",
            "contributi",
            "previdenziali",
            "assistenziali",
            "aliquota",
            "scadenza",
            "versamento",
            "dichiarazione",
            "fattura",
            "fatturazione",
            "inps",
            "inail",
            "agenzia",
        ]
        for term in fiscal_terms:
            assert term not in STOP_WORDS, f"fiscal term '{term}' wrongly in STOP_WORDS"

    def test_legal_terms_not_filtered(self):
        """Legal terms must NOT be stop words."""
        legal_terms = [
            "legge",
            "decreto",
            "circolare",
            "risoluzione",
            "interpello",
            "articolo",
            "comma",
            "sanzione",
            "ammenda",
            "multa",
            "ricorso",
            "istanza",
            "domanda",
        ]
        for term in legal_terms:
            assert term not in STOP_WORDS, f"legal term '{term}' wrongly in STOP_WORDS"

    def test_region_names_not_filtered(self):
        """Italian region names should NOT be stop words."""
        regions = [
            "sicilia",
            "lombardia",
            "lazio",
            "campania",
            "piemonte",
            "veneto",
            "emilia",
            "toscana",
        ]
        for region in regions:
            assert region not in STOP_WORDS, f"region '{region}' wrongly in STOP_WORDS"


class TestStopWordListProperties:
    """Test structural properties of stop word lists."""

    def test_minimal_is_subset_of_full(self):
        """Minimal list should be subset of full list."""
        assert STOP_WORDS_MINIMAL.issubset(STOP_WORDS), (
            f"STOP_WORDS_MINIMAL has words not in STOP_WORDS: " f"{STOP_WORDS_MINIMAL - STOP_WORDS}"
        )

    def test_stop_words_are_lowercase(self):
        """All stop words should be lowercase."""
        for word in STOP_WORDS:
            assert word == word.lower(), f"'{word}' is not lowercase"
        for word in STOP_WORDS_MINIMAL:
            assert word == word.lower(), f"'{word}' in MINIMAL is not lowercase"

    def test_stop_words_are_strings(self):
        """All stop words should be strings."""
        for word in STOP_WORDS:
            assert isinstance(word, str), f"'{word}' is not a string"

    def test_full_list_has_reasonable_size(self):
        """Full list should have ~200+ words for comprehensive coverage."""
        assert len(STOP_WORDS) >= 180, f"STOP_WORDS has only {len(STOP_WORDS)} words, expected 180+"

    def test_minimal_list_has_reasonable_size(self):
        """Minimal list should have ~50 words for basic coverage."""
        assert (
            40 <= len(STOP_WORDS_MINIMAL) <= 80
        ), f"STOP_WORDS_MINIMAL has {len(STOP_WORDS_MINIMAL)} words, expected 40-80"

    def test_no_empty_strings(self):
        """Stop word lists should not contain empty strings."""
        assert "" not in STOP_WORDS
        assert "" not in STOP_WORDS_MINIMAL


class TestKeywordExtractionScenarios:
    """Test real-world keyword extraction scenarios."""

    def test_q5_recepira_scenario(self):
        """DEV-245: Q5 scenario that caused the 'recepira' problem.

        Query: "la regione sicilia recepira' la rottamazione dell'irap?"
        Expected extracted keywords: ['regione', 'sicilia', 'rottamazione', 'irap']
        NOT: [..., 'recepira']

        The fix: Both "recepirà" (accented) and "recepira" (non-accented) are in STOP_WORDS.
        """
        import re

        query = "la regione sicilia recepira' la rottamazione dell'irap?"
        query_lower = query.lower()
        # Handle contractions - this converts "recepira'" to "recepira "
        query_lower = re.sub(r"[''`]", " ", query_lower)
        words = re.findall(r"[a-zàèéìòùáéíóú]+", query_lower)

        # Filter using STOP_WORDS
        keywords = [w for w in words if w not in STOP_WORDS and len(w) > 2]

        # CRITICAL: "recepira" (non-accented) must be filtered
        # This is the exact form that appears after normalization
        assert "recepira" in STOP_WORDS, "Non-accented 'recepira' must be in STOP_WORDS!"
        assert "recepira" not in keywords, "recepira should have been filtered!"

        # Domain terms should remain
        assert "rottamazione" in keywords, "rottamazione should be preserved"
        assert "sicilia" in keywords, "sicilia should be preserved"
        assert "regione" in keywords, "regione should be preserved"
        assert "irap" in keywords, "irap should be preserved"

    def test_simple_question_extraction(self):
        """Test extracting keywords from a simple question."""
        import re

        query = "parlami della rottamazione quinquies"
        query_lower = query.lower()
        words = re.findall(r"[a-zàèéìòùáéíóú]+", query_lower)

        keywords = [w for w in words if w not in STOP_WORDS and len(w) > 2]

        # "parlami" and "della" should be filtered
        assert "parlami" in STOP_WORDS
        assert "della" in STOP_WORDS

        # Domain terms should remain
        assert "rottamazione" in keywords
        assert "quinquies" in keywords
