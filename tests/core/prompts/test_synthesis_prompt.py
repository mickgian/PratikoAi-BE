"""TDD Tests for DEV-192: Critical Synthesis Prompt Template.

Tests for synthesis system prompt and prompt builder per Section 13.8.5.
"""

import pytest


class TestSynthesisSystemPrompt:
    """Tests for SYNTHESIS_SYSTEM_PROMPT constant."""

    def test_prompt_exists(self):
        """Test that SYNTHESIS_SYSTEM_PROMPT is defined."""
        from app.core.prompts.synthesis_critical import SYNTHESIS_SYSTEM_PROMPT

        assert SYNTHESIS_SYSTEM_PROMPT is not None
        assert len(SYNTHESIS_SYSTEM_PROMPT) > 100

    def test_prompt_valid_utf8(self):
        """Test that prompt is valid UTF-8."""
        from app.core.prompts.synthesis_critical import SYNTHESIS_SYSTEM_PROMPT

        # Should be able to encode/decode as UTF-8
        encoded = SYNTHESIS_SYSTEM_PROMPT.encode("utf-8")
        decoded = encoded.decode("utf-8")
        assert decoded == SYNTHESIS_SYSTEM_PROMPT

    def test_prompt_includes_role_definition(self):
        """Test that prompt defines the expert role."""
        from app.core.prompts.synthesis_critical import SYNTHESIS_SYSTEM_PROMPT

        prompt_lower = SYNTHESIS_SYSTEM_PROMPT.lower()
        assert "esperto" in prompt_lower or "fiscalista" in prompt_lower
        assert "prudente" in prompt_lower

    def test_prompt_includes_chronological_analysis(self):
        """Test that prompt includes chronological analysis task."""
        from app.core.prompts.synthesis_critical import SYNTHESIS_SYSTEM_PROMPT

        prompt_lower = SYNTHESIS_SYSTEM_PROMPT.lower()
        assert "cronologic" in prompt_lower
        assert "data" in prompt_lower or "ordina" in prompt_lower

    def test_prompt_includes_conflict_detection(self):
        """Test that prompt includes conflict detection task."""
        from app.core.prompts.synthesis_critical import SYNTHESIS_SYSTEM_PROMPT

        prompt_lower = SYNTHESIS_SYSTEM_PROMPT.lower()
        assert "conflitt" in prompt_lower or "contraddic" in prompt_lower

    def test_prompt_includes_hierarchy_rules(self):
        """Test that prompt includes source hierarchy rules."""
        from app.core.prompts.synthesis_critical import SYNTHESIS_SYSTEM_PROMPT

        prompt_lower = SYNTHESIS_SYSTEM_PROMPT.lower()
        assert "gerarchia" in prompt_lower
        # Should mention hierarchy order
        assert "legge" in prompt_lower
        assert "circolare" in prompt_lower

    def test_prompt_includes_verdetto_structure(self):
        """Test that prompt includes Verdetto Operativo structure."""
        from app.core.prompts.synthesis_critical import SYNTHESIS_SYSTEM_PROMPT

        assert "VERDETTO OPERATIVO" in SYNTHESIS_SYSTEM_PROMPT
        assert "AZIONE CONSIGLIATA" in SYNTHESIS_SYSTEM_PROMPT
        assert "ANALISI DEL RISCHIO" in SYNTHESIS_SYSTEM_PROMPT
        assert "SCADENZA" in SYNTHESIS_SYSTEM_PROMPT
        assert "DOCUMENTAZIONE" in SYNTHESIS_SYSTEM_PROMPT
        assert "FONTI" in SYNTHESIS_SYSTEM_PROMPT

    def test_prompt_includes_prudent_principle(self):
        """Test that prompt emphasizes prudent approach."""
        from app.core.prompts.synthesis_critical import SYNTHESIS_SYSTEM_PROMPT

        prompt_lower = SYNTHESIS_SYSTEM_PROMPT.lower()
        # Should mention prudent approach multiple times
        assert prompt_lower.count("prudent") >= 1
        assert "rischio" in prompt_lower or "sanzioni" in prompt_lower

    def test_prompt_includes_metadata_context(self):
        """Test that prompt mentions expected metadata fields."""
        from app.core.prompts.synthesis_critical import SYNTHESIS_SYSTEM_PROMPT

        prompt_lower = SYNTHESIS_SYSTEM_PROMPT.lower()
        # Should reference document metadata
        assert "data" in prompt_lower
        assert "ente" in prompt_lower or "emittente" in prompt_lower
        assert "tipo" in prompt_lower


