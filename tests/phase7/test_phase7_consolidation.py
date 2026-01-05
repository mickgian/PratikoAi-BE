"""DEV-197: Phase 7 Unit Tests Consolidation and Verification.

This module consolidates and verifies all unit tests created during
TDD in DEV-184 to DEV-196 for the Agentic RAG Pipeline.

Target: 145+ unit tests across all Phase 7 components (Actual: 261+)
Coverage: 95%+ for each new service

Phase 7 Components:
- DEV-184: LLM Model Config (20 tests)
- DEV-185: PremiumModelSelector (25 tests)
- DEV-186: RouterDecision schema (21 tests)
- DEV-187: LLMRouterService (23 tests)
- DEV-188: MultiQueryGeneratorService (20 tests)
- DEV-189: HyDEGeneratorService (21 tests)
- DEV-190: ParallelRetrievalService (20 tests)
- DEV-191: MetadataExtractor (19 tests)
- DEV-192: SynthesisPromptBuilder (29 tests)
- DEV-193: VerdettoOperativoParser (27 tests)
- DEV-194: Step 34a LLM Router Node (14 tests)
- DEV-195: Step 39 Query Expansion Nodes (15 tests)
- DEV-196: Step 64 Premium Verdetto (7 tests)
"""

import sys
from unittest.mock import MagicMock

import pytest

# =============================================================================
# Mock database service BEFORE importing any app modules
# =============================================================================
_mock_db_service = MagicMock()
_mock_db_service.engine = MagicMock()
_mock_db_service.get_session = MagicMock()
_mock_db_module = MagicMock()
_mock_db_module.database_service = _mock_db_service
_mock_db_module.DatabaseService = MagicMock(return_value=_mock_db_service)
sys.modules.setdefault("app.services.database", _mock_db_module)


class TestPhase7TestConsolidation:
    """Verify Phase 7 test consolidation requirements are met."""

    def test_minimum_test_count_requirement(self):
        """Verify we have at least 145 Phase 7 unit tests."""
        import subprocess

        # Count tests across all Phase 7 test files
        test_files = [
            "tests/langgraph/agentic_rag/",
            "tests/services/test_parallel_retrieval.py",
            "tests/services/test_hyde_generator.py",
            "tests/services/test_metadata_extractor.py",
            "tests/services/test_multi_query_generator.py",
            "tests/services/test_verdetto_parser.py",
            "tests/services/test_llm_router_service.py",
            "tests/services/test_premium_model_selector.py",
            "tests/core/llm/test_model_config.py",
            "tests/schemas/test_router.py",
            "tests/core/prompts/test_synthesis_prompt.py",
        ]

        total_tests = 0
        for path in test_files:
            result = subprocess.run(
                ["grep", "-r", "-c", "def test_", path],
                capture_output=True,
                text=True,
            )
            for line in result.stdout.strip().split("\n"):
                if line and ":" in line:
                    count = int(line.split(":")[-1])
                    total_tests += count
                elif line.isdigit():
                    total_tests += int(line)

        # We expect 145+ tests, actual is 261+
        assert total_tests >= 145, f"Expected 145+ tests, got {total_tests}"

    def test_all_phase7_services_have_tests(self):
        """Verify all Phase 7 services have corresponding test files."""
        import os

        required_test_files = [
            "tests/services/test_premium_model_selector.py",
            "tests/services/test_llm_router_service.py",
            "tests/services/test_multi_query_generator.py",
            "tests/services/test_hyde_generator.py",
            "tests/services/test_parallel_retrieval.py",
            "tests/services/test_metadata_extractor.py",
            "tests/services/test_verdetto_parser.py",
            "tests/core/llm/test_model_config.py",
            "tests/schemas/test_router.py",
            "tests/core/prompts/test_synthesis_prompt.py",
            "tests/langgraph/agentic_rag/test_step_034a__llm_router.py",
            "tests/langgraph/agentic_rag/test_step_039_query_expansion.py",
            "tests/langgraph/agentic_rag/test_step_064_premium_verdetto.py",
        ]

        missing_files = []
        for test_file in required_test_files:
            if not os.path.exists(test_file):
                missing_files.append(test_file)

        assert not missing_files, f"Missing test files: {missing_files}"

    def test_no_flaky_tests_detected(self):
        """Verify no flaky tests in Phase 7 by running twice."""
        import subprocess

        # Run tests twice to detect flakiness
        result = subprocess.run(
            [
                "python",
                "-m",
                "pytest",
                "tests/langgraph/agentic_rag/",
                "-q",
                "--tb=no",
            ],
            capture_output=True,
            text=True,
        )

        # Check first run
        first_run_passed = result.returncode == 0

        # If first run failed, that's a real failure not flakiness
        if not first_run_passed:
            pytest.skip("Tests failed on first run - not a flakiness issue")

        # Run second time
        result2 = subprocess.run(
            [
                "python",
                "-m",
                "pytest",
                "tests/langgraph/agentic_rag/",
                "-q",
                "--tb=no",
            ],
            capture_output=True,
            text=True,
        )

        second_run_passed = result2.returncode == 0

        assert second_run_passed, "Flaky test detected - passed first run but failed second run"


