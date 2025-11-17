"""
Tests for RAG Step 99 — Return to tool caller (RAG.platform.return.to.tool.caller)

Test coverage:
- Unit tests: Tool result formatting, convergence handling, error scenarios
- Integration tests: Step 80/83/97/98→99, Step 99→101
- Parity tests: Behavioral definition validation
"""

import asyncio
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.orchestrators.platform import step_99__tool_results


class TestStep99ToolResults:
    """Unit tests for Step 99 tool results convergence and formatting"""

    @pytest.fixture
    def context_from_knowledge_tool(self) -> dict[str, Any]:
        """Context from Step 80 (KBQueryTool) with knowledge search results"""
        return {
            "rag_step": 80,
            "step_id": "RAG.knowledge.knowledgesearchtool.search.kb.on.demand",
            "tool_name": "KnowledgeSearchTool",
            "tool_call_id": "call_kb_123",
            "tool_result": {
                "results": [
                    {
                        "content": "Italian VAT standard rate is 22%. Reduced rates apply to specific goods and services.",
                        "source": "KB_VAT_001",
                        "confidence": 0.95,
                        "metadata": {"category": "tax_rates", "country": "Italy"},
                    },
                    {
                        "content": "VAT registration threshold in Italy is €65,000 for businesses.",
                        "source": "KB_VAT_002",
                        "confidence": 0.88,
                        "metadata": {"category": "tax_thresholds", "country": "Italy"},
                    },
                ],
                "total_results": 2,
                "search_time_ms": 45,
            },
            "search_metadata": {
                "query": "Italian VAT rates and thresholds",
                "search_type": "knowledge_base",
                "kb_version": "2024.1",
            },
            "request_id": "kb_req_123",
            "session_id": "session_456",
        }

    @pytest.fixture
    def context_from_faq_tool(self) -> dict[str, Any]:
        """Context from Step 83 (FAQQuery) with FAQ results"""
        return {
            "rag_step": 83,
            "step_id": "RAG.golden.faqtool.faq.query.query.golden.set",
            "tool_name": "FAQTool",
            "tool_call_id": "call_faq_456",
            "tool_result": {
                "faqs": [
                    {
                        "question": "What is the corporate tax rate in Italy?",
                        "answer": "The standard corporate income tax rate (IRES) in Italy is 24%. Additionally, there is a regional tax (IRAP) of approximately 3.9%.",
                        "faq_id": "FAQ_CORP_TAX_001",
                        "confidence": 0.98,
                        "last_updated": "2024-01-15",
                        "category": "corporate_taxation",
                    }
                ],
                "total_matches": 1,
                "query_time_ms": 28,
            },
            "faq_metadata": {
                "query": "corporate tax rate Italy",
                "min_confidence": "high",
                "golden_set_version": "2024.Q1",
            },
            "request_id": "faq_req_456",
        }

    @pytest.fixture
    def context_from_ccnl_calc(self) -> dict[str, Any]:
        """Context from Step 97 (CCNLCalc) with calculation results"""
        return {
            "rag_step": 97,
            "step_id": "RAG.knowledge.ccnlcalculator.calculate.perform.calculations",
            "tool_name": "ccnl_query",
            "tool_call_id": "call_ccnl_789",
            "tool_result": {
                "calculation_result": {
                    "base_salary": 1500.00,
                    "overtime_hours": 10,
                    "overtime_rate": 1.25,
                    "overtime_pay": 93.75,
                    "total_gross": 1593.75,
                    "currency": "EUR",
                },
                "ccnl_context": {
                    "ccnl_type": "metalworkers",
                    "contract_year": 2024,
                    "applicable_rates": {"standard_hourly": 12.50, "overtime_multiplier": 1.25},
                },
                "calculation_time_ms": 15,
            },
            "ccnl_metadata": {
                "query": "overtime calculation metalworkers 10 hours",
                "ccnl_type": "metalworkers",
                "base_salary": 1500.00,
            },
            "request_id": "ccnl_req_789",
        }

    @pytest.fixture
    def context_from_document_processing(self) -> dict[str, Any]:
        """Context from Step 98 (ToToolResults) with document processing results"""
        return {
            "rag_step": 98,
            "step_id": "RAG.facts.convert.to.toolmessage.facts.and.spans",
            "tool_name": "DocumentIngestTool",
            "tool_call_id": "call_doc_012",
            "tool_result": {
                "processed_documents": [
                    {
                        "filename": "invoice_2024_001.pdf",
                        "document_type": "invoice",
                        "extracted_facts": [
                            {"type": "invoice_number", "value": "INV-2024-001", "confidence": 0.99},
                            {"type": "total_amount", "value": "1,220.00 EUR", "confidence": 0.97},
                            {"type": "vat_amount", "value": "220.00 EUR", "confidence": 0.95},
                            {"type": "issue_date", "value": "2024-01-15", "confidence": 0.98},
                        ],
                        "processing_status": "completed",
                        "text_spans": 156,
                    }
                ],
                "total_processed": 1,
                "processing_time_ms": 890,
            },
            "document_metadata": {
                "upload_batch_id": "batch_2024_001",
                "security_validated": True,
                "storage_location": "blob_store_encrypted",
            },
            "request_id": "doc_req_012",
        }

    @pytest.fixture
    def context_error_scenario(self) -> dict[str, Any]:
        """Context representing an error scenario from tool execution"""
        return {
            "rag_step": 80,
            "tool_name": "KnowledgeSearchTool",
            "tool_call_id": "call_error_999",
            "tool_result": None,
            "error": "Knowledge base temporarily unavailable",
            "error_type": "service_unavailable",
            "request_id": "error_req_999",
        }

    @pytest.mark.asyncio
    async def test_knowledge_tool_result_formatting(self, context_from_knowledge_tool):
        """Test formatting of knowledge search tool results"""

        result = await step_99__tool_results(ctx=context_from_knowledge_tool)

        # Verify tool result formatting
        assert "formatted_tool_result" in result
        formatted_result = result["formatted_tool_result"]

        # Should format as string content for ToolMessage
        assert isinstance(formatted_result, str)
        assert "Italian VAT standard rate is 22%" in formatted_result
        assert "VAT registration threshold" in formatted_result

        # Verify tool message metadata
        assert result["tool_message_metadata"]["tool_name"] == "KnowledgeSearchTool"
        assert result["tool_message_metadata"]["tool_call_id"] == "call_kb_123"
        assert result["tool_message_metadata"]["result_type"] == "knowledge_search"

        # Verify routing
        assert result["next_step"] == 101
        assert result["next_step_id"] == "RAG.response.return.to.chat.node.for.final.response"
        assert result["route_to"] == "FinalResponse"

    @pytest.mark.asyncio
    async def test_faq_tool_result_formatting(self, context_from_faq_tool):
        """Test formatting of FAQ tool results"""

        result = await step_99__tool_results(ctx=context_from_faq_tool)

        # Verify FAQ result formatting
        formatted_result = result["formatted_tool_result"]
        assert "corporate income tax rate (IRES) in Italy is 24%" in formatted_result
        assert "regional tax (IRAP)" in formatted_result

        # Verify FAQ-specific metadata
        assert result["tool_message_metadata"]["result_type"] == "faq_query"
        assert result["tool_message_metadata"]["confidence"] == 0.98

        # Context preservation
        assert result["faq_metadata"]["golden_set_version"] == "2024.Q1"

    @pytest.mark.asyncio
    async def test_ccnl_calculation_result_formatting(self, context_from_ccnl_calc):
        """Test formatting of CCNL calculation results"""

        result = await step_99__tool_results(ctx=context_from_ccnl_calc)

        # Verify calculation result formatting
        formatted_result = result["formatted_tool_result"]
        assert "1593.75" in formatted_result  # Total gross
        assert "93.75" in formatted_result  # Overtime pay
        assert "metalworkers" in formatted_result
        assert "EUR" in formatted_result

        # Verify calculation-specific metadata
        assert result["tool_message_metadata"]["result_type"] == "ccnl_calculation"
        assert result["ccnl_metadata"]["ccnl_type"] == "metalworkers"

    @pytest.mark.asyncio
    async def test_document_processing_result_formatting(self, context_from_document_processing):
        """Test formatting of document processing results"""

        result = await step_99__tool_results(ctx=context_from_document_processing)

        # Verify document result formatting
        formatted_result = result["formatted_tool_result"]
        assert "invoice_2024_001.pdf" in formatted_result
        assert "INV-2024-001" in formatted_result
        assert "1,220.00 EUR" in formatted_result
        assert "220.00 EUR" in formatted_result

        # Verify document-specific metadata
        assert result["tool_message_metadata"]["result_type"] == "document_processing"
        assert result["document_metadata"]["security_validated"] is True

    @pytest.mark.asyncio
    async def test_error_result_handling(self, context_error_scenario):
        """Test handling of error scenarios from tool execution"""

        result = await step_99__tool_results(ctx=context_error_scenario)

        # Verify error formatting
        formatted_result = result["formatted_tool_result"]
        assert "error" in formatted_result.lower()
        assert "Knowledge base temporarily unavailable" in formatted_result

        # Verify error metadata
        assert result["tool_message_metadata"]["has_error"] is True
        assert result["tool_message_metadata"]["error_type"] == "service_unavailable"
        assert result["error"] == "Knowledge base temporarily unavailable"

        # Should still route properly
        assert result["next_step"] == 101

    @pytest.mark.asyncio
    async def test_tool_message_creation(self, context_from_knowledge_tool):
        """Test proper ToolMessage structure creation"""

        result = await step_99__tool_results(ctx=context_from_knowledge_tool)

        # Verify ToolMessage structure
        assert "tool_message_data" in result
        tool_msg_data = result["tool_message_data"]

        assert tool_msg_data["content"] == result["formatted_tool_result"]
        assert tool_msg_data["name"] == "KnowledgeSearchTool"
        assert tool_msg_data["tool_call_id"] == "call_kb_123"

    @pytest.mark.asyncio
    async def test_context_preservation(self, context_from_knowledge_tool):
        """Test that all input context is preserved"""

        result = await step_99__tool_results(ctx=context_from_knowledge_tool)

        # All original context should be preserved
        assert result["request_id"] == context_from_knowledge_tool["request_id"]
        assert result["session_id"] == context_from_knowledge_tool["session_id"]
        assert result["search_metadata"] == context_from_knowledge_tool["search_metadata"]

        # New tool results metadata should be added
        assert "tool_results_processed" in result
        assert "tool_message_metadata" in result
        assert "formatted_tool_result" in result

    @pytest.mark.asyncio
    async def test_missing_tool_result_handling(self):
        """Test handling when tool result is missing or malformed"""

        ctx = {
            "rag_step": 80,
            "tool_name": "KnowledgeSearchTool",
            "tool_call_id": "call_missing",
            "request_id": "missing_result_test",
        }

        result = await step_99__tool_results(ctx=ctx)

        # Should handle gracefully
        assert "formatted_tool_result" in result
        assert result["tool_results_processed"] is False
        assert "error" in result
        assert result["next_step"] == 101  # Still route to FinalResponse


