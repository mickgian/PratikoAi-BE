"""TDD tests for GuardrailStreamProcessor.

Tests for sentence-level guardrail filtering during LLM streaming.
Implements Pattern 3 (Guardrail Streaming) to preserve disclaimer filtering,
PII deanonymization, and citation validation during real-time streaming.
"""

import pytest


class TestGuardrailStreamProcessorChunkAccumulation:
    """Test that chunks are accumulated until sentence boundaries."""

    def test_accumulates_partial_sentence(self):
        """Partial text without sentence boundary should buffer, not emit."""
        from app.services.guardrail_stream_processor import GuardrailStreamProcessor

        processor = GuardrailStreamProcessor()
        result = processor.process_chunk("L'aliquota è del")

        assert result == []  # No complete sentence yet

    def test_emits_on_sentence_boundary_period(self):
        """Text ending with period should emit the sentence."""
        from app.services.guardrail_stream_processor import GuardrailStreamProcessor

        processor = GuardrailStreamProcessor()
        processor.process_chunk("L'aliquota è del 22%")
        result = processor.process_chunk(".")

        assert len(result) == 1
        assert "22%" in result[0]

    def test_emits_on_newline_boundary(self):
        """Text ending with newline should emit."""
        from app.services.guardrail_stream_processor import GuardrailStreamProcessor

        processor = GuardrailStreamProcessor()
        result = processor.process_chunk("Prima riga\n")

        assert len(result) == 1
        assert "Prima riga" in result[0]

    def test_multiple_sentences_in_one_chunk(self):
        """Chunk with multiple sentences should emit all complete ones."""
        from app.services.guardrail_stream_processor import GuardrailStreamProcessor

        processor = GuardrailStreamProcessor()
        result = processor.process_chunk("Primo. Secondo. Terzo")

        # "Primo." and "Secondo." are complete, "Terzo" stays buffered
        assert len(result) == 2
        assert "Primo." in result[0]
        assert "Secondo." in result[1]


class TestGuardrailStreamProcessorDisclaimerFiltering:
    """Test that disclaimer phrases are removed from streamed chunks."""

    def test_removes_disclaimer_from_sentence(self):
        """Disclaimer phrase should be removed from emitted sentence."""
        from app.services.guardrail_stream_processor import GuardrailStreamProcessor

        processor = GuardrailStreamProcessor()
        result = processor.process_chunk("L'IRAP può essere inclusa, consulta un esperto fiscale per conferma.")

        assert len(result) == 1
        assert "consulta un esperto" not in result[0].lower()
        assert "IRAP" in result[0]

    def test_removes_consult_professional(self):
        """Should remove 'si consiglia di consultare' from stream."""
        from app.services.guardrail_stream_processor import GuardrailStreamProcessor

        processor = GuardrailStreamProcessor()
        result = processor.process_chunk("La scadenza è il 30 aprile. Si consiglia di consultare un professionista.")

        assert len(result) == 2
        assert "La scadenza è il 30 aprile" in result[0]
        assert all("si consiglia di consultare" not in r.lower() for r in result)

    def test_no_false_positives_on_clean_text(self):
        """Clean text without disclaimers should pass through unchanged."""
        from app.services.guardrail_stream_processor import GuardrailStreamProcessor

        processor = GuardrailStreamProcessor()
        result = processor.process_chunk("L'aliquota ridotta è del 10% per i beni di prima necessità.")

        assert len(result) == 1
        assert result[0].strip() == "L'aliquota ridotta è del 10% per i beni di prima necessità."


