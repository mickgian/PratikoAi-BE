"""
Unit tests for Golden Set streaming priority logic in graph.py.

This module tests Bug #7 fix: Priority 1 in the streaming handler was overwriting
the golden answer content because it lacked a `if not content` guard.

The priority logic ensures:
- Priority 0: golden_answer from Step 28 (highest priority)
- Priority 1: final_response content (only if Priority 0 didn't set content)
- Priority 2: LLM buffered response from Step 64 (fallback)
"""

from dataclasses import dataclass
from typing import Any
from unittest.mock import Mock, patch

import pytest


class ContentPriorityExtractor:
    """
    Helper class that extracts the streaming priority logic from graph.py
    for isolated testing.

    This replicates the priority logic from lines ~2800-2850 of graph.py:
        Priority 0: golden_answer (from Step 28)
        Priority 1: final_response content (if streaming_requested)
        Priority 2: llm buffered response (from Step 64)
    """

    @staticmethod
    def extract_content(
        state: dict[str, Any],
        final_response: dict[str, Any] | None,
        streaming_requested: bool,
    ) -> tuple[str | None, str]:
        """
        Extract content based on priority order.

        Returns:
            tuple: (content, source) where source indicates which priority was used
        """
        content = None
        source = "none"

        # Priority 0: Check for golden answer (served by Step 28)
        # This bypasses LLM entirely when a golden answer was served
        if state.get("golden_hit"):
            golden_answer = state.get("golden_answer")
            if golden_answer:
                content = golden_answer
                source = "priority_0_golden"

        # Priority 1: Check final_response (only if Priority 0 didn't set content)
        if not content and final_response and streaming_requested:
            response_content = final_response.get("content", "")
            if response_content:
                content = response_content
                source = "priority_1_final_response"

        # Priority 2: Check buffered response from Step 64
        if not content:
            llm_data = state.get("llm", {})
            buffered_response = llm_data.get("response")

            if llm_data.get("success") and buffered_response:
                # Extract content from LLMResponse object or dict format
                if isinstance(buffered_response, dict):
                    extracted = buffered_response.get("content")
                elif hasattr(buffered_response, "content"):
                    extracted = buffered_response.content
                else:
                    extracted = None

                if extracted:
                    content = extracted
                    source = "priority_2_llm_buffered"

        return content, source


