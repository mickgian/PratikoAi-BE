"""Tests for follow-up detection in result_builders.

DEV-251 Part 3.1: Tests for the follow-up detection logic that enables
concise responses for follow-up questions.
"""

import pytest

from app.services.topic_extraction.result_builders import (
    _detect_followup_from_query,
    hf_result_to_decision_dict,
)


class TestFollowupDetectionPatterns:
    """Test the _detect_followup_from_query function patterns."""

    # Pattern 1: Starts with continuation conjunctions
    @pytest.mark.parametrize(
        "query",
        [
            "e l'IMU?",
            "e l'IRAP?",
            "e il TFR?",
            "e la TARI?",
            "e i contributi?",
            "e le sanzioni?",
            "e gli interessi?",
            "ma le scadenze?",
            "però i requisiti?",
            "anche l'IVA?",
            "invece l'IRPEF?",
            "e per le aziende?",
        ],
    )
    def test_detects_continuation_conjunctions(self, query: str) -> None:
        """Queries starting with continuation conjunctions are follow-ups."""
        assert _detect_followup_from_query(query) is True

    # Pattern 2: Very short questions (<6 words)
    @pytest.mark.parametrize(
        "query",
        [
            "E l'IMU?",
            "E per IRAP?",
            "Anche le sanzioni?",
            "E i termini?",
        ],
    )
    def test_detects_short_questions(self, query: str) -> None:
        """Short questions with question mark are follow-ups."""
        assert _detect_followup_from_query(query) is True

    # Pattern 3: Anaphoric references
    @pytest.mark.parametrize(
        "query",
        [
            "questo vale anche per le partite IVA?",
            "quello che hai detto si applica ai professionisti?",
            "lo stesso per le società?",
            "anche per i dipendenti?",
            "e per le pensioni?",
            "riguardo a questo argomento, quali sono le eccezioni?",
            "in questo caso cosa succede?",
        ],
    )
    def test_detects_anaphoric_references(self, query: str) -> None:
        """Queries with anaphoric references are follow-ups."""
        assert _detect_followup_from_query(query) is True

    # Negative tests: NOT follow-ups
    @pytest.mark.parametrize(
        "query",
        [
            "Parlami della rottamazione quinquies",
            "Quali sono i requisiti per il bonus assunzioni?",
            "Come funziona il credito d'imposta ricerca e sviluppo?",
            "Quali sono le aliquote IVA applicabili ai servizi digitali?",
            "Spiegami la normativa sui contratti a tempo determinato",
            "Qual è il termine per la presentazione del modello Redditi?",
        ],
    )
    def test_does_not_detect_new_questions(self, query: str) -> None:
        """New standalone questions should NOT be detected as follow-ups."""
        assert _detect_followup_from_query(query) is False

    def test_empty_query_not_followup(self) -> None:
        """Empty queries should not be detected as follow-ups."""
        assert _detect_followup_from_query("") is False

    def test_none_safe(self) -> None:
        """Function should handle None-like inputs gracefully."""
        # Empty string
        assert _detect_followup_from_query("") is False


class TestHfResultToDecisionDict:
    """Test the hf_result_to_decision_dict function with query parameter."""

    def test_detects_followup_when_query_provided(self) -> None:
        """When query is provided, follow-up detection should run."""
        # Create a mock IntentResult
        from unittest.mock import MagicMock

        mock_result = MagicMock()
        mock_result.intent = "technical_research"
        mock_result.confidence = 0.85

        result = hf_result_to_decision_dict(mock_result, query="e l'IMU?")
        assert result["is_followup"] is True

    def test_no_followup_detection_without_query(self) -> None:
        """When query is not provided, is_followup defaults to False."""
        from unittest.mock import MagicMock

        mock_result = MagicMock()
        mock_result.intent = "technical_research"
        mock_result.confidence = 0.85

        result = hf_result_to_decision_dict(mock_result)
        assert result["is_followup"] is False

    def test_no_followup_for_new_question(self) -> None:
        """New questions should have is_followup=False."""
        from unittest.mock import MagicMock

        mock_result = MagicMock()
        mock_result.intent = "technical_research"
        mock_result.confidence = 0.85

        result = hf_result_to_decision_dict(mock_result, query="Parlami della rottamazione quinquies")
        assert result["is_followup"] is False

    def test_preserves_other_fields(self) -> None:
        """Other fields should be preserved correctly."""
        from unittest.mock import MagicMock

        mock_result = MagicMock()
        mock_result.intent = "normative_reference"
        mock_result.confidence = 0.92

        result = hf_result_to_decision_dict(mock_result, query="e l'IMU?")

        assert result["route"] == "normative_reference"
        assert result["confidence"] == 0.92
        assert result["needs_retrieval"] is True
        assert result["is_followup"] is True
