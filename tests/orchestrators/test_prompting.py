#!/usr/bin/env python3
"""
Tests for RAG STEP 41 — Select appropriate prompt

Tests document analysis prompt injection for domain-specific prompts
when query_composition is 'pure_doc' or 'hybrid'.

DEV-007 Issue 1: Document Analysis Quality Regression
"""

from unittest.mock import MagicMock, patch

import pytest


class TestStep41DocumentAnalysisInjection:
    """Test suite for document analysis prompt injection in step 41"""

    @pytest.fixture
    def mock_messages(self):
        """Mock user messages for processing."""
        msg = MagicMock()
        msg.role = "user"
        msg.content = "Cosa sono questi dati?"
        return [msg]

    @pytest.fixture
    def mock_classification_high_confidence(self):
        """Mock classification with high confidence (above threshold)."""
        return {
            "domain": "italian_tax",
            "action": "explain",
            "confidence": 0.85,  # Above 0.6 threshold
        }

    @pytest.fixture
    def mock_prompt_template_manager(self):
        """Mock prompt template manager."""
        manager = MagicMock()
        return manager

    @pytest.mark.asyncio
    @patch("app.orchestrators.prompting.rag_step_log")
    @patch("app.orchestrators.prompting.rag_step_timer")
    @patch("app.orchestrators.classify.step_43__domain_prompt")
    async def test_step_41_injects_document_analysis_for_pure_doc(
        self,
        mock_step_43,
        mock_timer,
        mock_rag_log,
        mock_messages,
        mock_classification_high_confidence,
        mock_prompt_template_manager,
    ):
        """Test Step 41: Injects DOCUMENT_ANALYSIS_OVERRIDE at TOP when query_composition is 'pure_doc'"""
        from app.core.prompts import DOCUMENT_ANALYSIS_OVERRIDE
        from app.orchestrators.prompting import step_41__select_prompt

        # Mock timer context manager
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        # Mock step 43 to return a domain prompt
        mock_step_43.return_value = {
            "prompt_generated": True,
            "domain_prompt": "You are an Italian tax expert.",
        }

        # Context with query_composition = 'pure_doc'
        ctx = {
            "classification": mock_classification_high_confidence,
            "prompt_template_manager": mock_prompt_template_manager,
            "request_id": "test_req_001",
            "query_composition": "pure_doc",  # This should trigger injection
        }

        result = await step_41__select_prompt(messages=mock_messages, ctx=ctx)

        # Verify DOCUMENT_ANALYSIS_OVERRIDE is injected at TOP
        assert result["prompt_selected"] is True
        selected_prompt = result.get("selected_prompt", "")
        assert DOCUMENT_ANALYSIS_OVERRIDE in selected_prompt, (
            f"DOCUMENT_ANALYSIS_OVERRIDE should be in selected_prompt for pure_doc. "
            f"Got prompt type: {result.get('prompt_type')}"
        )
        # Verify override is at TOP (starts with it)
        assert selected_prompt.startswith("[System context"), (
            "DOCUMENT_ANALYSIS_OVERRIDE should be at the TOP of the prompt"
        )

    @pytest.mark.asyncio
    @patch("app.orchestrators.prompting.rag_step_log")
    @patch("app.orchestrators.prompting.rag_step_timer")
    @patch("app.orchestrators.classify.step_43__domain_prompt")
    async def test_step_41_injects_document_analysis_for_hybrid(
        self,
        mock_step_43,
        mock_timer,
        mock_rag_log,
        mock_messages,
        mock_classification_high_confidence,
        mock_prompt_template_manager,
    ):
        """Test Step 41: Injects DOCUMENT_ANALYSIS_OVERRIDE at TOP when query_composition is 'hybrid'"""
        from app.core.prompts import DOCUMENT_ANALYSIS_OVERRIDE
        from app.orchestrators.prompting import step_41__select_prompt

        # Mock timer context manager
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        # Mock step 43 to return a domain prompt
        mock_step_43.return_value = {
            "prompt_generated": True,
            "domain_prompt": "You are an Italian tax expert.",
        }

        # Context with query_composition = 'hybrid'
        ctx = {
            "classification": mock_classification_high_confidence,
            "prompt_template_manager": mock_prompt_template_manager,
            "request_id": "test_req_002",
            "query_composition": "hybrid",  # This should also trigger injection
        }

        result = await step_41__select_prompt(messages=mock_messages, ctx=ctx)

        # Verify DOCUMENT_ANALYSIS_OVERRIDE is injected at TOP
        assert result["prompt_selected"] is True
        selected_prompt = result.get("selected_prompt", "")
        assert DOCUMENT_ANALYSIS_OVERRIDE in selected_prompt, (
            f"DOCUMENT_ANALYSIS_OVERRIDE should be in selected_prompt for hybrid. "
            f"Got prompt type: {result.get('prompt_type')}"
        )
        # Verify override is at TOP (starts with it)
        assert selected_prompt.startswith("[System context"), (
            "DOCUMENT_ANALYSIS_OVERRIDE should be at the TOP of the prompt"
        )

    @pytest.mark.asyncio
    @patch("app.orchestrators.prompting.rag_step_log")
    @patch("app.orchestrators.prompting.rag_step_timer")
    @patch("app.orchestrators.classify.step_43__domain_prompt")
    async def test_step_41_no_injection_for_pure_kb(
        self,
        mock_step_43,
        mock_timer,
        mock_rag_log,
        mock_messages,
        mock_classification_high_confidence,
        mock_prompt_template_manager,
    ):
        """Test Step 41: Does NOT inject DOCUMENT_ANALYSIS_OVERRIDE when query_composition is 'pure_kb'"""
        from app.core.prompts import DOCUMENT_ANALYSIS_OVERRIDE
        from app.orchestrators.prompting import step_41__select_prompt

        # Mock timer context manager
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        # Mock step 43 to return a domain prompt
        base_domain_prompt = "You are an Italian tax expert."
        mock_step_43.return_value = {
            "prompt_generated": True,
            "domain_prompt": base_domain_prompt,
        }

        # Context with query_composition = 'pure_kb' (default)
        ctx = {
            "classification": mock_classification_high_confidence,
            "prompt_template_manager": mock_prompt_template_manager,
            "request_id": "test_req_003",
            "query_composition": "pure_kb",  # Should NOT trigger injection
        }

        result = await step_41__select_prompt(messages=mock_messages, ctx=ctx)

        # Verify DOCUMENT_ANALYSIS_OVERRIDE is NOT injected
        assert result["prompt_selected"] is True
        selected_prompt = result.get("selected_prompt", "")
        assert DOCUMENT_ANALYSIS_OVERRIDE not in selected_prompt, (
            "DOCUMENT_ANALYSIS_OVERRIDE should NOT be in selected_prompt for pure_kb"
        )

    @pytest.mark.asyncio
    @patch("app.orchestrators.prompting.rag_step_log")
    @patch("app.orchestrators.prompting.rag_step_timer")
    @patch("app.orchestrators.classify.step_43__domain_prompt")
    async def test_step_41_no_injection_when_no_query_composition(
        self,
        mock_step_43,
        mock_timer,
        mock_rag_log,
        mock_messages,
        mock_classification_high_confidence,
        mock_prompt_template_manager,
    ):
        """Test Step 41: Does NOT inject when query_composition is missing (defaults to pure_kb)"""
        from app.core.prompts import DOCUMENT_ANALYSIS_OVERRIDE
        from app.orchestrators.prompting import step_41__select_prompt

        # Mock timer context manager
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        # Mock step 43 to return a domain prompt
        mock_step_43.return_value = {
            "prompt_generated": True,
            "domain_prompt": "You are an Italian tax expert.",
        }

        # Context WITHOUT query_composition (should default to pure_kb)
        ctx = {
            "classification": mock_classification_high_confidence,
            "prompt_template_manager": mock_prompt_template_manager,
            "request_id": "test_req_004",
            # No query_composition key
        }

        result = await step_41__select_prompt(messages=mock_messages, ctx=ctx)

        # Verify DOCUMENT_ANALYSIS_OVERRIDE is NOT injected
        assert result["prompt_selected"] is True
        selected_prompt = result.get("selected_prompt", "")
        assert DOCUMENT_ANALYSIS_OVERRIDE not in selected_prompt, (
            "DOCUMENT_ANALYSIS_OVERRIDE should NOT be in selected_prompt when query_composition is missing"
        )

    @pytest.mark.asyncio
    @patch("app.orchestrators.prompting.rag_step_log")
    @patch("app.orchestrators.prompting.rag_step_timer")
    @patch("app.orchestrators.classify.step_43__domain_prompt")
    @patch("app.core.logging.logger")
    async def test_step_41_logs_document_analysis_injection(
        self,
        mock_logger,
        mock_step_43,
        mock_timer,
        mock_rag_log,
        mock_messages,
        mock_classification_high_confidence,
        mock_prompt_template_manager,
    ):
        """Test Step 41: Logs when document analysis override is injected"""
        from app.orchestrators.prompting import step_41__select_prompt

        # Mock timer context manager
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        # Mock step 43 to return a domain prompt
        mock_step_43.return_value = {
            "prompt_generated": True,
            "domain_prompt": "You are an Italian tax expert.",
        }

        # Context with query_composition = 'pure_doc'
        ctx = {
            "classification": mock_classification_high_confidence,
            "prompt_template_manager": mock_prompt_template_manager,
            "request_id": "test_req_005",
            "query_composition": "pure_doc",
        }

        await step_41__select_prompt(messages=mock_messages, ctx=ctx)

        # Verify logging of injection
        info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any("document_analysis_override_injected_to_domain_prompt" in str(call) for call in info_calls), (
            "Should log document_analysis_override_injected_to_domain_prompt"
        )