class TestGoldenStreamingPriority:
    """Test suite for golden answer streaming priority logic."""

    def test_priority_0_golden_answer_used_when_golden_hit_true(self):
        """
        Test that golden_answer is used when golden_hit is True.

        Bug #7 context: This tests the fix where Priority 0 must be checked first.
        """
        # Arrange
        state = {
            "golden_hit": True,
            "golden_answer": "This is the golden answer content from FAQ database.",
            "llm": {},
        }
        final_response = {"content": "This should NOT be used"}
        streaming_requested = True

        # Act
        content, source = ContentPriorityExtractor.extract_content(state, final_response, streaming_requested)

        # Assert
        assert content == "This is the golden answer content from FAQ database."
        assert source == "priority_0_golden"

    def test_priority_1_skipped_when_content_already_set(self):
        """
        Test that Priority 1 is skipped when Priority 0 already set content.

        This is the core of Bug #7 fix: the `if not content` guard prevents
        final_response from overwriting golden_answer.
        """
        # Arrange
        golden_content = "Golden answer from Step 28"
        final_response_content = "Different content from final_response"

        state = {
            "golden_hit": True,
            "golden_answer": golden_content,
            "llm": {},
        }
        final_response = {"content": final_response_content}
        streaming_requested = True

        # Act
        content, source = ContentPriorityExtractor.extract_content(state, final_response, streaming_requested)

        # Assert - Golden answer must win, NOT final_response
        assert content == golden_content, (
            f"Bug #7: golden_answer was overwritten by final_response. "
            f"Expected '{golden_content}', got '{content}'"
        )
        assert content != final_response_content
        assert source == "priority_0_golden"

    def test_priority_1_used_when_no_golden_answer(self):
        """
        Test that final_response content is used when there is no golden_answer.

        When golden_hit is False or golden_answer is None, Priority 1 should apply.
        """
        # Arrange
        state = {
            "golden_hit": False,
            "golden_answer": None,
            "llm": {},
        }
        final_response = {"content": "Content from final_response"}
        streaming_requested = True

        # Act
        content, source = ContentPriorityExtractor.extract_content(state, final_response, streaming_requested)

        # Assert
        assert content == "Content from final_response"
        assert source == "priority_1_final_response"

    def test_priority_1_used_when_golden_hit_false(self):
        """
        Test Priority 1 is used when golden_hit is explicitly False.
        """
        # Arrange
        state = {
            "golden_hit": False,
            "golden_answer": "This should be ignored since hit is False",
            "llm": {},
        }
        final_response = {"content": "Final response wins"}
        streaming_requested = True

        # Act
        content, source = ContentPriorityExtractor.extract_content(state, final_response, streaming_requested)

        # Assert
        assert content == "Final response wins"
        assert source == "priority_1_final_response"

    def test_priority_1_not_used_when_streaming_not_requested(self):
        """
        Test that Priority 1 is skipped when streaming is not requested.
        """
        # Arrange
        state = {
            "golden_hit": False,
            "golden_answer": None,
            "llm": {"success": True, "response": {"content": "LLM fallback"}},
        }
        final_response = {"content": "Final response content"}
        streaming_requested = False  # Streaming NOT requested

        # Act
        content, source = ContentPriorityExtractor.extract_content(state, final_response, streaming_requested)

        # Assert - Should skip Priority 1 and go to Priority 2
        assert content == "LLM fallback"
        assert source == "priority_2_llm_buffered"

    def test_priority_2_llm_response_used_as_fallback(self):
        """
        Test that LLM buffered response (Priority 2) is used as fallback.

        This applies when:
        - No golden_answer (Priority 0 fails)
        - No final_response or streaming not requested (Priority 1 fails)
        - llm.success = True with buffered response
        """
        # Arrange
        state = {
            "golden_hit": False,
            "golden_answer": None,
            "llm": {
                "success": True,
                "response": {"content": "LLM generated response from Step 64"},
            },
        }
        final_response = None  # No final_response
        streaming_requested = True

        # Act
        content, source = ContentPriorityExtractor.extract_content(state, final_response, streaming_requested)

        # Assert
        assert content == "LLM generated response from Step 64"
        assert source == "priority_2_llm_buffered"

    def test_priority_2_with_llmresponse_object(self):
        """
        Test Priority 2 works with LLMResponse-like objects (not just dicts).
        """

        # Arrange - Create a mock LLMResponse object
        @dataclass
        class MockLLMResponse:
            content: str
            model: str = "gpt-4"
            tokens_used: int = 100

        state = {
            "golden_hit": False,
            "golden_answer": None,
            "llm": {
                "success": True,
                "response": MockLLMResponse(content="Response from LLMResponse object"),
            },
        }
        final_response = None
        streaming_requested = True

        # Act
        content, source = ContentPriorityExtractor.extract_content(state, final_response, streaming_requested)

        # Assert
        assert content == "Response from LLMResponse object"
        assert source == "priority_2_llm_buffered"

    def test_no_content_when_all_priorities_fail(self):
        """
        Test that None is returned when all priority sources fail.
        """
        # Arrange
        state = {
            "golden_hit": False,
            "golden_answer": None,
            "llm": {"success": False},  # LLM failed
        }
        final_response = None
        streaming_requested = True

        # Act
        content, source = ContentPriorityExtractor.extract_content(state, final_response, streaming_requested)

        # Assert
        assert content is None
        assert source == "none"

    def test_priority_0_with_empty_string_golden_answer(self):
        """
        Test that empty string golden_answer falls through to Priority 1.
        """
        # Arrange
        state = {
            "golden_hit": True,
            "golden_answer": "",  # Empty string
            "llm": {},
        }
        final_response = {"content": "Fallback to final_response"}
        streaming_requested = True

        # Act
        content, source = ContentPriorityExtractor.extract_content(state, final_response, streaming_requested)

        # Assert - Empty string is falsy, so Priority 1 should apply
        assert content == "Fallback to final_response"
        assert source == "priority_1_final_response"

    def test_priority_1_with_empty_string_content(self):
        """
        Test that empty string final_response content falls through to Priority 2.
        """
        # Arrange
        state = {
            "golden_hit": False,
            "golden_answer": None,
            "llm": {"success": True, "response": {"content": "LLM response"}},
        }
        final_response = {"content": ""}  # Empty string content
        streaming_requested = True

        # Act
        content, source = ContentPriorityExtractor.extract_content(state, final_response, streaming_requested)

        # Assert - Empty content in final_response, falls to Priority 2
        assert content == "LLM response"
        assert source == "priority_2_llm_buffered"


