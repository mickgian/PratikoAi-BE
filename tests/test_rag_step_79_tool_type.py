"""
Tests for RAG Step 79 — Tool type? (RAG.routing.tool.type)

Test coverage:
- Unit tests: Tool type detection, routing decisions, error handling
- Integration tests: Step 78→79, Step 79→80/81/82/83
- Parity tests: Behavioral definition validation
"""

import asyncio
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.orchestrators.routing import step_79__tool_type


class TestStep79ToolType:
    """Unit tests for Step 79 tool type detection and routing"""

    @pytest.fixture
    def context_knowledge_tool(self) -> dict[str, Any]:
        """Context with Knowledge Search tool call"""
        return {
            "rag_step": 78,
            "step_id": "RAG.platform.langgraphagent.tool.call.execute.tools",
            "tool_calls": [
                {"id": "call_123", "name": "KnowledgeSearchTool", "args": {"query": "Italian VAT calculation"}}
            ],
            "current_tool_call": {
                "id": "call_123",
                "name": "KnowledgeSearchTool",
                "args": {"query": "Italian VAT calculation"},
            },
            "request_id": "knowledge_req_123",
            "session_id": "session_456",
        }

    @pytest.fixture
    def context_ccnl_tool(self) -> dict[str, Any]:
        """Context with CCNL tool call"""
        return {
            "rag_step": 78,
            "tool_calls": [
                {
                    "id": "call_456",
                    "name": "ccnl_query",
                    "args": {"query": "labor contract terms", "ccnl_type": "commerce"},
                }
            ],
            "current_tool_call": {
                "id": "call_456",
                "name": "ccnl_query",
                "args": {"query": "labor contract terms", "ccnl_type": "commerce"},
            },
            "request_id": "ccnl_req_456",
        }

    @pytest.fixture
    def context_document_tool(self) -> dict[str, Any]:
        """Context with Document Ingest tool call"""
        return {
            "rag_step": 78,
            "tool_calls": [
                {
                    "id": "call_789",
                    "name": "DocumentIngestTool",
                    "args": {"attachments": [{"filename": "invoice.pdf", "content": "base64..."}]},
                }
            ],
            "current_tool_call": {
                "id": "call_789",
                "name": "DocumentIngestTool",
                "args": {"attachments": [{"filename": "invoice.pdf", "content": "base64..."}]},
            },
            "request_id": "doc_req_789",
        }

    @pytest.fixture
    def context_faq_tool(self) -> dict[str, Any]:
        """Context with FAQ tool call"""
        return {
            "rag_step": 78,
            "tool_calls": [
                {
                    "id": "call_012",
                    "name": "FAQTool",
                    "args": {"query": "What is the corporate tax rate?", "max_results": 3},
                }
            ],
            "current_tool_call": {
                "id": "call_012",
                "name": "FAQTool",
                "args": {"query": "What is the corporate tax rate?", "max_results": 3},
            },
            "request_id": "faq_req_012",
        }

    @pytest.fixture
    def context_unknown_tool(self) -> dict[str, Any]:
        """Context with unknown/unsupported tool call"""
        return {
            "rag_step": 78,
            "tool_calls": [{"id": "call_999", "name": "UnknownTool", "args": {"param": "value"}}],
            "current_tool_call": {"id": "call_999", "name": "UnknownTool", "args": {"param": "value"}},
            "request_id": "unknown_req_999",
        }

    @pytest.mark.asyncio
    async def test_knowledge_tool_type_detection(self, context_knowledge_tool):
        """Test detection and routing for Knowledge Search tool"""

        result = await step_79__tool_type(ctx=context_knowledge_tool)

        # Verify tool type decision
        assert result["tool_type"] == "Knowledge"
        assert result["tool_name"] == "KnowledgeSearchTool"
        assert result["tool_type_detected"] is True

        # Verify routing decision
        assert result["next_step"] == 80
        assert result["next_step_id"] == "RAG.knowledge.knowledgesearchtool.search.kb.on.demand"
        assert result["route_to"] == "KBQueryTool"

        # Verify context preservation
        assert result["current_tool_call"]["name"] == "KnowledgeSearchTool"
        assert result["request_id"] == "knowledge_req_123"

    @pytest.mark.asyncio
    async def test_ccnl_tool_type_detection(self, context_ccnl_tool):
        """Test detection and routing for CCNL tool"""

        result = await step_79__tool_type(ctx=context_ccnl_tool)

        # Verify tool type decision
        assert result["tool_type"] == "CCNL"
        assert result["tool_name"] == "ccnl_query"
        assert result["tool_type_detected"] is True

        # Verify routing decision
        assert result["next_step"] == 81
        assert result["next_step_id"] == "RAG.knowledge.ccnltool.ccnl.query.query.labor.agreements"
        assert result["route_to"] == "CCNLQuery"

        # Verify CCNL-specific context
        assert "ccnl_type" in result["current_tool_call"]["args"]

    @pytest.mark.asyncio
    async def test_document_tool_type_detection(self, context_document_tool):
        """Test detection and routing for Document Ingest tool"""

        result = await step_79__tool_type(ctx=context_document_tool)

        # Verify tool type decision
        assert result["tool_type"] == "Document"
        assert result["tool_name"] == "DocumentIngestTool"
        assert result["tool_type_detected"] is True

        # Verify routing decision
        assert result["next_step"] == 82
        assert result["next_step_id"] == "RAG.docs.documentingesttool.process.process.attachments"
        assert result["route_to"] == "DocIngest"

        # Verify document context
        assert "attachments" in result["current_tool_call"]["args"]

    @pytest.mark.asyncio
    async def test_faq_tool_type_detection(self, context_faq_tool):
        """Test detection and routing for FAQ tool"""

        result = await step_79__tool_type(ctx=context_faq_tool)

        # Verify tool type decision
        assert result["tool_type"] == "FAQ"
        assert result["tool_name"] == "FAQTool"
        assert result["tool_type_detected"] is True

        # Verify routing decision
        assert result["next_step"] == 83
        assert result["next_step_id"] == "RAG.golden.faqtool.faq.query.query.golden.set"
        assert result["route_to"] == "FAQQuery"

        # Verify FAQ context
        assert result["current_tool_call"]["args"]["max_results"] == 3

    @pytest.mark.asyncio
    async def test_unknown_tool_handling(self, context_unknown_tool):
        """Test handling of unknown/unsupported tool types"""

        result = await step_79__tool_type(ctx=context_unknown_tool)

        # Verify unknown tool handling
        assert result["tool_type"] == "Unknown"
        assert result["tool_name"] == "UnknownTool"
        assert result["tool_type_detected"] is False

        # Should still route somewhere (error handling or default)
        assert "next_step" in result
        assert "route_to" in result
        assert result["routing_decision"] == "unknown_tool"

    @pytest.mark.asyncio
    async def test_multiple_tool_calls_context(self):
        """Test handling context with multiple tool calls"""

        ctx = {
            "rag_step": 78,
            "tool_calls": [{"name": "KnowledgeSearchTool", "id": "call_1"}, {"name": "FAQTool", "id": "call_2"}],
            "current_tool_call": {"name": "KnowledgeSearchTool", "id": "call_1", "args": {"query": "test"}},
            "request_id": "multi_tool_test",
        }

        result = await step_79__tool_type(ctx=ctx)

        # Should detect based on current_tool_call
        assert result["tool_type"] == "Knowledge"
        assert result["tool_name"] == "KnowledgeSearchTool"

        # Should preserve all tool calls context
        assert len(result["tool_calls"]) == 2

    @pytest.mark.asyncio
    async def test_missing_tool_call_context(self):
        """Test error handling when tool call context is missing"""

        ctx = {"rag_step": 78, "request_id": "missing_context_test"}

        result = await step_79__tool_type(ctx=ctx)

        # Should handle gracefully
        assert result["tool_type"] == "Unknown"
        assert result["tool_type_detected"] is False
        assert "error" in result
        assert result["error"].startswith("Missing tool call context")

    @pytest.mark.asyncio
    async def test_tool_type_mapping_edge_cases(self):
        """Test edge cases in tool type detection logic"""

        test_cases = [
            # Case sensitivity
            {"name": "knowledgesearchtool", "expected_type": "Unknown"},
            {"name": "KNOWLEDGESEARCHTOOL", "expected_type": "Unknown"},
            # Partial matches
            {"name": "Knowledge", "expected_type": "Unknown"},
            {"name": "SearchTool", "expected_type": "Unknown"},
            # Empty/None names
            {"name": "", "expected_type": "Unknown"},
            {"name": None, "expected_type": "Unknown"},
        ]

        for case in test_cases:
            ctx = {
                "rag_step": 78,
                "current_tool_call": {"name": case["name"], "id": "test_call", "args": {}},
                "request_id": "edge_case_test",
            }

            result = await step_79__tool_type(ctx=ctx)
            assert result["tool_type"] == case["expected_type"], f"Failed for tool name: {case['name']}"