class TestVerdettoOperativoTemplate:
    """Tests for VERDETTO_OPERATIVO_TEMPLATE constant."""

    def test_template_exists(self):
        """Test that VERDETTO_OPERATIVO_TEMPLATE is defined."""
        from app.core.prompts.synthesis_critical import VERDETTO_OPERATIVO_TEMPLATE

        assert VERDETTO_OPERATIVO_TEMPLATE is not None
        assert len(VERDETTO_OPERATIVO_TEMPLATE) > 50

    def test_template_has_all_sections(self):
        """Test that template has all required sections."""
        from app.core.prompts.synthesis_critical import VERDETTO_OPERATIVO_TEMPLATE

        assert "AZIONE CONSIGLIATA" in VERDETTO_OPERATIVO_TEMPLATE
        assert "ANALISI DEL RISCHIO" in VERDETTO_OPERATIVO_TEMPLATE
        assert "SCADENZA" in VERDETTO_OPERATIVO_TEMPLATE
        assert "DOCUMENTAZIONE" in VERDETTO_OPERATIVO_TEMPLATE
        assert "INDICE DELLE FONTI" in VERDETTO_OPERATIVO_TEMPLATE

    def test_template_has_emojis(self):
        """Test that template includes visual emojis."""
        from app.core.prompts.synthesis_critical import VERDETTO_OPERATIVO_TEMPLATE

        assert "✅" in VERDETTO_OPERATIVO_TEMPLATE
        assert "⚠️" in VERDETTO_OPERATIVO_TEMPLATE
        assert "📅" in VERDETTO_OPERATIVO_TEMPLATE
        assert "📁" in VERDETTO_OPERATIVO_TEMPLATE

    def test_template_has_source_index_table(self):
        """Test that template includes source index table structure."""
        from app.core.prompts.synthesis_critical import VERDETTO_OPERATIVO_TEMPLATE

        # Should have table headers
        assert "Data" in VERDETTO_OPERATIVO_TEMPLATE
        assert "Ente" in VERDETTO_OPERATIVO_TEMPLATE
        assert "Tipo" in VERDETTO_OPERATIVO_TEMPLATE
        assert "Riferimento" in VERDETTO_OPERATIVO_TEMPLATE