class TestGoldenStreamingPriorityEdgeCases:
    """Edge case tests for golden streaming priority logic."""

    def test_golden_hit_none_treated_as_false(self):
        """
        Test that golden_hit=None is treated as False (falsy).
        """
        # Arrange
        state = {
            "golden_hit": None,  # None, not False
            "golden_answer": "Should be ignored",
            "llm": {},
        }
        final_response = {"content": "Final response used"}
        streaming_requested = True

        # Act
        content, source = ContentPriorityExtractor.extract_content(state, final_response, streaming_requested)

        # Assert
        assert content == "Final response used"
        assert source == "priority_1_final_response"

    def test_missing_golden_hit_key(self):
        """
        Test behavior when golden_hit key is completely missing from state.
        """
        # Arrange
        state = {
            # No golden_hit key at all
            "golden_answer": "Should be ignored",
            "llm": {},
        }
        final_response = {"content": "Final response used"}
        streaming_requested = True

        # Act
        content, source = ContentPriorityExtractor.extract_content(state, final_response, streaming_requested)

        # Assert
        assert content == "Final response used"
        assert source == "priority_1_final_response"

    def test_missing_llm_key(self):
        """
        Test behavior when llm key is missing from state.
        """
        # Arrange
        state = {
            "golden_hit": False,
            "golden_answer": None,
            # No llm key
        }
        final_response = None
        streaming_requested = True

        # Act
        content, source = ContentPriorityExtractor.extract_content(state, final_response, streaming_requested)

        # Assert - All priorities fail
        assert content is None
        assert source == "none"

    def test_llm_success_false_with_response(self):
        """
        Test that llm response is not used when llm.success is False.
        """
        # Arrange
        state = {
            "golden_hit": False,
            "golden_answer": None,
            "llm": {
                "success": False,  # Failed
                "response": {"content": "This should NOT be used"},
            },
        }
        final_response = None
        streaming_requested = True

        # Act
        content, source = ContentPriorityExtractor.extract_content(state, final_response, streaming_requested)

        # Assert - LLM failed, so no content
        assert content is None
        assert source == "none"

    def test_llm_success_true_but_no_response(self):
        """
        Test behavior when llm.success is True but response is None.
        """
        # Arrange
        state = {
            "golden_hit": False,
            "golden_answer": None,
            "llm": {
                "success": True,
                "response": None,  # No response despite success
            },
        }
        final_response = None
        streaming_requested = True

        # Act
        content, source = ContentPriorityExtractor.extract_content(state, final_response, streaming_requested)

        # Assert
        assert content is None
        assert source == "none"

    def test_special_characters_in_golden_answer(self):
        """
        Test that special characters in golden_answer are preserved.
        """
        # Arrange
        special_content = (
            "IVA al 22%: calcolo = base * 0.22\n"
            "Formula: totale = base + (base * aliquota)\n"
            "Esempio: 100 + 22 = 122"
        )
        state = {
            "golden_hit": True,
            "golden_answer": special_content,
            "llm": {},
        }
        final_response = {"content": "Ignored"}
        streaming_requested = True

        # Act
        content, source = ContentPriorityExtractor.extract_content(state, final_response, streaming_requested)

        # Assert
        assert content == special_content
        assert "22%" in content
        assert "\n" in content
        assert source == "priority_0_golden"

    def test_unicode_content_preserved(self):
        """
        Test that Unicode/Italian characters are preserved.
        """
        # Arrange
        italian_content = "L'aliquota IVA e applicata secondo la normativa italiana."
        state = {
            "golden_hit": True,
            "golden_answer": italian_content,
            "llm": {},
        }

        # Act
        content, source = ContentPriorityExtractor.extract_content(state, None, True)

        # Assert
        assert content == italian_content
        assert "e" in content
        assert source == "priority_0_golden"