class TestStep79IntegrationFlows:
    """Integration tests for Step 79 with neighboring steps"""

    @pytest.mark.asyncio
    async def test_step_78_to_79_execute_tools_flow(self):
        """Test flow from Step 78 (ExecuteTools) to Step 79"""

        # Simulate Step 78 output
        step_78_output = {
            "rag_step": 78,
            "step_id": "RAG.platform.langgraphagent.tool.call.execute.tools",
            "tools_executed": True,
            "tool_calls": [
                {
                    "name": "KnowledgeSearchTool",
                    "id": "call_integration_test",
                    "args": {"query": "Integration test query"},
                }
            ],
            "current_tool_call": {
                "name": "KnowledgeSearchTool",
                "id": "call_integration_test",
                "args": {"query": "Integration test query"},
            },
            "tool_execution_metadata": {"execution_time_ms": 150, "success": True},
            "request_id": "integration_test_78_79",
        }

        result = await step_79__tool_type(ctx=step_78_output)

        # Verify Step 78 context preserved
        assert result["tools_executed"] is True
        assert result["tool_execution_metadata"]["success"] is True

        # Verify Step 79 processing
        assert result["tool_type"] == "Knowledge"
        assert result["previous_step"] == 78
        assert result["next_step"] == 80

        # Verify data prepared for next step
        assert "tool_routing_metadata" in result

    @pytest.mark.asyncio
    async def test_step_79_to_80_kb_query_tool_flow(self):
        """Test flow from Step 79 to Step 80 (KBQueryTool) for Knowledge tools"""

        ctx = {
            "rag_step": 78,  # Previous step
            "current_tool_call": {
                "name": "KnowledgeSearchTool",
                "id": "kb_flow_test",
                "args": {"query": "Knowledge query test", "max_results": 5, "include_metadata": True},
            },
            "request_id": "kb_flow_test",
        }

        result = await step_79__tool_type(ctx=ctx)

        # Verify routing to KBQueryTool
        assert result["next_step"] == 80
        assert result["route_to"] == "KBQueryTool"

        # Verify knowledge search context prepared
        assert result["knowledge_search_params"]["query"] == "Knowledge query test"
        assert result["knowledge_search_params"]["max_results"] == 5

    @pytest.mark.asyncio
    async def test_step_79_to_81_ccnl_query_flow(self):
        """Test flow from Step 79 to Step 81 (CCNLQuery) for CCNL tools"""

        ctx = {
            "current_tool_call": {
                "name": "ccnl_query",
                "id": "ccnl_flow_test",
                "args": {"query": "overtime compensation", "ccnl_type": "metalworkers", "date_context": "2024"},
            },
            "request_id": "ccnl_flow_test",
        }

        result = await step_79__tool_type(ctx=ctx)

        # Verify routing to CCNLQuery
        assert result["next_step"] == 81
        assert result["route_to"] == "CCNLQuery"

        # Verify CCNL context prepared
        assert result["ccnl_query_params"]["ccnl_type"] == "metalworkers"
        assert result["ccnl_query_params"]["date_context"] == "2024"

    @pytest.mark.asyncio
    async def test_step_79_to_82_doc_ingest_flow(self):
        """Test flow from Step 79 to Step 82 (DocIngest) for Document tools"""

        ctx = {
            "current_tool_call": {
                "name": "DocumentIngestTool",
                "id": "doc_flow_test",
                "args": {
                    "attachments": [
                        {"filename": "contract.pdf", "size": 102400},
                        {"filename": "invoice.pdf", "size": 51200},
                    ],
                    "processing_options": {"extract_text": True, "detect_type": True},
                },
            },
            "request_id": "doc_flow_test",
        }

        result = await step_79__tool_type(ctx=ctx)

        # Verify routing to DocIngest
        assert result["next_step"] == 82
        assert result["route_to"] == "DocIngest"

        # Verify document processing context prepared
        assert len(result["document_ingest_params"]["attachments"]) == 2
        assert result["document_ingest_params"]["processing_options"]["extract_text"] is True

    @pytest.mark.asyncio
    async def test_step_79_to_83_faq_query_flow(self):
        """Test flow from Step 79 to Step 83 (FAQQuery) for FAQ tools"""

        ctx = {
            "current_tool_call": {
                "name": "FAQTool",
                "id": "faq_flow_test",
                "args": {
                    "query": "tax deduction limits",
                    "max_results": 5,
                    "min_confidence": "high",
                    "include_outdated": False,
                },
            },
            "request_id": "faq_flow_test",
        }

        result = await step_79__tool_type(ctx=ctx)

        # Verify routing to FAQQuery
        assert result["next_step"] == 83
        assert result["route_to"] == "FAQQuery"

        # Verify FAQ query context prepared
        assert result["faq_query_params"]["min_confidence"] == "high"
        assert result["faq_query_params"]["include_outdated"] is False