class TestStep99IntegrationFlows:
    """Integration tests for Step 99 with neighboring steps"""

    @pytest.mark.asyncio
    async def test_step_80_to_99_knowledge_flow(self):
        """Test flow from Step 80 (KBQueryTool) to Step 99"""

        # Simulate Step 80 output
        step_80_output = {
            "rag_step": 80,
            "step_id": "RAG.knowledge.knowledgesearchtool.search.kb.on.demand",
            "kb_search_completed": True,
            "tool_name": "KnowledgeSearchTool",
            "tool_call_id": "call_kb_integration",
            "tool_result": {
                "results": [
                    {"content": "Integration test knowledge result", "source": "KB_INT_001", "confidence": 0.9}
                ],
                "total_results": 1,
            },
            "knowledge_search_metadata": {"search_duration_ms": 55, "results_found": True},
            "request_id": "integration_kb_99",
        }

        result = await step_99__tool_results(ctx=step_80_output)

        # Verify Step 80 context preserved
        assert result["kb_search_completed"] is True
        assert result["knowledge_search_metadata"]["results_found"] is True

        # Verify Step 99 processing
        assert "Integration test knowledge result" in result["formatted_tool_result"]
        assert result["previous_step"] == 80
        assert result["next_step"] == 101

    @pytest.mark.asyncio
    async def test_step_83_to_99_faq_flow(self):
        """Test flow from Step 83 (FAQQuery) to Step 99"""

        step_83_output = {
            "rag_step": 83,
            "step_id": "RAG.golden.faqtool.faq.query.query.golden.set",
            "faq_query_completed": True,
            "tool_name": "FAQTool",
            "tool_call_id": "call_faq_integration",
            "tool_result": {
                "faqs": [
                    {
                        "question": "Integration test FAQ question?",
                        "answer": "Integration test FAQ answer",
                        "faq_id": "FAQ_INT_001",
                        "confidence": 0.95,
                    }
                ]
            },
            "request_id": "integration_faq_99",
        }

        result = await step_99__tool_results(ctx=step_83_output)

        # Verify FAQ context preserved
        assert result["faq_query_completed"] is True

        # Verify FAQ result formatting
        assert "Integration test FAQ answer" in result["formatted_tool_result"]
        assert result["tool_message_metadata"]["result_type"] == "faq_query"

    @pytest.mark.asyncio
    async def test_step_97_to_99_ccnl_calc_flow(self):
        """Test flow from Step 97 (CCNLCalc) to Step 99"""

        step_97_output = {
            "rag_step": 97,
            "step_id": "RAG.knowledge.ccnlcalculator.calculate.perform.calculations",
            "calculation_completed": True,
            "tool_name": "ccnl_query",
            "tool_call_id": "call_ccnl_integration",
            "tool_result": {
                "calculation_result": {
                    "total_gross": 2000.00,
                    "currency": "EUR",
                    "breakdown": "Integration test calculation",
                }
            },
            "request_id": "integration_ccnl_99",
        }

        result = await step_99__tool_results(ctx=step_97_output)

        # Verify CCNL context preserved
        assert result["calculation_completed"] is True

        # Verify calculation result formatting
        assert "2000.00" in result["formatted_tool_result"]
        assert "Integration test calculation" in result["formatted_tool_result"]

    @pytest.mark.asyncio
    async def test_step_98_to_99_document_flow(self):
        """Test flow from Step 98 (ToToolResults) to Step 99"""

        step_98_output = {
            "rag_step": 98,
            "step_id": "RAG.facts.convert.to.toolmessage.facts.and.spans",
            "facts_converted": True,
            "tool_name": "DocumentIngestTool",
            "tool_call_id": "call_doc_integration",
            "tool_result": {
                "processed_documents": [
                    {
                        "filename": "integration_test.pdf",
                        "extracted_facts": [{"type": "test_fact", "value": "integration_value", "confidence": 0.9}],
                    }
                ]
            },
            "request_id": "integration_doc_99",
        }

        result = await step_99__tool_results(ctx=step_98_output)

        # Verify document context preserved
        assert result["facts_converted"] is True

        # Verify document result formatting
        assert "integration_test.pdf" in result["formatted_tool_result"]
        assert "integration_value" in result["formatted_tool_result"]

    @pytest.mark.asyncio
    async def test_step_99_to_101_final_response_preparation(self):
        """Test Step 99 prepares data for Step 101 (FinalResponse)"""

        ctx = {
            "rag_step": 80,
            "tool_name": "KnowledgeSearchTool",
            "tool_call_id": "call_final_prep",
            "tool_result": {"results": [{"content": "Test result"}]},
            "request_id": "final_response_prep_test",
            "session_id": "session_123",
        }

        result = await step_99__tool_results(ctx=ctx)

        # Verify routing to FinalResponse
        assert result["next_step"] == 101
        assert result["next_step_id"] == "RAG.response.return.to.chat.node.for.final.response"
        assert result["route_to"] == "FinalResponse"

        # Should prepare ToolMessage data for final response
        assert "tool_message_data" in result
        assert result["tool_message_data"]["content"] is not None

        # Should preserve context for final response processing
        assert result["session_id"] == "session_123"
        assert "tool_results_completion_metadata" in result