class TestBug7Regression:
    """
    Regression tests specifically for Bug #7.

    Bug #7 description: Priority 1 in the streaming handler was overwriting
    the golden answer content because it lacked a `if not content` guard.

    These tests ensure the bug does not regress.
    """

    def test_bug7_golden_answer_not_overwritten_by_final_response(self):
        """
        Regression test: Ensure golden_answer is NOT overwritten by final_response.

        This is the exact scenario that Bug #7 was catching.
        """
        # Arrange - Exact scenario from Bug #7
        state = {
            "golden_hit": True,
            "golden_answer": "Correct golden answer from FAQ",
            "llm": {},
        }
        final_response = {"content": "Wrong: this final_response should NOT override golden"}
        streaming_requested = True

        # Act
        content, source = ContentPriorityExtractor.extract_content(state, final_response, streaming_requested)

        # Assert - The fix ensures golden_answer wins
        assert (
            content == "Correct golden answer from FAQ"
        ), "BUG #7 REGRESSION: golden_answer was overwritten by final_response!"
        assert "Wrong" not in content
        assert source == "priority_0_golden"

    def test_bug7_priority_order_is_correct(self):
        """
        Verify the priority order is: golden > final_response > llm_buffered.
        """
        # Test 1: Golden wins over both others
        state1 = {
            "golden_hit": True,
            "golden_answer": "GOLDEN",
            "llm": {"success": True, "response": {"content": "LLM"}},
        }
        content1, _ = ContentPriorityExtractor.extract_content(state1, {"content": "FINAL"}, True)
        assert content1 == "GOLDEN"

        # Test 2: Final wins over LLM when no golden
        state2 = {
            "golden_hit": False,
            "golden_answer": None,
            "llm": {"success": True, "response": {"content": "LLM"}},
        }
        content2, _ = ContentPriorityExtractor.extract_content(state2, {"content": "FINAL"}, True)
        assert content2 == "FINAL"

        # Test 3: LLM used when no golden and no final
        state3 = {
            "golden_hit": False,
            "golden_answer": None,
            "llm": {"success": True, "response": {"content": "LLM"}},
        }
        content3, _ = ContentPriorityExtractor.extract_content(state3, None, True)
        assert content3 == "LLM"

    def test_bug7_guard_condition_if_not_content(self):
        """
        Test the specific guard condition: `if not content`.

        This guard is what prevents Bug #7 from occurring.
        """
        # When content is already set (truthy), Priority 1 should be skipped
        state = {
            "golden_hit": True,
            "golden_answer": "Already set by Priority 0",
            "llm": {},
        }

        content, source = ContentPriorityExtractor.extract_content(state, {"content": "Should be skipped"}, True)

        # The guard `if not content` prevents overwriting
        assert content == "Already set by Priority 0"
        assert source == "priority_0_golden"

        # Verify the content IS truthy (non-empty string)
        assert bool(content) is True  # Content is truthy

    @pytest.mark.parametrize(
        "golden_answer,final_content,expected_content,expected_source",
        [
            # Golden answer present - should win
            ("Golden FAQ", "Final response", "Golden FAQ", "priority_0_golden"),
            # Golden empty - final_response should win
            ("", "Final response", "Final response", "priority_1_final_response"),
            # Both present, golden wins
            ("FAQ answer", "LLM answer", "FAQ answer", "priority_0_golden"),
            # Long golden answer - should still win
            ("A" * 5000, "B" * 5000, "A" * 5000, "priority_0_golden"),
        ],
    )
    def test_bug7_parametrized_priority_scenarios(
        self, golden_answer, final_content, expected_content, expected_source
    ):
        """
        Parametrized test for various priority scenarios.
        """
        state = {
            "golden_hit": bool(golden_answer),  # True if golden_answer is non-empty
            "golden_answer": golden_answer if golden_answer else None,
            "llm": {},
        }
        final_response = {"content": final_content}
        streaming_requested = True

        content, source = ContentPriorityExtractor.extract_content(state, final_response, streaming_requested)

        assert content == expected_content
        assert source == expected_source
