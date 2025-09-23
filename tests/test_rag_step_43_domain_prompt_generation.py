"""
Tests for RAG STEP 43 — PromptTemplateManager.get_prompt Get domain-specific prompt

This step generates domain-specific prompts when classification confidence is high enough.
It takes domain-action classification and creates specialized prompts for Italian professionals
in tax, legal, labor, business, and accounting domains.
"""

import pytest
from unittest.mock import MagicMock, patch

from app.services.domain_prompt_templates import PromptTemplateManager
from app.services.domain_action_classifier import Domain, Action


class TestRAGStep43DomainPromptGeneration:
    """Test suite for RAG STEP 43 - PromptTemplateManager.get_prompt Get domain-specific prompt."""

    @pytest.fixture
    def prompt_template_manager(self):
        """Create PromptTemplateManager instance for testing."""
        return PromptTemplateManager()

    @pytest.mark.asyncio
    @patch('app.services.domain_prompt_templates.rag_step_log')
    async def test_step_43_tax_information_request(
        self,
        mock_log,
        prompt_template_manager
    ):
        """Test STEP 43: Generate tax domain information request prompt."""

        result = prompt_template_manager.get_prompt(
            domain=Domain.TAX,
            action=Action.INFORMATION_REQUEST,
            query="What are the IVA rates for 2024?",
            context=None,
            document_type=None
        )

        # Should generate a domain-specific prompt
        assert isinstance(result, str)
        assert len(result) > 100  # Should be substantial prompt
        assert "Dottore Commercialista" in result  # Tax professional role
        assert "normativa fiscale italiana" in result  # Italian tax law reference

        # Verify structured logging for STEP 43
        mock_log.assert_called()

        # Find the STEP 43 log call
        step_43_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 43
        ]

        assert len(step_43_logs) > 0
        log_call = step_43_logs[0]
        assert log_call[1]['step'] == 43
        assert log_call[1]['step_id'] == "RAG.classify.prompttemplatemanager.get.prompt.get.domain.specific.prompt"
        assert log_call[1]['node_label'] == "DomainPrompt"
        assert log_call[1]['domain'] == Domain.TAX.value
        assert log_call[1]['action'] == Action.INFORMATION_REQUEST.value
        assert log_call[1]['user_query'] == "What are the IVA rates for 2024?"

    @pytest.mark.asyncio
    @patch('app.services.domain_prompt_templates.rag_step_log')
    async def test_step_43_legal_document_generation(
        self,
        mock_log,
        prompt_template_manager
    ):
        """Test STEP 43: Generate legal domain document generation prompt."""

        result = prompt_template_manager.get_prompt(
            domain=Domain.LEGAL,
            action=Action.DOCUMENT_GENERATION,
            query="I need a diffida letter for unpaid invoices",
            context=None,
            document_type="lettera_diffida"
        )

        # Should generate legal-specific prompt
        assert isinstance(result, str)
        assert "Avvocato esperto" in result  # Legal professional role
        assert "diritto civile" in result  # Civil law reference
        assert "DOCUMENTO RICHIESTO: LETTERA_DIFFIDA" in result  # Document type

        # Verify STEP 43 logging
        step_43_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 43
        ]

        assert len(step_43_logs) > 0
        log_call = step_43_logs[0]
        assert log_call[1]['domain'] == Domain.LEGAL.value
        assert log_call[1]['action'] == Action.DOCUMENT_GENERATION.value
        assert log_call[1]['document_type'] == "lettera_diffida"

    @pytest.mark.asyncio
    @patch('app.services.domain_prompt_templates.rag_step_log')
    async def test_step_43_labor_calculation_request(
        self,
        mock_log,
        prompt_template_manager
    ):
        """Test STEP 43: Generate labor domain calculation request prompt."""

        result = prompt_template_manager.get_prompt(
            domain=Domain.LABOR,
            action=Action.CALCULATION_REQUEST,
            query="Calculate severance payment for 5 years employment",
            context=None,
            document_type=None
        )

        # Should generate labor-specific calculation prompt
        assert isinstance(result, str)
        assert "Consulente del Lavoro" in result  # Labor consultant role
        assert "CCNL" in result  # Labor agreements reference

        # Verify STEP 43 logging
        step_43_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 43
        ]

        assert len(step_43_logs) > 0
        log_call = step_43_logs[0]
        assert log_call[1]['domain'] == Domain.LABOR.value
        assert log_call[1]['action'] == Action.CALCULATION_REQUEST.value

    @pytest.mark.asyncio
    @patch('app.services.domain_prompt_templates.rag_step_log')
    async def test_step_43_business_strategic_advice(
        self,
        mock_log,
        prompt_template_manager
    ):
        """Test STEP 43: Generate business domain strategic advice prompt."""

        result = prompt_template_manager.get_prompt(
            domain=Domain.BUSINESS,
            action=Action.STRATEGIC_ADVICE,
            query="How to expand my business internationally?",
            context=None,
            document_type=None
        )

        # Should generate business-specific strategic prompt
        assert isinstance(result, str)
        assert "Consulente aziendale" in result or "consulente" in result.lower()  # Business consultant role
        assert "strateg" in result.lower()  # Strategic reference

        # Verify STEP 43 logging
        step_43_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 43
        ]

        assert len(step_43_logs) > 0
        log_call = step_43_logs[0]
        assert log_call[1]['domain'] == Domain.BUSINESS.value
        assert log_call[1]['action'] == Action.STRATEGIC_ADVICE.value

    @pytest.mark.asyncio
    @patch('app.services.domain_prompt_templates.rag_step_log')
    async def test_step_43_accounting_compliance_check(
        self,
        mock_log,
        prompt_template_manager
    ):
        """Test STEP 43: Generate accounting domain compliance check prompt."""

        result = prompt_template_manager.get_prompt(
            domain=Domain.ACCOUNTING,
            action=Action.COMPLIANCE_CHECK,
            query="Check compliance with OIC 29 standard",
            context=None,
            document_type=None
        )

        # Should generate accounting-specific prompt
        assert isinstance(result, str)
        assert "Revisore Contabile" in result or "commercialista" in result.lower()  # Accounting professional

        # Verify STEP 43 logging
        step_43_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 43
        ]

        assert len(step_43_logs) > 0
        log_call = step_43_logs[0]
        assert log_call[1]['domain'] == Domain.ACCOUNTING.value
        assert log_call[1]['action'] == Action.COMPLIANCE_CHECK.value
        assert log_call[1]['has_context'] is False

    @pytest.mark.asyncio
    @patch('app.services.domain_prompt_templates.rag_step_log')
    async def test_step_43_tax_ccnl_query(
        self,
        mock_log,
        prompt_template_manager
    ):
        """Test STEP 43: Generate prompt with context."""

        context = {
            "calculation_parameters": {"salary": 30000, "months": 12}
        }

        result = prompt_template_manager.get_prompt(
            domain=Domain.TAX,
            action=Action.CCNL_QUERY,
            query="What CCNL applies to tax consultants?",
            context=context,
            document_type=None
        )

        # Should generate prompt with context
        assert isinstance(result, str)
        assert "CONTESTO AGGIUNTIVO" in result  # Context section

        # Verify STEP 43 logging includes context
        step_43_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 43
        ]

        assert len(step_43_logs) > 0
        log_call = step_43_logs[0]
        assert log_call[1]['has_context'] is True
        assert 'context_keys' in log_call[1]

    @pytest.mark.asyncio
    @patch('app.services.domain_prompt_templates.rag_step_log')
    async def test_step_43_prompt_customization_with_context(
        self,
        mock_log,
        prompt_template_manager
    ):
        """Test STEP 43: Prompt customization with additional context."""

        context = {
            "user_profile": {"profession": "Commercialista", "experience": "10+ years"},
            "related_documents": [{"type": "fattura", "id": "001"}, {"type": "ricevuta", "id": "002"}],
            "regulatory_updates": [{"date": "2024-01-15", "topic": "IVA changes"}]
        }

        result = prompt_template_manager.get_prompt(
            domain=Domain.TAX,
            action=Action.DOCUMENT_ANALYSIS,
            query="Analyze these invoices for tax compliance",
            context=context,
            document_type=None
        )

        # Should include context information
        assert "CONTESTO AGGIUNTIVO" in result
        assert "Commercialista" in result  # User profile
        assert "2 documenti disponibili" in result  # Related documents
        assert "1 modifiche" in result  # Regulatory updates

        # Verify STEP 43 logging includes context details
        step_43_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 43
        ]

        assert len(step_43_logs) > 0
        log_call = step_43_logs[0]
        assert log_call[1]['has_context'] is True
        assert "user_profile" in log_call[1]['context_keys']
        assert "related_documents" in log_call[1]['context_keys']

    @pytest.mark.asyncio
    @patch('app.services.domain_prompt_templates.rag_step_log')
    async def test_step_43_error_handling_invalid_domain_action(
        self,
        mock_log,
        prompt_template_manager
    ):
        """Test STEP 43: Error handling for invalid domain-action combinations."""

        # Test with a domain-action combination that might not have specific templates
        result = prompt_template_manager.get_prompt(
            domain=Domain.ACCOUNTING,  # Less common domain
            action=Action.CCNL_QUERY,   # Labor-specific action
            query="CCNL for accounting professionals",
            context=None,
            document_type=None
        )

        # Should still generate a prompt (fallback to default templates)
        assert isinstance(result, str)
        assert len(result) > 50

        # Verify STEP 43 logging handles the case
        step_43_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 43
        ]

        assert len(step_43_logs) > 0
        log_call = step_43_logs[0]
        assert log_call[1]['domain'] == Domain.ACCOUNTING.value
        assert log_call[1]['action'] == Action.CCNL_QUERY.value
        # Should log that it used fallback templates
        assert 'template_source' in log_call[1]

    @pytest.mark.asyncio
    @patch('app.services.domain_prompt_templates.rag_step_log')
    async def test_step_43_comprehensive_logging_format(
        self,
        mock_log,
        prompt_template_manager
    ):
        """Test STEP 43: Comprehensive structured logging format."""

        result = prompt_template_manager.get_prompt(
            domain=Domain.TAX,
            action=Action.INFORMATION_REQUEST,
            query="IVA exemptions for non-profit organizations",
            context={"user_profile": {"profession": "Commercialista"}},
            document_type=None
        )

        # Verify all required STEP 43 logging fields
        step_43_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 43
        ]

        assert len(step_43_logs) > 0
        log_call = step_43_logs[0]

        required_fields = [
            'step', 'step_id', 'node_label', 'domain', 'action',
            'user_query', 'has_context', 'has_specific_combination',
            'template_source', 'prompt_length', 'processing_stage'
        ]

        for field in required_fields:
            assert field in log_call[1], f"Missing required field: {field}"

        # Verify specific values
        assert log_call[1]['step'] == 43
        assert log_call[1]['step_id'] == "RAG.classify.prompttemplatemanager.get.prompt.get.domain.specific.prompt"
        assert log_call[1]['node_label'] == "DomainPrompt"
        assert log_call[1]['domain'] == Domain.TAX.value
        assert log_call[1]['action'] == Action.INFORMATION_REQUEST.value
        assert log_call[1]['user_query'] == "IVA exemptions for non-profit organizations"
        assert isinstance(log_call[1]['prompt_length'], int)
        assert log_call[1]['prompt_length'] > 0

    @pytest.mark.asyncio
    @patch('app.services.domain_prompt_templates.rag_step_log')
    async def test_step_43_performance_tracking_with_timer(
        self,
        mock_log,
        prompt_template_manager
    ):
        """Test STEP 43: Performance tracking with timer context."""

        with patch('app.services.domain_prompt_templates.rag_step_timer') as mock_timer:
            # Mock the timer context manager
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            result = prompt_template_manager.get_prompt(
                domain=Domain.LEGAL,
                action=Action.DOCUMENT_ANALYSIS,
                query="Review contract clauses for legal compliance",
                context=None,
                document_type=None
            )

            # Verify timer was used for STEP 43
            mock_timer.assert_called_once_with(
                43,
                "RAG.classify.prompttemplatemanager.get.prompt.get.domain.specific.prompt",
                "DomainPrompt",
                domain=Domain.LEGAL.value,
                action=Action.DOCUMENT_ANALYSIS.value
            )

    @pytest.mark.asyncio
    @patch('app.services.domain_prompt_templates.rag_step_log')
    async def test_step_43_all_domain_action_combinations(
        self,
        mock_log,
        prompt_template_manager
    ):
        """Test STEP 43: Test all domain-action combinations."""

        # Test key domain-action combinations
        test_cases = [
            (Domain.TAX, Action.INFORMATION_REQUEST, "IVA rates"),
            (Domain.LEGAL, Action.DOCUMENT_GENERATION, "Legal contract"),
            (Domain.LABOR, Action.CCNL_QUERY, "CCNL inquiry"),
            (Domain.BUSINESS, Action.STRATEGIC_ADVICE, "Business growth"),
            (Domain.ACCOUNTING, Action.COMPLIANCE_CHECK, "OIC compliance")
        ]

        for domain, action, query in test_cases:
            # Clear mock logs for each iteration
            mock_log.reset_mock()

            result = prompt_template_manager.get_prompt(
                domain=domain,
                action=action,
                query=query,
                context=None,
                document_type=None
            )

            # Should generate domain-specific prompt
            assert isinstance(result, str)
            assert len(result) > 50

            # Verify STEP 43 logging for each domain
            step_43_logs = [
                call for call in mock_log.call_args_list
                if len(call[1]) > 3 and call[1].get('step') == 43
            ]

            assert len(step_43_logs) > 0, f"No STEP 43 logging found for {domain.value}"
            log_call = step_43_logs[0]
            assert log_call[1]['domain'] == domain.value
            assert log_call[1]['action'] == action.value
            assert log_call[1]['user_query'] == query