class TestStep99ParityAndBehavior:
    """Parity tests ensuring Step 99 meets behavioral definition of done"""

    @pytest.mark.asyncio
    async def test_behavioral_convergence_point(self):
        """
        BEHAVIORAL TEST: Step 99 must act as convergence point for all tool execution paths
        and format results consistently for return to LangGraph tool caller.
        """

        # Test convergence from all tool paths
        tool_contexts = [
            # Knowledge path
            {
                "rag_step": 80,
                "tool_name": "KnowledgeSearchTool",
                "tool_result": {"results": [{"content": "Knowledge result"}]},
            },
            # FAQ path
            {"rag_step": 83, "tool_name": "FAQTool", "tool_result": {"faqs": [{"answer": "FAQ answer"}]}},
            # CCNL path
            {"rag_step": 97, "tool_name": "ccnl_query", "tool_result": {"calculation_result": {"total": 1000}}},
            # Document path
            {
                "rag_step": 98,
                "tool_name": "DocumentIngestTool",
                "tool_result": {"processed_documents": [{"filename": "test.pdf"}]},
            },
        ]

        for ctx in tool_contexts:
            ctx.update({"tool_call_id": "test_call", "request_id": "convergence_test"})

            result = await step_99__tool_results(ctx=ctx)

            # Must format results consistently
            assert "formatted_tool_result" in result
            assert isinstance(result["formatted_tool_result"], str)

            # Must create proper ToolMessage data
            assert "tool_message_data" in result
            assert result["tool_message_data"]["name"] == ctx["tool_name"]

            # Must route to FinalResponse
            assert result["next_step"] == 101
            assert result["route_to"] == "FinalResponse"

    @pytest.mark.asyncio
    async def test_behavioral_mermaid_flow_compliance(self):
        """
        BEHAVIORAL TEST: Step 99 must comply with Mermaid flow:
        - Receives from Steps 80, 83, 97, 98 (tool execution paths)
        - Routes to Step 101 (FinalResponse)
        """

        # Test all valid input paths from Mermaid
        mermaid_input_steps = [80, 83, 97, 98]

        for step in mermaid_input_steps:
            ctx = {
                "rag_step": step,
                "tool_name": "TestTool",
                "tool_call_id": f"call_{step}",
                "tool_result": {"test": "data"},
                "request_id": f"mermaid_test_{step}",
            }

            result = await step_99__tool_results(ctx=ctx)

            # Must identify previous step correctly
            assert result["previous_step"] == step

            # Must route to Step 101 (FinalResponse)
            assert result["next_step"] == 101

    @pytest.mark.asyncio
    async def test_behavioral_context_preservation(self):
        """
        BEHAVIORAL TEST: Step 99 must preserve all context while adding tool result formatting.
        """

        original_ctx = {
            "rag_step": 80,
            "request_id": "context_preservation_test",
            "session_id": "session_test_456",
            "user_id": "user_test_789",
            "tool_name": "KnowledgeSearchTool",
            "tool_call_id": "call_context_test",
            "tool_result": {"results": [{"content": "Test result"}]},
            "search_metadata": {"query": "test query", "time_ms": 50},
            "custom_context": {"key": "value"},
        }

        result = await step_99__tool_results(ctx=original_ctx)

        # All original context must be preserved
        assert result["request_id"] == original_ctx["request_id"]
        assert result["session_id"] == original_ctx["session_id"]
        assert result["user_id"] == original_ctx["user_id"]
        assert result["search_metadata"] == original_ctx["search_metadata"]
        assert result["custom_context"] == original_ctx["custom_context"]

        # New tool results metadata must be added
        assert "formatted_tool_result" in result
        assert "tool_message_data" in result
        assert "tool_results_processed" in result
        assert "tool_results_completion_metadata" in result

    @pytest.mark.asyncio
    async def test_behavioral_structured_observability(self):
        """
        BEHAVIORAL TEST: Step 99 must implement structured observability
        with rag_step_log and rag_step_timer per MASTER_GUARDRAILS.
        """

        with (
            patch("app.orchestrators.platform.rag_step_log") as mock_log,
            patch("app.orchestrators.platform.rag_step_timer") as mock_timer,
        ):
            ctx = {
                "tool_name": "KnowledgeSearchTool",
                "tool_call_id": "observability_test",
                "tool_result": {"results": []},
                "request_id": "observability_test",
            }

            await step_99__tool_results(ctx=ctx)

            # Verify structured logging
            mock_log.assert_called()
            log_calls = mock_log.call_args_list

            # Check required log attributes
            start_log = log_calls[0][1]  # kwargs from first call
            assert start_log["step"] == 99
            assert start_log["step_id"] == "RAG.platform.return.to.tool.caller"
            assert start_log["node_label"] == "ToolResults"
            assert start_log["category"] == "platform"
            assert start_log["type"] == "process"

            # Verify timing
            mock_timer.assert_called_with(
                99, "RAG.platform.return.to.tool.caller", "ToolResults", request_id="observability_test", stage="start"
            )

    @pytest.mark.asyncio
    async def test_behavioral_tool_message_format_compliance(self):
        """
        BEHAVIORAL TEST: Step 99 must format tool results to comply with
        LangChain ToolMessage format requirements for proper tool caller integration.
        """

        ctx = {
            "tool_name": "KnowledgeSearchTool",
            "tool_call_id": "format_compliance_test",
            "tool_result": {
                "results": [
                    {"content": "Test result 1", "confidence": 0.9},
                    {"content": "Test result 2", "confidence": 0.8},
                ]
            },
            "request_id": "format_compliance_test",
        }

        result = await step_99__tool_results(ctx=ctx)

        # Must create proper ToolMessage data structure
        tool_msg_data = result["tool_message_data"]

        # Required ToolMessage fields
        assert "content" in tool_msg_data
        assert "name" in tool_msg_data
        assert "tool_call_id" in tool_msg_data

        # Content must be string format for LangChain compatibility
        assert isinstance(tool_msg_data["content"], str)
        assert tool_msg_data["name"] == "KnowledgeSearchTool"
        assert tool_msg_data["tool_call_id"] == "format_compliance_test"

        # Formatted content should contain result data
        content = tool_msg_data["content"]
        assert "Test result 1" in content
        assert "Test result 2" in content

    @pytest.mark.asyncio
    async def test_behavioral_error_resilience(self):
        """
        BEHAVIORAL TEST: Step 99 must handle errors gracefully and still provide
        valid tool results for pipeline continuity.
        """

        error_test_cases = [
            # Missing tool result
            {"ctx": {"tool_name": "TestTool", "tool_call_id": "call_1"}, "should_format": True},
            # Malformed tool result
            {
                "ctx": {"tool_name": "TestTool", "tool_call_id": "call_2", "tool_result": "invalid"},
                "should_format": True,
            },
            # None values
            {"ctx": {"tool_name": None, "tool_call_id": "call_3", "tool_result": None}, "should_format": True},
        ]

        for case in error_test_cases:
            case["ctx"]["request_id"] = "error_resilience_test"
            result = await step_99__tool_results(ctx=case["ctx"])

            # Must still provide valid tool message data
            if case["should_format"]:
                assert "tool_message_data" in result
                assert "formatted_tool_result" in result
                assert result["next_step"] == 101

            # Error information should be captured
            if result.get("tool_results_processed") is False:
                assert "error" in result