class TestGuardrailStreamProcessorDeanonymization:
    """Test PII deanonymization during streaming."""

    def test_deanonymizes_pii_placeholder(self):
        """PII placeholders should be replaced in emitted chunks."""
        from app.services.guardrail_stream_processor import GuardrailStreamProcessor

        dmap = {"[PERSON_1]": "Mario Rossi", "[CF_1]": "RSSMRA80A01H501Z"}
        processor = GuardrailStreamProcessor(deanonymization_map=dmap)
        result = processor.process_chunk("Il contribuente [PERSON_1] con CF [CF_1] deve pagare.")

        assert len(result) == 1
        assert "Mario Rossi" in result[0]
        assert "RSSMRA80A01H501Z" in result[0]
        assert "[PERSON_1]" not in result[0]

    def test_no_deanonymization_without_map(self):
        """Without deanonymization map, text passes through as-is."""
        from app.services.guardrail_stream_processor import GuardrailStreamProcessor

        processor = GuardrailStreamProcessor()
        result = processor.process_chunk("Il contribuente [PERSON_1] deve pagare.")

        assert len(result) == 1
        assert "[PERSON_1]" in result[0]


class TestGuardrailStreamProcessorFinalize:
    """Test finalization (flush buffer + full-text post-processing)."""

    def test_flush_emits_remaining_buffer(self):
        """Finalize should emit any remaining buffered text."""
        from app.services.guardrail_stream_processor import GuardrailStreamProcessor

        processor = GuardrailStreamProcessor()
        processor.process_chunk("Testo senza punto finale")
        result = processor.finalize()

        assert result.remaining_text == "Testo senza punto finale"

    def test_finalize_returns_full_text(self):
        """Finalize should return the full accumulated response."""
        from app.services.guardrail_stream_processor import GuardrailStreamProcessor

        processor = GuardrailStreamProcessor()
        processor.process_chunk("Prima frase.")
        processor.process_chunk(" Seconda frase.")
        result = processor.finalize()

        assert "Prima frase" in result.full_text
        assert "Seconda frase" in result.full_text

    def test_finalize_applies_section_numbering_fix(self):
        """Finalize should fix broken section numbering on full text."""
        from app.services.guardrail_stream_processor import GuardrailStreamProcessor

        processor = GuardrailStreamProcessor()
        # Feed line by line (as the LLM would stream)
        processor.process_chunk("1. Primo Punto\n")
        processor.process_chunk("Dettagli del primo punto.\n")
        processor.process_chunk("1. Secondo Punto\n")
        processor.process_chunk("Dettagli del secondo punto.\n")
        result = processor.finalize()

        # SectionNumberingFixer should correct 1. 1. → 1. 2.
        assert "2. " in result.full_text

    def test_finalize_applies_bold_formatting(self):
        """Finalize should apply bold section formatting on full text."""
        from app.services.guardrail_stream_processor import GuardrailStreamProcessor

        processor = GuardrailStreamProcessor()
        processor.process_chunk("1. Scadenze e Termini\n")
        processor.process_chunk("\n")
        processor.process_chunk("La scadenza è il 30 aprile.\n")
        result = processor.finalize()

        # BoldSectionFormatter should add bold to section titles
        assert "**Scadenze e Termini**" in result.full_text

    def test_finalize_disclaimer_filtered_in_remaining(self):
        """Remaining buffer at finalize should also have disclaimers filtered."""
        from app.services.guardrail_stream_processor import GuardrailStreamProcessor

        processor = GuardrailStreamProcessor()
        processor.process_chunk("Resto a disposizione per qualsiasi domanda")
        result = processor.finalize()

        assert "resto a disposizione" not in result.remaining_text.lower()


class TestGuardrailStreamProcessorStats:
    """Test statistics and metrics tracking."""

    def test_tracks_chunks_processed(self):
        """Should track number of chunks processed."""
        from app.services.guardrail_stream_processor import GuardrailStreamProcessor

        processor = GuardrailStreamProcessor()
        processor.process_chunk("Prima.")
        processor.process_chunk(" Seconda.")
        result = processor.finalize()

        assert result.chunks_processed == 2

    def test_tracks_disclaimers_removed(self):
        """Should track total disclaimers removed across all chunks."""
        from app.services.guardrail_stream_processor import GuardrailStreamProcessor

        processor = GuardrailStreamProcessor()
        processor.process_chunk("Consulta un esperto fiscale.")
        processor.process_chunk(" Rivolgiti a un professionista.")
        result = processor.finalize()

        assert result.disclaimers_removed >= 2