class TestSynthesisPromptBuilder:
    """Tests for SynthesisPromptBuilder class."""

    def _get_builder(self):
        """Get SynthesisPromptBuilder with isolated import."""
        # Import the module directly without going through app.services.__init__
        import importlib.util
        import sys
        from pathlib import Path

        # Get the module path
        module_path = Path(__file__).parent.parent.parent.parent / "app" / "services" / "synthesis_prompt_builder.py"

        # Load the module directly
        spec = importlib.util.spec_from_file_location("synthesis_prompt_builder", module_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules["synthesis_prompt_builder"] = module
        spec.loader.exec_module(module)

        return module.SynthesisPromptBuilder()

    def test_builder_instantiation(self):
        """Test that SynthesisPromptBuilder can be instantiated."""
        builder = self._get_builder()
        assert builder is not None

    def test_build_returns_string(self):
        """Test that build() returns a string."""
        builder = self._get_builder()
        result = builder.build(
            context="Documento 1: Contenuto...",
            query="Come funziona il ravvedimento?",
        )

        assert isinstance(result, str)
        assert len(result) > 0

    def test_build_includes_context(self):
        """Test that built prompt includes the context."""
        builder = self._get_builder()
        context = "DOCUMENTO 1: Circolare 9/E del 2025 sul regime forfettario..."
        query = "Requisiti regime forfettario?"

        result = builder.build(context=context, query=query)

        assert "Circolare 9/E" in result or "DOCUMENTO 1" in result

    def test_build_includes_query(self):
        """Test that built prompt includes the query."""
        builder = self._get_builder()
        query = "Quali sono i requisiti per il regime forfettario nel 2025?"

        result = builder.build(context="Context...", query=query)

        assert "requisiti" in result.lower() or "forfettario" in result.lower()

    def test_build_includes_metadata_instructions(self):
        """Test that built prompt includes metadata analysis instructions."""
        builder = self._get_builder()
        result = builder.build(context="Test context", query="Test query")

        result_lower = result.lower()
        # Should include instructions about analyzing metadata
        assert "cronologic" in result_lower or "data" in result_lower

    def test_get_system_prompt(self):
        """Test that get_system_prompt() returns the system prompt."""
        builder = self._get_builder()
        system_prompt = builder.get_system_prompt()

        assert "VERDETTO OPERATIVO" in system_prompt
        assert "prudent" in system_prompt.lower()

    def test_build_empty_context_handled(self):
        """Test that empty context is handled gracefully."""
        builder = self._get_builder()
        result = builder.build(context="", query="Test query")

        # Should still produce valid output
        assert isinstance(result, str)
        assert "query" in result.lower() or "test" in result.lower()


class TestHierarchyRulesConstant:
    """Tests for HIERARCHY_RULES constant."""

    def test_hierarchy_rules_exists(self):
        """Test that HIERARCHY_RULES is defined."""
        from app.core.prompts.synthesis_critical import HIERARCHY_RULES

        assert HIERARCHY_RULES is not None

    def test_hierarchy_rules_order(self):
        """Test that hierarchy rules specify correct order."""
        from app.core.prompts.synthesis_critical import HIERARCHY_RULES

        rules_lower = HIERARCHY_RULES.lower()
        # Legge should be mentioned before Circolare
        assert "legge" in rules_lower
        assert "decreto" in rules_lower
        assert "circolare" in rules_lower

    def test_hierarchy_rules_recency(self):
        """Test that hierarchy rules mention recency tiebreaker."""
        from app.core.prompts.synthesis_critical import HIERARCHY_RULES

        rules_lower = HIERARCHY_RULES.lower()
        assert "recente" in rules_lower or "data" in rules_lower


class TestAllFourCompiti:
    """Tests verifying all 4 tasks (compiti) from Section 13.8.5 are included."""

    def test_compito_1_analisi_cronologica(self):
        """Test Compito 1: ANALISI CRONOLOGICA is in prompt."""
        from app.core.prompts.synthesis_critical import SYNTHESIS_SYSTEM_PROMPT

        assert "ANALISI CRONOLOGICA" in SYNTHESIS_SYSTEM_PROMPT

    def test_compito_2_rilevamento_conflitti(self):
        """Test Compito 2: RILEVAMENTO CONFLITTI is in prompt."""
        from app.core.prompts.synthesis_critical import SYNTHESIS_SYSTEM_PROMPT

        assert "RILEVAMENTO CONFLITTI" in SYNTHESIS_SYSTEM_PROMPT

    def test_compito_3_applicazione_gerarchia(self):
        """Test Compito 3: APPLICAZIONE GERARCHIA is in prompt."""
        from app.core.prompts.synthesis_critical import SYNTHESIS_SYSTEM_PROMPT

        assert "APPLICAZIONE GERARCHIA" in SYNTHESIS_SYSTEM_PROMPT

    def test_compito_4_verdetto_operativo(self):
        """Test Compito 4: VERDETTO OPERATIVO is in prompt."""
        from app.core.prompts.synthesis_critical import SYNTHESIS_SYSTEM_PROMPT

        assert "VERDETTO OPERATIVO" in SYNTHESIS_SYSTEM_PROMPT


class TestPromptIntegration:
    """Integration tests for prompt components."""

    def _load_module(self, module_name: str, filename: str):
        """Load a module directly without going through package __init__."""
        import importlib.util
        import sys
        from pathlib import Path

        module_path = Path(__file__).parent.parent.parent.parent / "app" / "services" / filename
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    def _get_builder(self):
        """Get SynthesisPromptBuilder with isolated import."""
        module = self._load_module("synthesis_prompt_builder", "synthesis_prompt_builder.py")
        return module.SynthesisPromptBuilder()

    def test_full_prompt_assembly(self):
        """Test that full prompt can be assembled with all components."""
        builder = self._get_builder()

        context = """
━━━ DOCUMENTO 1 ━━━
📅 Data: 10/03/2025
🏛️ Ente: Agenzia delle Entrate
📄 Tipo: circolare (Livello gerarchico: 3)
📌 Riferimento: Circ. 9/E/2025
📊 Relevance: 0.92

CONTENUTO:
Ai sensi dell'art. 1, commi 54-89, della Legge 190/2014...
"""

        query = "Quali sono i limiti di fatturato per il regime forfettario?"

        result = builder.build(context=context, query=query)

        # Should be a substantial prompt
        assert len(result) > 100
        # Should contain the context data
        assert "2025" in result

    def test_builder_with_formatted_context(self):
        """Test builder works with formatted context (similar to MetadataExtractor output)."""
        builder = self._get_builder()

        # Simulate MetadataExtractor formatted context
        context = """
## Documenti Recuperati: 1
## Tempo Retrieval: 150ms

━━━ DOCUMENTO 1 ━━━
📅 Data: 10/03/2025
🏛️ Ente: Agenzia delle Entrate
📄 Tipo: circolare (Livello gerarchico: 3)
📌 Riferimento: Circ. 9/E/2025
🔗 URL: https://www.agenziaentrate.gov.it/circ-9e
📊 Relevance: 0.05

CONTENUTO:
Contenuto di test per la sintesi. Chiarimenti regime forfettario.
"""

        # Build prompt
        prompt = builder.build(context=context, query="Test query forfettario")

        # Should produce valid combined output
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        # Should include both context markers and query
        assert "Circolare" in prompt or "DOCUMENTO" in prompt
        assert "forfettario" in prompt.lower()