class TestStep44DocumentAnalysisInjection:
    """Test suite for document analysis prompt injection in step 44 (default prompt path)"""

    @patch("app.orchestrators.prompting.rag_step_log")
    @patch("app.orchestrators.prompting.rag_step_timer")
    def test_step_44_injects_document_analysis_for_pure_doc(
        self,
        mock_timer,
        mock_rag_log,
    ):
        """Test Step 44: Injects DOCUMENT_ANALYSIS_OVERRIDE at TOP when query_composition is 'pure_doc'"""
        from app.core.prompts import DOCUMENT_ANALYSIS_OVERRIDE
        from app.orchestrators.prompting import step_44__default_sys_prompt

        # Mock timer context manager
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        # Context with query_composition = 'pure_doc'
        ctx = {
            "user_query": "Cosa sono questi dati?",
            "trigger_reason": "no_classification",
            "query_composition": "pure_doc",
        }

        result = step_44__default_sys_prompt(ctx=ctx)

        # Verify DOCUMENT_ANALYSIS_OVERRIDE is injected at TOP
        assert DOCUMENT_ANALYSIS_OVERRIDE in result, "DOCUMENT_ANALYSIS_OVERRIDE should be in result for pure_doc"
        # Verify override is at TOP (starts with it)
        assert result.startswith("[System context"), "DOCUMENT_ANALYSIS_OVERRIDE should be at the TOP of the prompt"

    @patch("app.orchestrators.prompting.rag_step_log")
    @patch("app.orchestrators.prompting.rag_step_timer")
    def test_step_44_injects_document_analysis_for_hybrid(
        self,
        mock_timer,
        mock_rag_log,
    ):
        """Test Step 44: Injects DOCUMENT_ANALYSIS_OVERRIDE at TOP when query_composition is 'hybrid'"""
        from app.core.prompts import DOCUMENT_ANALYSIS_OVERRIDE
        from app.orchestrators.prompting import step_44__default_sys_prompt

        # Mock timer context manager
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        # Context with query_composition = 'hybrid'
        ctx = {
            "user_query": "Spiega questi dati fiscali",
            "trigger_reason": "low_confidence",
            "query_composition": "hybrid",
        }

        result = step_44__default_sys_prompt(ctx=ctx)

        # Verify DOCUMENT_ANALYSIS_OVERRIDE is injected at TOP
        assert DOCUMENT_ANALYSIS_OVERRIDE in result, "DOCUMENT_ANALYSIS_OVERRIDE should be in result for hybrid"
        # Verify override is at TOP (starts with it)
        assert result.startswith("[System context"), "DOCUMENT_ANALYSIS_OVERRIDE should be at the TOP of the prompt"

    @patch("app.orchestrators.prompting.rag_step_log")
    @patch("app.orchestrators.prompting.rag_step_timer")
    def test_step_44_no_injection_for_pure_kb(
        self,
        mock_timer,
        mock_rag_log,
    ):
        """Test Step 44: Does NOT inject DOCUMENT_ANALYSIS_OVERRIDE when query_composition is 'pure_kb'"""
        from app.core.prompts import DOCUMENT_ANALYSIS_OVERRIDE
        from app.orchestrators.prompting import step_44__default_sys_prompt

        # Mock timer context manager
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        # Context with query_composition = 'pure_kb'
        ctx = {
            "user_query": "What is IVA?",
            "trigger_reason": "no_classification",
            "query_composition": "pure_kb",
        }

        result = step_44__default_sys_prompt(ctx=ctx)

        # Verify DOCUMENT_ANALYSIS_OVERRIDE is NOT injected
        assert DOCUMENT_ANALYSIS_OVERRIDE not in result, (
            "DOCUMENT_ANALYSIS_OVERRIDE should NOT be in result for pure_kb"
        )


