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
    async def test_step_43_labor_ccnl_query(
        self,
        mock_log,
        prompt_template_manager
    ):
        """Test STEP 43: Generate labor domain CCNL query prompt."""
        
        result = prompt_template_manager.get_prompt(
            domain=Domain.LABOR,
            action=Action.CCNL_QUERY,
            query="What is the average salary for a metalworker in Milan?",
            context=None,
            document_type=None
        )
        
        # Should generate labor-specific prompt
        assert isinstance(result, str)
        assert "Consulente del Lavoro" in result  # Labor consultant role
        assert "CCNL" in result  # Labor contract reference
        assert "Metalmeccanico" in result  # Metalworking sector
        
        # Verify STEP 43 logging
        step_43_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 43
        ]
        
        assert len(step_43_logs) > 0
        log_call = step_43_logs[0]
        assert log_call[1]['domain'] == Domain.LABOR.value
        assert log_call[1]['action'] == Action.CCNL_QUERY.value

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
            query="Should I incorporate as SRL or remain a sole proprietorship?",
            context=None,
            document_type=None
        )
        
        # Should generate business-specific prompt
        assert isinstance(result, str)
        assert "business" in result.lower() or "società" in result  # Business context
        assert "SRL" in result or "srl" in result  # Corporate form reference
        
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
    async def test_step_43_accounting_calculation_request(
        self,
        mock_log,
        prompt_template_manager
    ):
        """Test STEP 43: Generate accounting domain calculation prompt."""
        
        result = prompt_template_manager.get_prompt(
            domain=Domain.ACCOUNTING,
            action=Action.CALCULATION_REQUEST,
            query="Calculate depreciation for office equipment purchased in 2024",
            context={"calculation_parameters": {"asset_value": 5000, "asset_type": "office_equipment"}},
            document_type=None
        )
        
        # Should generate accounting-specific prompt
        assert isinstance(result, str)
        assert "contabil" in result.lower()  # Accounting reference
        assert "calcolo" in result.lower() or "CALCOLO" in result  # Calculation instruction
        assert "asset_value: 5000" in result  # Context parameters
        
        # Verify STEP 43 logging with context
        step_43_logs = [
            call for call in mock_log.call_args_list
            if len(call[1]) > 3 and call[1].get('step') == 43
        ]
        
        assert len(step_43_logs) > 0
        log_call = step_43_logs[0]
        assert log_call[1]['domain'] == Domain.ACCOUNTING.value
        assert log_call[1]['action'] == Action.CALCULATION_REQUEST.value
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
        
        # Verify all required fields for STEP 43
        required_fields = [
            'step', 'step_id', 'node_label', 'domain', 'action', 
            'user_query', 'prompt_length', 'template_source', 'has_context'
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
        """Test STEP 43: Performance tracking with timer."""
        
        # Mock rag_step_timer as well
        with patch('app.services.domain_prompt_templates.rag_step_timer') as mock_timer:
            # Mock the context manager
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()
            
            result = prompt_template_manager.get_prompt(
                domain=Domain.LEGAL,
                action=Action.DOCUMENT_GENERATION,
                query="Draft a contract for software development services",
                context=None,
                document_type="contratto_sviluppo_software"
            )
            
            # Should generate prompt successfully
            assert isinstance(result, str)
            
            # Verify timer was used for performance tracking
            mock_timer.assert_called_with(
                43,
                "RAG.classify.prompttemplatemanager.get.prompt.get.domain.specific.prompt",
                "DomainPrompt",
                domain=Domain.LEGAL.value,
                action=Action.DOCUMENT_GENERATION.value
            )

    @pytest.mark.asyncio
    @patch('app.services.domain_prompt_templates.rag_step_log')
    async def test_step_43_all_domains_work_correctly(
        self,
        mock_log,
        prompt_template_manager
    ):
        """Test STEP 43: All domains generate appropriate prompts."""
        
        test_cases = [
            (Domain.TAX, Action.INFORMATION_REQUEST, "tax query"),
            (Domain.LEGAL, Action.DOCUMENT_GENERATION, "legal document request"),
            (Domain.LABOR, Action.CCNL_QUERY, "labor contract question"),
            (Domain.BUSINESS, Action.STRATEGIC_ADVICE, "business strategy question"),
            (Domain.ACCOUNTING, Action.COMPLIANCE_CHECK, "accounting compliance check")
        ]
        
        for domain, action, query in test_cases:
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