class TestRAGStep43Orchestrator:
    """Test suite for RAG STEP 43 Orchestrator - step_43__domain_prompt orchestration function."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    async def test_step_43_orchestrator_success(self, mock_rag_log):
        """Test Step 43: Orchestrator successfully generates domain prompt."""
        from app.orchestrators.classify import step_43__domain_prompt
        from app.services.domain_action_classifier import DomainActionClassification, Domain, Action
        from unittest.mock import MagicMock

        # Mock PromptTemplateManager
        mock_prompt_manager = MagicMock()
        mock_prompt_manager.get_prompt.return_value = "Domain-specific tax consultation prompt."

        # Create classification
        classification = DomainActionClassification(
            domain=Domain.TAX,
            action=Action.INFORMATION_REQUEST,
            confidence=0.85,
            document_type=None
        )

        # Call orchestrator
        ctx = {
            'classification': classification,
            'prompt_template_manager': mock_prompt_manager,
            'user_query': 'What are the IVA rates?',
            'request_id': 'test-43-success'
        }

        result = await step_43__domain_prompt(messages=[], ctx=ctx)

        # Verify result structure
        assert isinstance(result, dict)
        assert result['domain_prompt'] == "Domain-specific tax consultation prompt."
        assert result['prompt_generated'] is True
        assert result['domain'] == 'tax'
        assert result['action'] == 'information_request'
        assert result['prompt_length'] > 0
        assert result['error_occurred'] is False
        assert result['request_id'] == 'test-43-success'

        # Verify PromptTemplateManager was called correctly
        mock_prompt_manager.get_prompt.assert_called_once_with(
            domain=classification.domain,
            action=classification.action,
            query='What are the IVA rates?',
            context=None,
            document_type=None
        )

        # Verify orchestrator logging
        assert mock_rag_log.call_count >= 2  # start and completed
        start_call = None
        completed_call = None

        for call in mock_rag_log.call_args_list:
            if call[1].get('processing_stage') == 'started':
                start_call = call[1]
            elif call[1].get('processing_stage') == 'completed':
                completed_call = call[1]

        assert start_call is not None
        assert start_call['step'] == 43
        assert start_call['node_label'] == 'DomainPrompt'

        assert completed_call is not None
        assert completed_call['prompt_generated'] is True
        assert completed_call['orchestration_result'] == 'success'

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_43_orchestrator_error_handling(self, mock_logger, mock_rag_log):
        """Test Step 43: Orchestrator handles errors gracefully."""
        from app.orchestrators.classify import step_43__domain_prompt
        from app.services.domain_action_classifier import DomainActionClassification, Domain, Action
        from unittest.mock import MagicMock

        # Mock PromptTemplateManager that raises an error
        mock_prompt_manager = MagicMock()
        mock_prompt_manager.get_prompt.side_effect = Exception("Template generation failed")

        # Create classification
        classification = DomainActionClassification(
            domain=Domain.LEGAL,
            action=Action.DOCUMENT_GENERATION,
            confidence=0.75,
            document_type="contratto"
        )

        # Call orchestrator
        ctx = {
            'classification': classification,
            'prompt_template_manager': mock_prompt_manager,
            'user_query': 'Generate a contract',
            'request_id': 'test-43-error'
        }

        result = await step_43__domain_prompt(messages=[], ctx=ctx)

        # Verify error handling
        assert result['domain_prompt'] == ""  # Empty prompt on error
        assert result['prompt_generated'] is False
        assert result['error_occurred'] is True
        assert result['error_message'] == "Template generation failed"
        assert result['domain'] == 'legal'
        assert result['action'] == 'document_generation'

        # Verify error was logged
        mock_logger.error.assert_called_once()

        # Verify orchestrator completion logging
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log['prompt_generated'] is False
        assert completed_log['orchestration_result'] == 'fallback'
        assert completed_log['error_occurred'] is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    async def test_step_43_orchestrator_no_classification(self, mock_rag_log):
        """Test Step 43: Orchestrator handles missing classification."""
        from app.orchestrators.classify import step_43__domain_prompt

        # Call orchestrator without classification
        ctx = {
            'user_query': 'Generate something',
            'request_id': 'test-43-no-class'
        }

        result = await step_43__domain_prompt(messages=[], ctx=ctx)

        # Verify error handling for missing classification
        assert result['domain_prompt'] == ""
        assert result['prompt_generated'] is False
        assert result['error_occurred'] is True
        assert "Classification is required" in result['error_message']

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    async def test_step_43_orchestrator_creates_manager_if_missing(self, mock_rag_log):
        """Test Step 43: Orchestrator creates PromptTemplateManager if not provided."""
        from app.orchestrators.classify import step_43__domain_prompt
        from app.services.domain_action_classifier import DomainActionClassification, Domain, Action

        # Create classification
        classification = DomainActionClassification(
            domain=Domain.BUSINESS,
            action=Action.STRATEGIC_ADVICE,
            confidence=0.70,
            document_type=None
        )

        # Call orchestrator without prompt_template_manager
        ctx = {
            'classification': classification,
            'user_query': 'Business expansion strategy',
            'request_id': 'test-43-no-manager'
        }

        result = await step_43__domain_prompt(messages=[], ctx=ctx)

        # Should still generate a prompt (creates its own manager)
        assert result['prompt_generated'] is True
        assert result['domain_prompt'] != ""
        assert result['domain'] == 'business'
        assert result['action'] == 'strategic_advice'

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    async def test_step_43_orchestrator_with_context(self, mock_rag_log):
        """Test Step 43: Orchestrator passes through prompt context."""
        from app.orchestrators.classify import step_43__domain_prompt
        from app.services.domain_action_classifier import DomainActionClassification, Domain, Action
        from unittest.mock import MagicMock

        # Mock PromptTemplateManager
        mock_prompt_manager = MagicMock()
        mock_prompt_manager.get_prompt.return_value = "Prompt with context included."

        # Create classification
        classification = DomainActionClassification(
            domain=Domain.ACCOUNTING,
            action=Action.COMPLIANCE_CHECK,
            confidence=0.80,
            document_type=None
        )

        # Call orchestrator with context
        prompt_context = {
            'user_profile': {'profession': 'Commercialista'},
            'regulatory_updates': [{'topic': 'OIC 29'}]
        }

        ctx = {
            'classification': classification,
            'prompt_template_manager': mock_prompt_manager,
            'user_query': 'Check OIC compliance',
            'prompt_context': prompt_context,
            'request_id': 'test-43-context'
        }

        result = await step_43__domain_prompt(messages=[], ctx=ctx, prompt_context=prompt_context)

        # Verify context was passed through
        mock_prompt_manager.get_prompt.assert_called_once_with(
            domain=classification.domain,
            action=classification.action,
            query='Check OIC compliance',
            context=prompt_context,
            document_type=None
        )

        assert result['prompt_generated'] is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    async def test_step_43_parity_behavior_preservation(self, mock_rag_log):
        """Test Step 43: Parity test proving identical behavior before/after orchestrator."""
        from app.orchestrators.classify import step_43__domain_prompt
        from app.services.domain_prompt_templates import PromptTemplateManager
        from app.services.domain_action_classifier import DomainActionClassification, Domain, Action

        # Create classification
        classification = DomainActionClassification(
            domain=Domain.TAX,
            action=Action.INFORMATION_REQUEST,
            confidence=0.90,
            document_type=None
        )

        # Direct approach (original)
        prompt_manager = PromptTemplateManager()
        direct_result = prompt_manager.get_prompt(
            domain=classification.domain,
            action=classification.action,
            query="IVA calculation",
            context=None,
            document_type=None
        )

        # Orchestrator approach (new)
        ctx = {
            'classification': classification,
            'prompt_template_manager': prompt_manager,
            'user_query': 'IVA calculation',
            'request_id': 'test-43-parity'
        }

        orchestrator_result = await step_43__domain_prompt(messages=[], ctx=ctx)

        # Verify identical prompt generation
        assert orchestrator_result['domain_prompt'] == direct_result
        assert orchestrator_result['prompt_generated'] is True
        assert orchestrator_result['domain'] == 'tax'
        assert orchestrator_result['action'] == 'information_request'

        # Both approaches should produce the same prompt content
        assert len(orchestrator_result['domain_prompt']) == len(direct_result)