class TestDEV245ConciseMode:
    """DEV-245: Tests for concise mode when is_followup is True"""

    @patch("app.orchestrators.prompting.rag_step_log")
    @patch("app.orchestrators.prompting.rag_step_timer")
    def test_step_44_injects_concise_mode_for_followup(
        self,
        mock_timer,
        mock_rag_log,
    ):
        """DEV-245: Test Step 44 injects concise mode prefix when is_followup=True"""
        from app.orchestrators.prompting import step_44__default_sys_prompt

        # Mock timer context manager
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        # Context with is_followup=True and KB context
        ctx = {
            "user_query": "e l'IRAP?",
            "trigger_reason": "no_classification",
            "query_composition": "pure_kb",
            "routing_decision": {
                "route": "theoretical_definition",
                "is_followup": True,
                "confidence": 0.85,
            },
            "context": "IRAP è l'Imposta Regionale sulle Attività Produttive...",
        }

        result = step_44__default_sys_prompt(ctx=ctx)

        # Verify follow-up mode grounding rules are injected
        # DEV-251 Part 3: Changed from CONCISE_MODE_PREFIX to FOLLOWUP_GROUNDING_RULES
        assert "MODALITÀ FOLLOW-UP" in result, "Follow-up mode rules should be in prompt for follow-up"
        assert "NON RIPETERE" in result, "Follow-up mode should instruct not to repeat"

    @patch("app.orchestrators.prompting.rag_step_log")
    @patch("app.orchestrators.prompting.rag_step_timer")
    def test_step_44_no_concise_mode_when_not_followup(
        self,
        mock_timer,
        mock_rag_log,
    ):
        """DEV-245: Test Step 44 does NOT inject concise mode when is_followup=False"""
        from app.orchestrators.prompting import step_44__default_sys_prompt

        # Mock timer context manager
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        # Context with is_followup=False and KB context
        ctx = {
            "user_query": "Cos'è l'IRAP?",
            "trigger_reason": "no_classification",
            "query_composition": "pure_kb",
            "routing_decision": {
                "route": "theoretical_definition",
                "is_followup": False,
                "confidence": 0.85,
            },
            "context": "IRAP è l'Imposta Regionale sulle Attività Produttive...",
        }

        result = step_44__default_sys_prompt(ctx=ctx)

        # Verify concise mode prefix is NOT injected
        assert "MODALITÀ CONCISA" not in result, "Concise mode should NOT be in prompt when not follow-up"

    @patch("app.orchestrators.prompting.rag_step_log")
    @patch("app.orchestrators.prompting.rag_step_timer")
    def test_step_44_no_concise_mode_without_routing_decision(
        self,
        mock_timer,
        mock_rag_log,
    ):
        """DEV-245: Test Step 44 does NOT inject concise mode when routing_decision is missing"""
        from app.orchestrators.prompting import step_44__default_sys_prompt

        # Mock timer context manager
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        # Context without routing_decision
        ctx = {
            "user_query": "Cos'è l'IRAP?",
            "trigger_reason": "no_classification",
            "query_composition": "pure_kb",
            "context": "IRAP è l'Imposta Regionale sulle Attività Produttive...",
        }

        result = step_44__default_sys_prompt(ctx=ctx)

        # Verify concise mode prefix is NOT injected
        assert "MODALITÀ CONCISA" not in result, "Concise mode should NOT be in prompt without routing_decision"

    @patch("app.orchestrators.prompting.rag_step_log")
    @patch("app.orchestrators.prompting.rag_step_timer")
    def test_step_44_no_concise_mode_without_context(
        self,
        mock_timer,
        mock_rag_log,
    ):
        """DEV-245: Test Step 44 does NOT inject concise mode when no KB context (concise mode only with context)"""
        from app.orchestrators.prompting import step_44__default_sys_prompt

        # Mock timer context manager
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        # Context with is_followup=True but NO KB context
        ctx = {
            "user_query": "e l'IRAP?",
            "trigger_reason": "no_classification",
            "query_composition": "pure_kb",
            "routing_decision": {
                "route": "theoretical_definition",
                "is_followup": True,
                "confidence": 0.85,
            },
            # No "context" key - no KB content
        }

        result = step_44__default_sys_prompt(ctx=ctx)

        # Concise mode should NOT be injected because there's no KB context
        # The concise mode prefix is only added when has_actual_context is True
        assert "MODALITÀ CONCISA" not in result, "Concise mode should NOT be in prompt without KB context"

    @pytest.mark.asyncio
    @patch("app.orchestrators.prompting.rag_step_log")
    @patch("app.orchestrators.prompting.rag_step_timer")
    @patch("app.orchestrators.classify.step_43__domain_prompt")
    async def test_step_41_domain_prompt_concise_mode_for_followup(
        self,
        mock_step_43,
        mock_timer,
        mock_rag_log,
    ):
        """DEV-245: Test Step 41 domain prompt path injects concise mode for follow-up"""
        from app.orchestrators.prompting import step_41__select_prompt

        # Mock timer context manager
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        # Mock step 43 to return a domain prompt
        mock_step_43.return_value = {
            "prompt_generated": True,
            "domain_prompt": "You are an Italian tax expert.",
        }

        # Mock user message
        msg = MagicMock()
        msg.role = "user"
        msg.content = "e l'IRAP?"
        messages = [msg]

        # Context with is_followup=True
        ctx = {
            "classification": {
                "domain": "italian_tax",
                "action": "explain",
                "confidence": 0.85,
            },
            "request_id": "test_concise_001",
            "routing_decision": {
                "route": "theoretical_definition",
                "is_followup": True,
                "confidence": 0.85,
            },
            "context": "IRAP è l'Imposta Regionale sulle Attività Produttive...",
        }

        result = await step_41__select_prompt(messages=messages, ctx=ctx)

        # Verify concise mode prefix is in the selected prompt
        selected_prompt = result.get("selected_prompt", "")
        assert "MODALITÀ CONCISA" in selected_prompt, "Concise mode should be in domain prompt for follow-up"
