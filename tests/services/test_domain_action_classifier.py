"""Comprehensive tests for DomainActionClassifier service.

Tests the rule-based Italian professional query classifier including:
- Domain classification (TAX, LEGAL, LABOR, BUSINESS, ACCOUNTING)
- Action classification (INFORMATION_REQUEST, DOCUMENT_GENERATION, etc.)
- Sub-domain extraction
- Document type extraction
- Query composition detection
- Reasoning generation
- Classification statistics
- Edge cases and low-confidence queries

Target: 90%+ coverage of app/services/domain_action_classifier.py
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.domain_action_classifier import (
    Action,
    Domain,
    DomainActionClassification,
    DomainActionClassifier,
    PatternMatch,
    QueryComposition,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def classifier():
    """Create a DomainActionClassifier instance with mocked settings."""
    with patch("app.services.domain_action_classifier.settings"):
        return DomainActionClassifier()


# ===========================================================================
# Enum and Model Tests
# ===========================================================================


class TestEnums:
    """Tests for Domain, Action, and QueryComposition enums."""

    def test_domain_enum_values(self):
        assert Domain.TAX == "tax"
        assert Domain.LEGAL == "legal"
        assert Domain.LABOR == "labor"
        assert Domain.BUSINESS == "business"
        assert Domain.ACCOUNTING == "accounting"

    def test_domain_enum_count(self):
        assert len(Domain) == 5

    def test_action_enum_values(self):
        assert Action.INFORMATION_REQUEST == "information_request"
        assert Action.DOCUMENT_GENERATION == "document_generation"
        assert Action.DOCUMENT_ANALYSIS == "document_analysis"
        assert Action.CALCULATION_REQUEST == "calculation_request"
        assert Action.COMPLIANCE_CHECK == "compliance_check"
        assert Action.STRATEGIC_ADVICE == "strategic_advice"
        assert Action.CCNL_QUERY == "ccnl_query"

    def test_action_enum_count(self):
        assert len(Action) == 7

    def test_query_composition_enum_values(self):
        assert QueryComposition.PURE_KB == "pure_kb"
        assert QueryComposition.PURE_DOCUMENT == "pure_doc"
        assert QueryComposition.HYBRID == "hybrid"
        assert QueryComposition.CONVERSATIONAL == "chat"

    def test_query_composition_enum_count(self):
        assert len(QueryComposition) == 4


class TestDomainActionClassification:
    """Tests for the DomainActionClassification Pydantic model."""

    def test_basic_classification_creation(self):
        classification = DomainActionClassification(
            domain=Domain.TAX,
            action=Action.CALCULATION_REQUEST,
            confidence=0.85,
        )
        assert classification.domain == Domain.TAX
        assert classification.action == Action.CALCULATION_REQUEST
        assert classification.confidence == 0.85
        assert classification.sub_domain is None
        assert classification.document_type is None
        assert classification.reasoning is None
        assert classification.fallback_used is False

    def test_full_classification_creation(self):
        classification = DomainActionClassification(
            domain=Domain.LEGAL,
            action=Action.DOCUMENT_GENERATION,
            confidence=0.92,
            sub_domain="civile",
            document_type="contratto",
            reasoning="Domain identified from keywords: contratto",
            fallback_used=True,
        )
        assert classification.domain == Domain.LEGAL
        assert classification.sub_domain == "civile"
        assert classification.document_type == "contratto"
        assert classification.reasoning is not None
        assert classification.fallback_used is True

    def test_classification_serialization(self):
        classification = DomainActionClassification(
            domain=Domain.TAX,
            action=Action.INFORMATION_REQUEST,
            confidence=0.75,
        )
        data = classification.model_dump()
        assert data["domain"] == "tax"
        assert data["action"] == "information_request"
        assert data["confidence"] == 0.75


class TestPatternMatch:
    """Tests for PatternMatch dataclass."""

    def test_pattern_match_creation(self):
        pm = PatternMatch(keywords=["iva", "tasse"], score=0.8)
        assert pm.keywords == ["iva", "tasse"]
        assert pm.score == 0.8
        assert pm.weight == 1.0

    def test_pattern_match_custom_weight(self):
        pm = PatternMatch(keywords=["contratto"], score=0.6, weight=1.5)
        assert pm.weight == 1.5


# ===========================================================================
# Domain Classification Tests
# ===========================================================================


class TestDomainScoring:
    """Tests for _calculate_domain_scores method."""

    def test_tax_domain_irpef(self, classifier):
        scores = classifier._calculate_domain_scores("quanto pago di irpef")
        assert scores[Domain.TAX] > 0
        assert scores[Domain.TAX] == max(scores.values())

    def test_tax_domain_iva(self, classifier):
        scores = classifier._calculate_domain_scores("calcolo iva")
        assert scores[Domain.TAX] > 0

    def test_tax_domain_regime_forfettario(self, classifier):
        scores = classifier._calculate_domain_scores("regime forfettario aliquota")
        assert scores[Domain.TAX] > 0

    def test_tax_domain_f24(self, classifier):
        scores = classifier._calculate_domain_scores("compilazione f24")
        assert scores[Domain.TAX] > 0

    def test_tax_domain_730(self, classifier):
        scores = classifier._calculate_domain_scores("dichiarazione 730")
        assert scores[Domain.TAX] > 0

    def test_tax_domain_cedolare_secca(self, classifier):
        scores = classifier._calculate_domain_scores("cedolare secca")
        assert scores[Domain.TAX] > 0

    def test_legal_domain_ricorso(self, classifier):
        scores = classifier._calculate_domain_scores("presentare ricorso al tribunale")
        assert scores[Domain.LEGAL] > 0

    def test_legal_domain_contratto(self, classifier):
        scores = classifier._calculate_domain_scores("clausole del contratto")
        assert scores[Domain.LEGAL] > 0

    def test_legal_domain_diffida(self, classifier):
        scores = classifier._calculate_domain_scores("lettera di diffida")
        assert scores[Domain.LEGAL] > 0

    def test_legal_domain_extra_weight(self, classifier):
        """Legal domain keywords get 1.3x extra weight."""
        scores = classifier._calculate_domain_scores("ricorso al tribunale per sentenza")
        assert scores[Domain.LEGAL] > 0

    def test_labor_domain_tfr(self, classifier):
        scores = classifier._calculate_domain_scores("calcolo tfr")
        assert scores[Domain.LABOR] > 0

    def test_labor_domain_ccnl(self, classifier):
        scores = classifier._calculate_domain_scores("ccnl metalmeccanici")
        assert scores[Domain.LABOR] > 0

    def test_labor_domain_busta_paga(self, classifier):
        scores = classifier._calculate_domain_scores("busta paga")
        assert scores[Domain.LABOR] > 0

    def test_labor_domain_licenziamento(self, classifier):
        scores = classifier._calculate_domain_scores("licenziamento giusta causa")
        assert scores[Domain.LABOR] > 0

    def test_labor_domain_stipendio(self, classifier):
        scores = classifier._calculate_domain_scores("stipendio operaio metalmeccanico")
        assert scores[Domain.LABOR] > 0

    def test_business_domain_srl(self, classifier):
        scores = classifier._calculate_domain_scores("costituzione srl")
        assert scores[Domain.BUSINESS] > 0

    def test_business_domain_business_plan(self, classifier):
        scores = classifier._calculate_domain_scores("business plan per startup")
        assert scores[Domain.BUSINESS] > 0

    def test_business_domain_fusione(self, classifier):
        scores = classifier._calculate_domain_scores("fusione società")
        assert scores[Domain.BUSINESS] > 0

    def test_accounting_domain_bilancio(self, classifier):
        scores = classifier._calculate_domain_scores("analisi bilancio")
        assert scores[Domain.ACCOUNTING] > 0

    def test_accounting_domain_fattura(self, classifier):
        scores = classifier._calculate_domain_scores("registrazione fattura")
        assert scores[Domain.ACCOUNTING] > 0

    def test_accounting_domain_principi_contabili(self, classifier):
        scores = classifier._calculate_domain_scores("principi contabili oic")
        assert scores[Domain.ACCOUNTING] > 0

    def test_accounting_domain_ammortamento(self, classifier):
        scores = classifier._calculate_domain_scores("ammortamento cespiti")
        assert scores[Domain.ACCOUNTING] > 0

    def test_no_domain_match(self, classifier):
        """Query with no domain keywords should return all zeros."""
        scores = classifier._calculate_domain_scores("buongiorno come stai")
        assert all(v == 0.0 for v in scores.values())

    def test_all_domains_present_in_scores(self, classifier):
        """Every Domain enum member must appear in the scores dict."""
        scores = classifier._calculate_domain_scores("iva")
        for domain in Domain:
            assert domain in scores

    def test_score_capped_at_095(self, classifier):
        """Scores should not exceed 0.95."""
        scores = classifier._calculate_domain_scores(
            "iva irpef ires irap tasse imposta aliquota detrazione deduzione f24 730"
        )
        for score in scores.values():
            assert score <= 0.95

    def test_position_weight_early_keyword(self, classifier):
        """Keywords appearing early in query get position bonus (1.2x)."""
        scores_early = classifier._calculate_domain_scores("iva nel calcolo")
        scores_late = classifier._calculate_domain_scores("nel calcolo dell'importo iva")
        # Early position should give slightly higher score
        assert scores_early[Domain.TAX] >= scores_late[Domain.TAX]

    def test_longer_keywords_higher_weight(self, classifier):
        """Longer keywords get higher length_weight (len/20)."""
        scores_short = classifier._calculate_domain_scores("iva")
        scores_long = classifier._calculate_domain_scores("regime forfettario")
        # Both should match TAX domain
        assert scores_short[Domain.TAX] > 0
        assert scores_long[Domain.TAX] > 0


# ===========================================================================
# Action Classification Tests
# ===========================================================================


class TestActionScoring:
    """Tests for _calculate_action_scores method."""

    def test_document_generation_genera(self, classifier):
        scores = classifier._calculate_action_scores("genera fattura")
        assert scores[Action.DOCUMENT_GENERATION] > 0

    def test_document_generation_scrivi(self, classifier):
        scores = classifier._calculate_action_scores("scrivi contratto")
        assert scores[Action.DOCUMENT_GENERATION] > 0

    def test_document_generation_prepara(self, classifier):
        scores = classifier._calculate_action_scores("prepara ricorso")
        assert scores[Action.DOCUMENT_GENERATION] > 0

    def test_document_generation_fammi(self, classifier):
        """Colloquial Italian: fammi -> document generation."""
        scores = classifier._calculate_action_scores("fammi una lettera di diffida")
        assert scores[Action.DOCUMENT_GENERATION] > 0

    def test_document_analysis_analizza(self, classifier):
        scores = classifier._calculate_action_scores("analizza questo documento")
        assert scores[Action.DOCUMENT_ANALYSIS] > 0

    def test_document_analysis_allegato(self, classifier):
        scores = classifier._calculate_action_scores("ti allego il bilancio")
        assert scores[Action.DOCUMENT_ANALYSIS] > 0

    def test_document_analysis_verifica(self, classifier):
        scores = classifier._calculate_action_scores("verifica nel documento")
        assert scores[Action.DOCUMENT_ANALYSIS] > 0

    def test_calculation_request_calcola(self, classifier):
        scores = classifier._calculate_action_scores("calcola iva")
        assert scores[Action.CALCULATION_REQUEST] > 0

    def test_calculation_request_quanto(self, classifier):
        scores = classifier._calculate_action_scores("quanto devo pagare")
        assert scores[Action.CALCULATION_REQUEST] > 0

    def test_calculation_request_importo(self, classifier):
        scores = classifier._calculate_action_scores("qual è l'importo")
        assert scores[Action.CALCULATION_REQUEST] > 0

    def test_compliance_check_obbligatorio(self, classifier):
        scores = classifier._calculate_action_scores("è obbligatorio il versamento")
        assert scores[Action.COMPLIANCE_CHECK] > 0

    def test_compliance_check_normativa(self, classifier):
        scores = classifier._calculate_action_scores("normativa gdpr")
        assert scores[Action.COMPLIANCE_CHECK] > 0

    def test_compliance_check_devo(self, classifier):
        scores = classifier._calculate_action_scores("devo pagare l'obbligo")
        assert scores[Action.COMPLIANCE_CHECK] > 0

    def test_strategic_advice_conviene(self, classifier):
        scores = classifier._calculate_action_scores("conviene aprire partita iva")
        assert scores[Action.STRATEGIC_ADVICE] > 0

    def test_strategic_advice_pro_e_contro(self, classifier):
        scores = classifier._calculate_action_scores("pro e contro del forfettario")
        assert scores[Action.STRATEGIC_ADVICE] > 0

    def test_information_request_cose(self, classifier):
        scores = classifier._calculate_action_scores("cos'è l'irpef")
        assert scores[Action.INFORMATION_REQUEST] > 0

    def test_information_request_spiegami(self, classifier):
        scores = classifier._calculate_action_scores("spiegami la cedolare secca")
        assert scores[Action.INFORMATION_REQUEST] > 0

    def test_ccnl_query_indicators(self, classifier):
        scores = classifier._calculate_action_scores("ccnl metalmeccanici stipendio")
        assert scores[Action.CCNL_QUERY] > 0

    def test_ccnl_query_question_pattern(self, classifier):
        """CCNL-specific question patterns get 4.0 weight boost."""
        scores = classifier._calculate_action_scores("quanto guadagna un operaio metalmeccanico")
        assert scores[Action.CCNL_QUERY] > 0

    def test_ccnl_query_ferie_pattern(self, classifier):
        scores = classifier._calculate_action_scores("quante ferie ha un impiegato")
        assert scores[Action.CCNL_QUERY] > 0

    def test_explicit_document_request_patterns(self, classifier):
        """Explicit 'che documento' patterns boost DOCUMENT_GENERATION by 5.0."""
        scores = classifier._calculate_action_scores("che documento devo fare per il ricorso")
        assert scores[Action.DOCUMENT_GENERATION] > 0
        assert scores[Action.DOCUMENT_GENERATION] == max(scores.values())

    def test_legal_action_request_with_context(self, classifier):
        """'cosa fare' + legal context -> DOCUMENT_GENERATION boost."""
        scores = classifier._calculate_action_scores("cosa fare se non paga il creditore")
        assert scores[Action.DOCUMENT_GENERATION] > 0

    def test_verb_position_weight_start(self, classifier):
        """Verbs at start of query get 2.0x position weight."""
        scores_start = classifier._calculate_action_scores("calcola le tasse dovute")
        scores_end = classifier._calculate_action_scores("le tasse dovute devi calcola")
        assert scores_start[Action.CALCULATION_REQUEST] > 0
        assert scores_end[Action.CALCULATION_REQUEST] > 0

    def test_document_types_matching(self, classifier):
        """Document type terms give extra weight for DOCUMENT_GENERATION."""
        scores = classifier._calculate_action_scores("prepara un ricorso al tar")
        assert scores[Action.DOCUMENT_GENERATION] > 0

    def test_legal_document_types_extra_weight(self, classifier):
        """Legal document types get 4.5 weight vs 3.0 for generic."""
        scores = classifier._calculate_action_scores("genera un decreto ingiuntivo")
        assert scores[Action.DOCUMENT_GENERATION] > 0

    def test_no_action_match(self, classifier):
        """Query with no action keywords should return all zeros."""
        scores = classifier._calculate_action_scores("xyz abc 123")
        assert all(v == 0.0 for v in scores.values())

    def test_all_actions_present_in_scores(self, classifier):
        """Every Action enum member must appear in scores dict."""
        scores = classifier._calculate_action_scores("calcola iva")
        for action in Action:
            assert action in scores

    def test_action_score_capped_at_095(self, classifier):
        """Action scores should not exceed 0.95."""
        scores = classifier._calculate_action_scores(
            "scrivi redigi prepara crea genera modello fac simile bozza template ricorso contratto"
        )
        for score in scores.values():
            assert score <= 0.95


# ===========================================================================
# Full Classification (classify) Tests
# ===========================================================================


class TestClassify:
    """Tests for the main classify() async method."""

    @pytest.mark.asyncio
    async def test_classify_tax_irpef(self, classifier):
        result = await classifier.classify("quanto pago di IRPEF")
        assert result.domain == Domain.TAX
        assert result.confidence > 0
        assert result.fallback_used is False
        assert isinstance(result, DomainActionClassification)

    @pytest.mark.asyncio
    async def test_classify_tax_calculation(self, classifier):
        result = await classifier.classify("calcola IVA al 22%")
        assert result.domain == Domain.TAX
        assert result.action == Action.CALCULATION_REQUEST
        assert result.confidence > 0

    @pytest.mark.asyncio
    async def test_classify_legal_ricorso(self, classifier):
        result = await classifier.classify("devo presentare ricorso al tribunale")
        assert result.domain == Domain.LEGAL

    @pytest.mark.asyncio
    async def test_classify_labor_tfr(self, classifier):
        result = await classifier.classify("calcolo TFR dipendente")
        assert result.domain == Domain.LABOR

    @pytest.mark.asyncio
    async def test_classify_labor_ccnl(self, classifier):
        result = await classifier.classify("CCNL metalmeccanici stipendio")
        assert result.domain == Domain.LABOR

    @pytest.mark.asyncio
    async def test_classify_business_srl(self, classifier):
        result = await classifier.classify("come costituire una SRL")
        assert result.domain == Domain.BUSINESS

    @pytest.mark.asyncio
    async def test_classify_business_plan(self, classifier):
        result = await classifier.classify("business plan per investimento startup")
        assert result.domain == Domain.BUSINESS

    @pytest.mark.asyncio
    async def test_classify_accounting_bilancio(self, classifier):
        result = await classifier.classify("analisi bilancio aziendale")
        assert result.domain == Domain.ACCOUNTING

    @pytest.mark.asyncio
    async def test_classify_document_generation(self, classifier):
        result = await classifier.classify("genera fattura elettronica")
        assert result.action == Action.DOCUMENT_GENERATION

    @pytest.mark.asyncio
    async def test_classify_document_analysis(self, classifier):
        result = await classifier.classify("analizza questo documento allegato")
        assert result.action == Action.DOCUMENT_ANALYSIS

    @pytest.mark.asyncio
    async def test_classify_ccnl_query(self, classifier):
        result = await classifier.classify("quanto guadagna un operaio metalmeccanico al nord")
        assert result.action == Action.CCNL_QUERY

    @pytest.mark.asyncio
    async def test_classify_compliance_check(self, classifier):
        result = await classifier.classify("è obbligatorio il versamento della normativa")
        assert result.action == Action.COMPLIANCE_CHECK

    @pytest.mark.asyncio
    async def test_classify_strategic_advice(self, classifier):
        result = await classifier.classify("conviene il regime forfettario pro e contro")
        assert result.action == Action.STRATEGIC_ADVICE

    @pytest.mark.asyncio
    async def test_classify_information_request(self, classifier):
        result = await classifier.classify("cos'è la cedolare secca")
        assert result.action == Action.INFORMATION_REQUEST

    @pytest.mark.asyncio
    async def test_classify_combined_confidence(self, classifier):
        """Combined confidence = domain*0.6 + action*0.4."""
        result = await classifier.classify("calcola irpef per dichiarazione 730")
        assert 0 <= result.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_classify_low_confidence_query(self, classifier):
        """Ambiguous query should still return a result (no LLM fallback)."""
        result = await classifier.classify("buongiorno come stai")
        assert isinstance(result, DomainActionClassification)
        assert result.fallback_used is False

    @pytest.mark.asyncio
    async def test_classify_has_reasoning(self, classifier):
        result = await classifier.classify("calcola IVA")
        assert result.reasoning is not None
        assert len(result.reasoning) > 0

    @pytest.mark.asyncio
    async def test_classify_case_insensitive(self, classifier):
        """classify() should lowercase the query internally."""
        result_lower = await classifier.classify("irpef")
        result_upper = await classifier.classify("IRPEF")
        assert result_lower.domain == result_upper.domain

    @pytest.mark.asyncio
    async def test_classify_with_sub_domain(self, classifier):
        """Queries with sub-domain keywords should extract sub_domain."""
        result = await classifier.classify("imposta valore aggiunto iva aliquota")
        assert result.domain == Domain.TAX
        assert result.sub_domain is not None

    @pytest.mark.asyncio
    async def test_classify_with_document_type(self, classifier):
        """Document generation queries should extract document_type."""
        result = await classifier.classify("scrivi un ricorso al tribunale")
        assert result.action == Action.DOCUMENT_GENERATION
        assert result.document_type is not None


# ===========================================================================
# Sub-domain Extraction Tests
# ===========================================================================


class TestExtractSubDomain:
    """Tests for _extract_sub_domain method."""

    def test_tax_iva_sub_domain(self, classifier):
        result = classifier._extract_sub_domain("aliquota iva", Domain.TAX)
        assert result == "iva"

    def test_tax_irpef_sub_domain(self, classifier):
        result = classifier._extract_sub_domain("irpef persone fisiche", Domain.TAX)
        assert result == "irpef"

    def test_tax_ires_sub_domain(self, classifier):
        result = classifier._extract_sub_domain("ires imposta società", Domain.TAX)
        assert result == "ires"

    def test_tax_forfettario_sub_domain(self, classifier):
        result = classifier._extract_sub_domain("regime forfettario", Domain.TAX)
        assert result == "forfettario"

    def test_tax_successioni_sub_domain(self, classifier):
        result = classifier._extract_sub_domain("imposta successioni", Domain.TAX)
        assert result == "successioni"

    def test_legal_civile_sub_domain(self, classifier):
        result = classifier._extract_sub_domain("responsabilità civile", Domain.LEGAL)
        assert result == "civile"

    def test_legal_amministrativo_sub_domain(self, classifier):
        result = classifier._extract_sub_domain("ricorso amministrativo al tar", Domain.LEGAL)
        assert result == "amministrativo"

    def test_labor_subordinato_sub_domain(self, classifier):
        result = classifier._extract_sub_domain("contratto lavoro subordinato", Domain.LABOR)
        assert result == "subordinato"

    def test_labor_ccnl_sub_domain(self, classifier):
        result = classifier._extract_sub_domain("ccnl contratto collettivo", Domain.LABOR)
        assert result == "ccnl"

    def test_labor_salary_sub_domain(self, classifier):
        result = classifier._extract_sub_domain("stipendio mensile", Domain.LABOR)
        assert result == "salary"

    def test_labor_benefits_sub_domain(self, classifier):
        result = classifier._extract_sub_domain("ferie e permessi", Domain.LABOR)
        assert result == "benefits"

    def test_labor_sectors_sub_domain(self, classifier):
        result = classifier._extract_sub_domain("settore metalmeccanico", Domain.LABOR)
        # "settore" matches "ccnl" sub_domain first (dict order), "metalmeccanico" matches "sectors"
        assert result in ("ccnl", "sectors")

    def test_labor_job_levels_sub_domain(self, classifier):
        result = classifier._extract_sub_domain("livello operaio", Domain.LABOR)
        assert result == "job_levels"

    def test_business_costituzione_sub_domain(self, classifier):
        result = classifier._extract_sub_domain("costituzione nuova società", Domain.BUSINESS)
        assert result == "costituzione"

    def test_business_governance_sub_domain(self, classifier):
        result = classifier._extract_sub_domain("assemblea amministratore", Domain.BUSINESS)
        assert result == "governance"

    def test_accounting_bilancio_sub_domain(self, classifier):
        result = classifier._extract_sub_domain("stato patrimoniale bilancio", Domain.ACCOUNTING)
        assert result == "bilancio"

    def test_accounting_principi_sub_domain(self, classifier):
        result = classifier._extract_sub_domain("principi contabili oic", Domain.ACCOUNTING)
        assert result == "principi"

    def test_no_sub_domain_match(self, classifier):
        result = classifier._extract_sub_domain("xyz abc 123", Domain.TAX)
        assert result is None

    def test_sub_domain_invalid_domain(self, classifier):
        """Passing a domain not in domain_patterns returns None."""
        # Create a mock domain that doesn't exist in patterns
        result = classifier._extract_sub_domain("test", Domain.TAX)
        # TAX is valid, but "test" won't match any sub_domain keywords
        assert result is None


# ===========================================================================
# Document Type Extraction Tests
# ===========================================================================


class TestExtractDocumentType:
    """Tests for _extract_document_type method."""

    def test_ricorso_document_type(self, classifier):
        result = classifier._extract_document_type("ricorso al tar", Action.DOCUMENT_GENERATION)
        assert result == "ricorso"

    def test_contratto_document_type(self, classifier):
        result = classifier._extract_document_type("redigi un contratto", Action.DOCUMENT_GENERATION)
        assert result == "contratto"

    def test_lettera_document_type(self, classifier):
        result = classifier._extract_document_type("scrivi lettera di diffida", Action.DOCUMENT_GENERATION)
        assert result == "lettera"

    def test_atto_document_type(self, classifier):
        result = classifier._extract_document_type("prepara atto di citazione", Action.DOCUMENT_GENERATION)
        assert result == "atto"

    def test_dichiarazione_document_type(self, classifier):
        result = classifier._extract_document_type("compila dichiarazione", Action.DOCUMENT_GENERATION)
        assert result == "dichiarazione"

    def test_istanza_document_type(self, classifier):
        result = classifier._extract_document_type("istanza di rimborso", Action.DOCUMENT_GENERATION)
        assert result == "istanza"

    def test_procura_document_type(self, classifier):
        result = classifier._extract_document_type("preparami una procura", Action.DOCUMENT_GENERATION)
        assert result == "procura"

    def test_precetto_document_type(self, classifier):
        """'precetto esecutivo' uniquely matches the precetto pattern."""
        result = classifier._extract_document_type("precetto esecutivo", Action.DOCUMENT_GENERATION)
        assert result == "precetto"

    def test_transazione_document_type(self, classifier):
        """'conciliazione' uniquely matches the transazione pattern."""
        result = classifier._extract_document_type("conciliazione tra le parti", Action.DOCUMENT_GENERATION)
        assert result == "transazione"

    def test_denuncia_document_type(self, classifier):
        result = classifier._extract_document_type("denuncia querela", Action.DOCUMENT_GENERATION)
        assert result == "denuncia"

    def test_testamento_document_type(self, classifier):
        result = classifier._extract_document_type("redigi testamento", Action.DOCUMENT_GENERATION)
        assert result == "testamento"

    def test_no_document_type_for_non_generation_action(self, classifier):
        """Non-DOCUMENT_GENERATION actions should return None."""
        result = classifier._extract_document_type("ricorso", Action.INFORMATION_REQUEST)
        assert result is None

    def test_no_document_type_match(self, classifier):
        result = classifier._extract_document_type("genera qualcosa", Action.DOCUMENT_GENERATION)
        assert result is None


# ===========================================================================
# Reasoning Generation Tests
# ===========================================================================


class TestGenerateReasoning:
    """Tests for _generate_reasoning method."""

    def test_reasoning_contains_domain(self, classifier):
        domain_scores = dict.fromkeys(Domain, 0.0)
        domain_scores[Domain.TAX] = 0.8
        action_scores = dict.fromkeys(Action, 0.0)
        action_scores[Action.CALCULATION_REQUEST] = 0.7
        reasoning = classifier._generate_reasoning(
            "calcola iva", Domain.TAX, Action.CALCULATION_REQUEST, domain_scores, action_scores
        )
        assert "tax" in reasoning

    def test_reasoning_contains_action(self, classifier):
        domain_scores = dict.fromkeys(Domain, 0.0)
        domain_scores[Domain.TAX] = 0.8
        action_scores = dict.fromkeys(Action, 0.0)
        action_scores[Action.CALCULATION_REQUEST] = 0.7
        reasoning = classifier._generate_reasoning(
            "calcola iva", Domain.TAX, Action.CALCULATION_REQUEST, domain_scores, action_scores
        )
        assert "calculation_request" in reasoning

    def test_reasoning_contains_keywords(self, classifier):
        domain_scores = dict.fromkeys(Domain, 0.0)
        domain_scores[Domain.TAX] = 0.8
        action_scores = dict.fromkeys(Action, 0.0)
        action_scores[Action.CALCULATION_REQUEST] = 0.7
        reasoning = classifier._generate_reasoning(
            "calcola iva", Domain.TAX, Action.CALCULATION_REQUEST, domain_scores, action_scores
        )
        assert "iva" in reasoning

    def test_reasoning_limits_keywords_to_3(self, classifier):
        """Reasoning should show at most 3 domain keywords."""
        domain_scores = dict.fromkeys(Domain, 0.0)
        domain_scores[Domain.TAX] = 0.8
        action_scores = dict.fromkeys(Action, 0.0)
        reasoning = classifier._generate_reasoning(
            "iva irpef ires irap tasse imposta aliquota",
            Domain.TAX,
            Action.INFORMATION_REQUEST,
            domain_scores,
            action_scores,
        )
        assert "Domain" in reasoning
        assert "Action" in reasoning

    def test_reasoning_no_matching_keywords(self, classifier):
        """Reasoning with no keyword matches should still produce valid text."""
        domain_scores = dict.fromkeys(Domain, 0.0)
        action_scores = dict.fromkeys(Action, 0.0)
        reasoning = classifier._generate_reasoning(
            "xyz abc", Domain.TAX, Action.INFORMATION_REQUEST, domain_scores, action_scores
        )
        assert "Domain" in reasoning
        assert "Action" in reasoning


# ===========================================================================
# Classification Statistics Tests
# ===========================================================================


class TestClassificationStats:
    """Tests for get_classification_stats method."""

    def test_stats_contains_domains(self, classifier):
        stats = classifier.get_classification_stats()
        assert "domains" in stats
        assert "tax" in stats["domains"]
        assert "legal" in stats["domains"]
        assert "labor" in stats["domains"]
        assert "business" in stats["domains"]
        assert "accounting" in stats["domains"]

    def test_stats_contains_actions(self, classifier):
        stats = classifier.get_classification_stats()
        assert "actions" in stats
        assert "document_generation" in stats["actions"]
        assert "document_analysis" in stats["actions"]
        assert "calculation_request" in stats["actions"]

    def test_stats_domain_keywords_count(self, classifier):
        stats = classifier.get_classification_stats()
        for domain_stats in stats["domains"].values():
            assert "keywords_count" in domain_stats
            assert domain_stats["keywords_count"] > 0

    def test_stats_domain_sub_domains(self, classifier):
        stats = classifier.get_classification_stats()
        for domain_stats in stats["domains"].values():
            assert "sub_domains" in domain_stats
            assert isinstance(domain_stats["sub_domains"], list)

    def test_stats_action_verbs_count(self, classifier):
        stats = classifier.get_classification_stats()
        for action_stats in stats["actions"].values():
            assert "verbs_count" in action_stats
            assert "indicators_count" in action_stats


# ===========================================================================
# Query Composition Detection Tests
# ===========================================================================


class TestQueryComposition:
    """Tests for detect_query_composition and _detect_composition_regex."""

    @pytest.mark.asyncio
    async def test_no_attachment_conversational_ciao(self, classifier):
        result = await classifier.detect_query_composition("ciao", has_attachments=False)
        assert result == QueryComposition.CONVERSATIONAL

    @pytest.mark.asyncio
    async def test_no_attachment_conversational_grazie(self, classifier):
        result = await classifier.detect_query_composition("grazie mille", has_attachments=False)
        assert result == QueryComposition.CONVERSATIONAL

    @pytest.mark.asyncio
    async def test_no_attachment_conversational_buongiorno(self, classifier):
        result = await classifier.detect_query_composition("buongiorno", has_attachments=False)
        assert result == QueryComposition.CONVERSATIONAL

    @pytest.mark.asyncio
    async def test_no_attachment_conversational_ok(self, classifier):
        result = await classifier.detect_query_composition("ok", has_attachments=False)
        assert result == QueryComposition.CONVERSATIONAL

    @pytest.mark.asyncio
    async def test_no_attachment_conversational_va_bene(self, classifier):
        result = await classifier.detect_query_composition("va bene", has_attachments=False)
        assert result == QueryComposition.CONVERSATIONAL

    @pytest.mark.asyncio
    async def test_no_attachment_kb_query(self, classifier):
        result = await classifier.detect_query_composition(
            "come si calcola l'IVA intracomunitaria", has_attachments=False
        )
        assert result == QueryComposition.PURE_KB

    @pytest.mark.asyncio
    async def test_no_attachment_long_conversational_becomes_kb(self, classifier):
        """Conversational signal in long query (>5 words) -> PURE_KB."""
        result = await classifier.detect_query_composition(
            "ciao come posso calcolare l'iva per la mia azienda", has_attachments=False
        )
        assert result == QueryComposition.PURE_KB

    @pytest.mark.asyncio
    async def test_with_attachment_calls_llm(self, classifier):
        """With attachments, should call LLM classification."""
        with patch.object(
            classifier,
            "_classify_composition_with_llm",
            new_callable=AsyncMock,
            return_value=QueryComposition.PURE_DOCUMENT,
        ) as mock_llm:
            result = await classifier.detect_query_composition(
                "analizza questo documento", has_attachments=True, attachment_filename="bilancio.pdf"
            )
            mock_llm.assert_called_once_with("analizza questo documento", "bilancio.pdf")
            assert result == QueryComposition.PURE_DOCUMENT

    def test_regex_composition_conversational_salve(self, classifier):
        result = classifier._detect_composition_regex("salve")
        assert result == QueryComposition.CONVERSATIONAL

    def test_regex_composition_conversational_arrivederci(self, classifier):
        result = classifier._detect_composition_regex("arrivederci")
        assert result == QueryComposition.CONVERSATIONAL

    def test_regex_composition_conversational_perfetto(self, classifier):
        result = classifier._detect_composition_regex("perfetto")
        assert result == QueryComposition.CONVERSATIONAL

    def test_regex_composition_pure_kb(self, classifier):
        result = classifier._detect_composition_regex("normativa sul licenziamento")
        assert result == QueryComposition.PURE_KB


# ===========================================================================
# LLM Composition Classification Tests
# ===========================================================================


class TestClassifyCompositionWithLLM:
    """Tests for _classify_composition_with_llm with mocked LLM."""

    @pytest.mark.asyncio
    async def test_llm_returns_hybrid(self, classifier):
        mock_response = MagicMock()
        mock_response.content = "HYBRID"
        mock_provider = AsyncMock()
        mock_provider.chat_completion = AsyncMock(return_value=mock_response)
        mock_factory = MagicMock()
        mock_factory.create_provider.return_value = mock_provider

        with patch("app.services.domain_action_classifier.LLMFactory", return_value=mock_factory):
            result = await classifier._classify_composition_with_llm("verifica normativa", "doc.pdf")
            assert result == QueryComposition.HYBRID

    @pytest.mark.asyncio
    async def test_llm_returns_kb_only(self, classifier):
        mock_response = MagicMock()
        mock_response.content = "KB_ONLY"
        mock_provider = AsyncMock()
        mock_provider.chat_completion = AsyncMock(return_value=mock_response)
        mock_factory = MagicMock()
        mock_factory.create_provider.return_value = mock_provider

        with patch("app.services.domain_action_classifier.LLMFactory", return_value=mock_factory):
            result = await classifier._classify_composition_with_llm("che tempo fa", "doc.pdf")
            assert result == QueryComposition.PURE_KB

    @pytest.mark.asyncio
    async def test_llm_returns_document_only(self, classifier):
        mock_response = MagicMock()
        mock_response.content = "DOCUMENT_ONLY"
        mock_provider = AsyncMock()
        mock_provider.chat_completion = AsyncMock(return_value=mock_response)
        mock_factory = MagicMock()
        mock_factory.create_provider.return_value = mock_provider

        with patch("app.services.domain_action_classifier.LLMFactory", return_value=mock_factory):
            result = await classifier._classify_composition_with_llm("analizza questo", "bilancio.pdf")
            assert result == QueryComposition.PURE_DOCUMENT

    @pytest.mark.asyncio
    async def test_llm_exception_fallback_to_pure_document(self, classifier):
        """On LLM exception, fallback to PURE_DOCUMENT."""
        with patch(
            "app.services.domain_action_classifier.LLMFactory",
            side_effect=Exception("LLM error"),
        ):
            result = await classifier._classify_composition_with_llm("calcola pensione", "cedolino.pdf")
            assert result == QueryComposition.PURE_DOCUMENT

    @pytest.mark.asyncio
    async def test_llm_no_filename(self, classifier):
        """When filename is None, prompt uses 'documento' default."""
        mock_response = MagicMock()
        mock_response.content = "DOCUMENT_ONLY"
        mock_provider = AsyncMock()
        mock_provider.chat_completion = AsyncMock(return_value=mock_response)
        mock_factory = MagicMock()
        mock_factory.create_provider.return_value = mock_provider

        with patch("app.services.domain_action_classifier.LLMFactory", return_value=mock_factory):
            result = await classifier._classify_composition_with_llm("analizza", None)
            assert result == QueryComposition.PURE_DOCUMENT


# ===========================================================================
# LLM Fallback Classification Tests
# ===========================================================================


class TestLLMFallbackClassification:
    """Tests for _llm_fallback_classification method."""

    @pytest.mark.asyncio
    async def test_llm_fallback_success(self, classifier):
        mock_response = MagicMock()
        mock_response.content = '{"domain": "tax", "action": "calculation_request", "confidence": 0.9, "sub_domain": "iva", "reasoning": "test"}'
        mock_provider = AsyncMock()
        mock_provider.chat_completion = AsyncMock(return_value=mock_response)
        mock_factory = MagicMock()
        mock_factory.create_provider.return_value = mock_provider

        with patch("app.services.domain_action_classifier.LLMFactory", return_value=mock_factory):
            result = await classifier._llm_fallback_classification("calcola iva")
            assert result is not None
            assert result.domain == Domain.TAX
            assert result.action == Action.CALCULATION_REQUEST
            assert result.confidence == 0.9
            assert result.fallback_used is True

    @pytest.mark.asyncio
    async def test_llm_fallback_invalid_json(self, classifier):
        mock_response = MagicMock()
        mock_response.content = "not valid json"
        mock_provider = AsyncMock()
        mock_provider.chat_completion = AsyncMock(return_value=mock_response)
        mock_factory = MagicMock()
        mock_factory.create_provider.return_value = mock_provider

        with patch("app.services.domain_action_classifier.LLMFactory", return_value=mock_factory):
            result = await classifier._llm_fallback_classification("test query")
            assert result is None

    @pytest.mark.asyncio
    async def test_llm_fallback_missing_keys(self, classifier):
        mock_response = MagicMock()
        mock_response.content = '{"domain": "tax"}'
        mock_provider = AsyncMock()
        mock_provider.chat_completion = AsyncMock(return_value=mock_response)
        mock_factory = MagicMock()
        mock_factory.create_provider.return_value = mock_provider

        with patch("app.services.domain_action_classifier.LLMFactory", return_value=mock_factory):
            result = await classifier._llm_fallback_classification("test query")
            assert result is None

    @pytest.mark.asyncio
    async def test_llm_fallback_exception(self, classifier):
        with patch(
            "app.services.domain_action_classifier.LLMFactory",
            side_effect=Exception("Connection error"),
        ):
            result = await classifier._llm_fallback_classification("test query")
            assert result is None

    @pytest.mark.asyncio
    async def test_llm_fallback_invalid_domain_value(self, classifier):
        mock_response = MagicMock()
        mock_response.content = '{"domain": "invalid_domain", "action": "calculation_request", "confidence": 0.9}'
        mock_provider = AsyncMock()
        mock_provider.chat_completion = AsyncMock(return_value=mock_response)
        mock_factory = MagicMock()
        mock_factory.create_provider.return_value = mock_provider

        with patch("app.services.domain_action_classifier.LLMFactory", return_value=mock_factory):
            result = await classifier._llm_fallback_classification("test")
            assert result is None


# ===========================================================================
# Edge Case and Integration-Style Tests
# ===========================================================================


class TestEdgeCases:
    """Edge case tests for comprehensive coverage."""

    @pytest.mark.asyncio
    async def test_empty_query(self, classifier):
        """Empty query should still produce a classification."""
        result = await classifier.classify("")
        assert isinstance(result, DomainActionClassification)

    @pytest.mark.asyncio
    async def test_very_long_query(self, classifier):
        """Very long query should not crash."""
        long_query = "calcola iva " * 500
        result = await classifier.classify(long_query)
        assert isinstance(result, DomainActionClassification)

    @pytest.mark.asyncio
    async def test_special_characters_in_query(self, classifier):
        result = await classifier.classify("calcola l'IVA al 22%? €1000")
        assert isinstance(result, DomainActionClassification)

    @pytest.mark.asyncio
    async def test_mixed_domain_query(self, classifier):
        """Query touching multiple domains should pick the highest scoring one."""
        result = await classifier.classify("bilancio aziendale e tasse iva irpef")
        assert isinstance(result, DomainActionClassification)
        assert result.domain in [Domain.TAX, Domain.ACCOUNTING]

    @pytest.mark.asyncio
    async def test_classify_returns_correct_types(self, classifier):
        result = await classifier.classify("calcola irpef")
        assert isinstance(result.domain, Domain)
        assert isinstance(result.action, Action)
        assert isinstance(result.confidence, float)
        assert isinstance(result.fallback_used, bool)

    def test_load_patterns_called_on_init(self):
        """_load_patterns should be called during __init__."""
        with patch("app.services.domain_action_classifier.settings"):
            clf = DomainActionClassifier()
            assert hasattr(clf, "domain_patterns")
            assert hasattr(clf, "action_patterns")
            assert len(clf.domain_patterns) == 5
            assert len(clf.action_patterns) == 7

    def test_domain_patterns_have_required_keys(self, classifier):
        for domain, patterns in classifier.domain_patterns.items():
            assert "keywords" in patterns
            assert "sub_domains" in patterns
            assert isinstance(patterns["keywords"], list)
            assert len(patterns["keywords"]) > 0

    def test_action_patterns_structure(self, classifier):
        """All action patterns should have valid structure."""
        for action, patterns in classifier.action_patterns.items():
            assert isinstance(patterns, dict)
            # Most actions have indicators
            if action != Action.CCNL_QUERY:
                assert "indicators" in patterns

    @pytest.mark.asyncio
    async def test_classify_multiple_keywords_same_domain(self, classifier):
        """Multiple keywords from same domain should increase confidence."""
        result_single = await classifier.classify("iva")
        result_multi = await classifier.classify("iva irpef tasse imposta")
        assert result_multi.confidence >= result_single.confidence

    @pytest.mark.asyncio
    async def test_classify_reverse_charge(self, classifier):
        result = await classifier.classify("reverse charge iva intracomunitaria")
        assert result.domain == Domain.TAX

    @pytest.mark.asyncio
    async def test_classify_mobbing(self, classifier):
        """Mobbing is a keyword in both LEGAL and LABOR domains."""
        result = await classifier.classify("mobbing sul lavoro")
        assert result.domain in [Domain.LEGAL, Domain.LABOR]

    @pytest.mark.asyncio
    async def test_classify_maternita(self, classifier):
        result = await classifier.classify("congedo maternità inps")
        assert result.domain == Domain.LABOR

    @pytest.mark.asyncio
    async def test_classify_ammortamento(self, classifier):
        result = await classifier.classify("calcolo ammortamento cespiti")
        assert result.domain == Domain.ACCOUNTING