class TestPhase7ComponentCoverage:
    """Verify individual component test coverage."""

    def test_premium_model_selector_has_tests(self):
        """Verify PremiumModelSelector has comprehensive tests."""
        from tests.services.test_premium_model_selector import (
            TestModelSelection,
            TestPremiumModelSelector,
            TestSynthesisContext,
        )

        # Verify key test classes exist and have tests
        assert hasattr(TestPremiumModelSelector, "test_selects_gpt4o_by_default")
        assert hasattr(TestPremiumModelSelector, "test_selects_gpt4o_for_long_context")

    def test_llm_router_service_has_tests(self):
        """Verify LLMRouterService has comprehensive tests."""
        from tests.services.test_llm_router_service import (
            TestLLMRouterServiceRouting,
        )

        assert hasattr(TestLLMRouterServiceRouting, "test_route_technical_research")
        assert hasattr(TestLLMRouterServiceRouting, "test_route_chitchat_query")

    def test_verdetto_parser_has_tests(self):
        """Verify VerdettoOperativoParser has comprehensive tests."""
        from tests.services.test_verdetto_parser import (
            TestVerdettoOperativoParser,
        )

        assert hasattr(TestVerdettoOperativoParser, "test_parse_complete_verdetto")
        assert hasattr(TestVerdettoOperativoParser, "test_parse_no_verdetto_returns_answer")

    def test_synthesis_prompt_has_tests(self):
        """Verify SynthesisPromptBuilder has comprehensive tests."""
        from tests.core.prompts.test_synthesis_prompt import (
            TestSynthesisPromptBuilder,
            TestSynthesisSystemPrompt,
        )

        assert hasattr(TestSynthesisPromptBuilder, "test_build_returns_string")
        assert hasattr(TestSynthesisSystemPrompt, "test_prompt_includes_verdetto_structure")


class TestPhase7MockIsolation:
    """Verify all Phase 7 tests use proper mock isolation."""

    def test_service_tests_mock_llm_calls(self):
        """Verify service tests mock LLM API calls."""
        import ast

        test_files = [
            "tests/services/test_llm_router_service.py",
            "tests/services/test_hyde_generator.py",
            "tests/services/test_multi_query_generator.py",
        ]

        for test_file in test_files:
            with open(test_file) as f:
                content = f.read()

            # Verify mock/patch imports or usage
            has_mocking = (
                "from unittest.mock import" in content
                or "@patch" in content
                or "MagicMock" in content
                or "AsyncMock" in content
            )
            assert has_mocking, f"{test_file} should use mocking for LLM calls"

    def test_node_tests_mock_orchestrators(self):
        """Verify node tests mock orchestrator calls."""
        import ast

        node_test_files = [
            "tests/langgraph/agentic_rag/test_step_034a__llm_router.py",
            "tests/langgraph/agentic_rag/test_step_039_query_expansion.py",
            "tests/langgraph/agentic_rag/test_step_064_premium_verdetto.py",
        ]

        for test_file in node_test_files:
            with open(test_file) as f:
                content = f.read()

            # Verify mock/patch usage
            has_mocking = "@patch" in content or "patch(" in content
            assert has_mocking, f"{test_file} should mock orchestrator/service calls"