class TestStep79ParityAndBehavior:
    """Parity tests ensuring Step 79 meets behavioral definition of done"""

    @pytest.mark.asyncio
    async def test_behavioral_tool_type_decision_logic(self):
        """
        BEHAVIORAL TEST: Step 79 must make routing decisions based on tool type
        according to the exact Mermaid diagram flow specifications.
        """

        # Test all defined routing paths from Mermaid
        routing_test_cases = [
            # Knowledge → KBQueryTool (Step 80)
            {
                "tool_name": "KnowledgeSearchTool",
                "expected_type": "Knowledge",
                "expected_next_step": 80,
                "expected_route": "KBQueryTool",
            },
            # CCNL → CCNLQuery (Step 81)
            {
                "tool_name": "ccnl_query",
                "expected_type": "CCNL",
                "expected_next_step": 81,
                "expected_route": "CCNLQuery",
            },
            # Document → DocIngest (Step 82)
            {
                "tool_name": "DocumentIngestTool",
                "expected_type": "Document",
                "expected_next_step": 82,
                "expected_route": "DocIngest",
            },
            # FAQ → FAQQuery (Step 83)
            {"tool_name": "FAQTool", "expected_type": "FAQ", "expected_next_step": 83, "expected_route": "FAQQuery"},
        ]

        for case in routing_test_cases:
            ctx = {
                "current_tool_call": {"name": case["tool_name"], "id": "behavior_test", "args": {"test": "data"}},
                "request_id": "behavioral_test",
            }

            result = await step_79__tool_type(ctx=ctx)

            # Must detect correct tool type
            assert result["tool_type"] == case["expected_type"]
            # Must route to correct next step
            assert result["next_step"] == case["expected_next_step"]
            assert result["route_to"] == case["expected_route"]
            # Must be a valid decision
            assert result["tool_type_detected"] is True

    @pytest.mark.asyncio
    async def test_behavioral_mermaid_flow_compliance(self):
        """
        BEHAVIORAL TEST: Step 79 must comply with Mermaid flow:
        - Receives from ExecuteTools (Step 78)
        - Routes to KBQueryTool (80), CCNLQuery (81), DocIngest (82), or FAQQuery (83)
        """

        # From ExecuteTools (Step 78)
        from_execute_tools = {
            "rag_step": 78,
            "step_id": "RAG.platform.langgraphagent.tool.call.execute.tools",
            "current_tool_call": {"name": "KnowledgeSearchTool", "id": "mermaid_test"},
            "request_id": "mermaid_compliance_test",
        }

        result = await step_79__tool_type(ctx=from_execute_tools)

        # Must identify previous step correctly
        assert result["previous_step"] == 78

        # Must route to valid next step from Mermaid
        valid_next_steps = [80, 81, 82, 83]  # KBQueryTool, CCNLQuery, DocIngest, FAQQuery
        assert result["next_step"] in valid_next_steps

        # Must preserve ExecuteTools context
        assert result["step_id"] == "RAG.platform.langgraphagent.tool.call.execute.tools"

    @pytest.mark.asyncio
    async def test_behavioral_context_preservation(self):
        """
        BEHAVIORAL TEST: Step 79 must preserve all context while adding routing decision.
        """

        original_ctx = {
            "rag_step": 78,
            "request_id": "context_preservation_test",
            "session_id": "session_test_123",
            "user_id": "user_test_456",
            "tool_calls": [{"name": "KnowledgeSearchTool", "id": "call_1"}],
            "current_tool_call": {
                "name": "KnowledgeSearchTool",
                "id": "call_1",
                "args": {"query": "test query", "custom_param": "custom_value"},
            },
            "execution_metadata": {"timing": 150, "success": True},
            "custom_context": {"key": "value"},
        }

        result = await step_79__tool_type(ctx=original_ctx)

        # All original context must be preserved
        assert result["request_id"] == original_ctx["request_id"]
        assert result["session_id"] == original_ctx["session_id"]
        assert result["user_id"] == original_ctx["user_id"]
        assert result["tool_calls"] == original_ctx["tool_calls"]
        assert result["execution_metadata"] == original_ctx["execution_metadata"]
        assert result["custom_context"] == original_ctx["custom_context"]

        # New routing decision metadata must be added
        assert "tool_type" in result
        assert "tool_type_detected" in result
        assert "next_step" in result
        assert "route_to" in result
        assert "tool_routing_metadata" in result

    @pytest.mark.asyncio
    async def test_behavioral_structured_observability(self):
        """
        BEHAVIORAL TEST: Step 79 must implement structured observability
        with rag_step_log and rag_step_timer per MASTER_GUARDRAILS.
        """

        with (
            patch("app.orchestrators.routing.rag_step_log") as mock_log,
            patch("app.orchestrators.routing.rag_step_timer") as mock_timer,
        ):
            ctx = {
                "current_tool_call": {"name": "KnowledgeSearchTool", "id": "observability_test"},
                "request_id": "observability_test",
            }

            await step_79__tool_type(ctx=ctx)

            # Verify structured logging
            mock_log.assert_called()
            log_calls = mock_log.call_args_list

            # Check required log attributes
            start_log = log_calls[0][1]  # kwargs from first call
            assert start_log["step"] == 79
            assert start_log["step_id"] == "RAG.routing.tool.type"
            assert start_log["node_label"] == "ToolType"
            assert start_log["category"] == "routing"
            assert start_log["type"] == "decision"

            # Verify timing
            mock_timer.assert_called_with(
                79, "RAG.routing.tool.type", "ToolType", request_id="observability_test", stage="start"
            )

    @pytest.mark.asyncio
    async def test_behavioral_decision_consistency(self):
        """
        BEHAVIORAL TEST: Step 79 decisions must be consistent and deterministic
        for the same tool type inputs.
        """

        test_tool_call = {
            "name": "KnowledgeSearchTool",
            "id": "consistency_test",
            "args": {"query": "consistency test"},
        }

        ctx = {"current_tool_call": test_tool_call, "request_id": "consistency_test"}

        # Run the same decision multiple times
        results = []
        for _ in range(3):
            result = await step_79__tool_type(ctx=ctx)
            results.append(
                {"tool_type": result["tool_type"], "next_step": result["next_step"], "route_to": result["route_to"]}
            )

        # All results must be identical
        for result in results[1:]:
            assert result == results[0], "Tool type decisions must be deterministic"

    @pytest.mark.asyncio
    async def test_behavioral_error_resilience(self):
        """
        BEHAVIORAL TEST: Step 79 must handle errors gracefully and still provide
        routing decisions for pipeline continuity.
        """

        error_test_cases = [
            # Missing tool call data
            {"ctx": {}, "should_route": True},
            # Malformed tool call
            {"ctx": {"current_tool_call": {}}, "should_route": True},
            # None values
            {"ctx": {"current_tool_call": None}, "should_route": True},
        ]

        for case in error_test_cases:
            case["ctx"]["request_id"] = "error_resilience_test"
            result = await step_79__tool_type(ctx=case["ctx"])

            # Must still provide routing decision even with errors
            if case["should_route"]:
                assert "next_step" in result
                assert "route_to" in result
                assert "tool_type" in result

            # Error information should be captured
            if result.get("tool_type") == "Unknown":
                assert "error" in result or result.get("tool_type_detected") is False