class TestGuardrailStreamProcessorXMLStripping:
    """Test that XML tags are stripped per-sentence to prevent formatting flash."""

    def test_strips_answer_tags_from_sentence(self):
        """<answer> tags should be stripped during streaming, not at content_cleaned."""
        from app.services.guardrail_stream_processor import GuardrailStreamProcessor

        processor = GuardrailStreamProcessor()
        result = processor.process_chunk("<answer>L'aliquota è del 22%.\n")

        assert len(result) >= 1
        combined = "".join(result)
        assert "<answer>" not in combined
        assert "22%" in combined

    def test_strips_closing_answer_tag(self):
        """</answer> tag should be stripped."""
        from app.services.guardrail_stream_processor import GuardrailStreamProcessor

        processor = GuardrailStreamProcessor()
        result = processor.process_chunk("La scadenza è il 30 aprile.</answer>\n")

        assert len(result) >= 1
        combined = "".join(result)
        assert "</answer>" not in combined
        assert "30 aprile" in combined

    def test_strips_suggested_actions_block(self):
        """<suggested_actions> blocks should be stripped from streamed content."""
        from app.services.guardrail_stream_processor import GuardrailStreamProcessor

        processor = GuardrailStreamProcessor()
        result = processor.process_chunk("Risposta valida.\n<suggested_actions>azione1</suggested_actions>\n")

        combined = "".join(result)
        assert "<suggested_actions>" not in combined
        assert "Risposta valida." in combined

    def test_strips_caveat_blocks(self):
        """📌 caveat blocks should be stripped from streamed content."""
        from app.services.guardrail_stream_processor import GuardrailStreamProcessor

        processor = GuardrailStreamProcessor()
        result = processor.process_chunk("Informazione utile.\n📌 Nota: verifica i dati.\n")

        combined = "".join(result)
        assert "📌" not in combined
        assert "Informazione utile." in combined

    def test_preserves_content_without_xml(self):
        """Normal content without XML should pass through unchanged."""
        from app.services.guardrail_stream_processor import GuardrailStreamProcessor

        processor = GuardrailStreamProcessor()
        result = processor.process_chunk("Contenuto normale senza tag XML.\n")

        assert len(result) >= 1
        assert "Contenuto normale senza tag XML." in "".join(result)


class TestGuardrailStreamProcessorEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_chunk(self):
        """Empty chunk should return empty list."""
        from app.services.guardrail_stream_processor import GuardrailStreamProcessor

        processor = GuardrailStreamProcessor()
        result = processor.process_chunk("")

        assert result == []

    def test_none_chunk(self):
        """None chunk should return empty list."""
        from app.services.guardrail_stream_processor import GuardrailStreamProcessor

        processor = GuardrailStreamProcessor()
        result = processor.process_chunk(None)

        assert result == []

    def test_very_long_sentence_force_emit(self):
        """Very long text without sentence boundary should force-emit at threshold."""
        from app.services.guardrail_stream_processor import GuardrailStreamProcessor

        processor = GuardrailStreamProcessor(max_buffer_chars=200)
        long_text = "parola " * 50  # ~350 chars, no period
        result = processor.process_chunk(long_text)

        # Should force-emit when buffer exceeds max_buffer_chars
        assert len(result) >= 1

    def test_markdown_list_items_emit_on_newline(self):
        """Markdown list items separated by newlines should emit individually."""
        from app.services.guardrail_stream_processor import GuardrailStreamProcessor

        processor = GuardrailStreamProcessor()
        result = processor.process_chunk("- Primo punto\n- Secondo punto\n")

        # Both lines end with \n, so both should emit
        assert len(result) >= 1
        combined = "".join(result)
        assert "Primo punto" in combined
        assert "Secondo punto" in combined
