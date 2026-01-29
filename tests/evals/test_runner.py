"""Tests for evaluation runner.

TDD: RED phase - Write tests first, then implement.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from evals.config import (
    EvalConfig,
    RunMode,
    create_local_config,
    create_nightly_config,
    create_pr_config,
)
from evals.runner import (
    EvalRunner,
    RunResult,
    load_test_cases,
)
from evals.schemas.test_case import (
    GradeResult,
    GraderType,
    TestCase,
    TestCaseCategory,
)


class TestEvalConfig:
    """Tests for EvalConfig."""

    def test_default_config(self) -> None:
        """Test default configuration."""
        config = EvalConfig()
        assert config.mode == RunMode.LOCAL
        assert config.use_ollama is False
        assert config.fail_threshold == 1.0

    def test_pr_config(self) -> None:
        """Test PR mode configuration."""
        config = create_pr_config()
        assert config.mode == RunMode.PR
        assert config.use_ollama is False
        assert config.fail_threshold == 1.0
        assert config.graders == ["code"]

    def test_local_config(self) -> None:
        """Test local mode configuration."""
        config = create_local_config()
        assert config.mode == RunMode.LOCAL
        assert config.use_ollama is True

    def test_nightly_config(self) -> None:
        """Test nightly mode configuration."""
        config = create_nightly_config()
        assert config.mode == RunMode.NIGHTLY
        assert config.k_attempts == 3
        assert config.use_ollama is True


class TestRunMode:
    """Tests for RunMode enum."""

    def test_run_modes(self) -> None:
        """Test all run modes exist."""
        assert RunMode.PR.value == "pr"
        assert RunMode.LOCAL.value == "local"
        assert RunMode.NIGHTLY.value == "nightly"
        assert RunMode.WEEKLY.value == "weekly"


class TestLoadTestCases:
    """Tests for load_test_cases function."""

    def test_load_from_json_file(self, tmp_path: Path) -> None:
        """Test loading test cases from JSON file."""
        test_file = tmp_path / "test_cases.json"
        test_data = [
            {
                "id": "TEST-001",
                "category": "routing",
                "query": "Test query 1",
            },
            {
                "id": "TEST-002",
                "category": "retrieval",
                "query": "Test query 2",
            },
        ]
        test_file.write_text(json.dumps(test_data))

        cases = load_test_cases(test_file)

        assert len(cases) == 2
        assert cases[0].id == "TEST-001"
        assert cases[1].category == TestCaseCategory.RETRIEVAL

    def test_load_from_directory(self, tmp_path: Path) -> None:
        """Test loading test cases from directory."""
        (tmp_path / "routing.json").write_text(
            json.dumps(
                [
                    {"id": "R-001", "category": "routing", "query": "Routing query"},
                ]
            )
        )
        (tmp_path / "retrieval.json").write_text(
            json.dumps(
                [
                    {"id": "RET-001", "category": "retrieval", "query": "Retrieval query"},
                ]
            )
        )

        cases = load_test_cases(tmp_path)

        assert len(cases) == 2

    def test_load_empty_file(self, tmp_path: Path) -> None:
        """Test loading empty file."""
        test_file = tmp_path / "empty.json"
        test_file.write_text("[]")

        cases = load_test_cases(test_file)

        assert len(cases) == 0

    def test_load_invalid_json(self, tmp_path: Path) -> None:
        """Test loading invalid JSON file."""
        test_file = tmp_path / "invalid.json"
        test_file.write_text("not valid json")

        with pytest.raises(json.JSONDecodeError):
            load_test_cases(test_file)


class TestRunResult:
    """Tests for RunResult."""

    def test_create_run_result(self) -> None:
        """Test creating a run result."""
        result = RunResult(
            success=True,
            total=10,
            passed=10,
            failed=0,
            pass_rate=1.0,
            duration_seconds=5.5,
            exit_code=0,
        )
        assert result.success is True
        assert result.exit_code == 0

    def test_failed_run_result(self) -> None:
        """Test failed run result."""
        result = RunResult(
            success=False,
            total=10,
            passed=8,
            failed=2,
            pass_rate=0.8,
            duration_seconds=10.0,
            exit_code=1,
            failure_reason="Regression threshold not met",
        )
        assert result.success is False
        assert result.exit_code == 1


class TestEvalRunner:
    """Tests for EvalRunner."""

    @pytest.fixture
    def runner(self) -> EvalRunner:
        """Create an eval runner with default config."""
        return EvalRunner(EvalConfig())

    @pytest.fixture
    def sample_test_cases(self) -> list[TestCase]:
        """Create sample test cases."""
        return [
            TestCase(
                id="ROUTING-001",
                category=TestCaseCategory.ROUTING,
                query="Test query 1",
                expected_route="technical_research",
                grader_type=GraderType.CODE,
            ),
            TestCase(
                id="ROUTING-002",
                category=TestCaseCategory.ROUTING,
                query="Test query 2",
                expected_route="chitchat",
                grader_type=GraderType.CODE,
            ),
        ]

    @pytest.mark.asyncio
    async def test_run_with_all_passing(
        self,
        runner: EvalRunner,
        sample_test_cases: list[TestCase],
    ) -> None:
        """Test running evaluations when all pass."""
        # Mock the grader to always pass
        with patch.object(runner, "_grade_test_case") as mock_grade:
            mock_grade.return_value = GradeResult(score=0.95, passed=True, reasoning="Good")

            result = await runner.run(sample_test_cases)

        assert result.success is True
        assert result.passed == 2
        assert result.failed == 0
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_run_with_failures(
        self,
        runner: EvalRunner,
        sample_test_cases: list[TestCase],
    ) -> None:
        """Test running evaluations with some failures."""
        with patch.object(runner, "_grade_test_case") as mock_grade:
            mock_grade.side_effect = [
                GradeResult(score=0.9, passed=True),
                GradeResult(score=0.4, passed=False),
            ]

            result = await runner.run(sample_test_cases)

        assert result.success is False
        assert result.passed == 1
        assert result.failed == 1
        assert result.exit_code == 1

    @pytest.mark.asyncio
    async def test_run_filters_by_category(
        self,
        runner: EvalRunner,
    ) -> None:
        """Test running only specific categories."""
        test_cases = [
            TestCase(id="R-1", category=TestCaseCategory.ROUTING, query="Q1"),
            TestCase(id="RET-1", category=TestCaseCategory.RETRIEVAL, query="Q2"),
            TestCase(id="R-2", category=TestCaseCategory.ROUTING, query="Q3"),
        ]

        with patch.object(runner, "_grade_test_case") as mock_grade:
            mock_grade.return_value = GradeResult(score=0.9, passed=True)

            result = await runner.run(
                test_cases,
                categories=[TestCaseCategory.ROUTING],
            )

        # Should only run routing tests (2 of 3)
        assert result.total == 2

    @pytest.mark.asyncio
    async def test_run_filters_by_grader_type(
        self,
        runner: EvalRunner,
    ) -> None:
        """Test running only specific grader types."""
        test_cases = [
            TestCase(
                id="C-1",
                category=TestCaseCategory.ROUTING,
                query="Q1",
                grader_type=GraderType.CODE,
            ),
            TestCase(
                id="M-1",
                category=TestCaseCategory.ROUTING,
                query="Q2",
                grader_type=GraderType.MODEL,
            ),
        ]

        with patch.object(runner, "_grade_test_case") as mock_grade:
            mock_grade.return_value = GradeResult(score=0.9, passed=True)

            result = await runner.run(
                test_cases,
                grader_types=[GraderType.CODE],
            )

        assert result.total == 1

    @pytest.mark.asyncio
    async def test_run_generates_report(
        self,
        runner: EvalRunner,
        sample_test_cases: list[TestCase],
        tmp_path: Path,
    ) -> None:
        """Test that run generates a report file."""
        runner.config.report_dir = tmp_path

        with patch.object(runner, "_grade_test_case") as mock_grade:
            mock_grade.return_value = GradeResult(score=0.9, passed=True)

            result = await runner.run(sample_test_cases)

        # Report should be generated
        assert result.report_path is not None
        assert Path(result.report_path).exists()

    @pytest.mark.asyncio
    async def test_run_regression_mode(
        self,
        sample_test_cases: list[TestCase],
    ) -> None:
        """Test running in regression-only mode."""
        # Mark one as regression
        sample_test_cases[0].is_regression = True

        config = EvalConfig(regression_only=True)
        runner = EvalRunner(config)

        with patch.object(runner, "_grade_test_case") as mock_grade:
            mock_grade.return_value = GradeResult(score=0.9, passed=True)

            result = await runner.run(sample_test_cases)

        # Should only run regression tests
        assert result.total == 1

    @pytest.mark.asyncio
    async def test_check_threshold(
        self,
        runner: EvalRunner,
        sample_test_cases: list[TestCase],
    ) -> None:
        """Test threshold checking."""
        runner.config.fail_threshold = 1.0  # 100% required

        with patch.object(runner, "_grade_test_case") as mock_grade:
            mock_grade.side_effect = [
                GradeResult(score=0.9, passed=True),
                GradeResult(score=0.4, passed=False),  # One fails
            ]

            result = await runner.run(sample_test_cases)

        # Should fail because 50% < 100%
        assert result.success is False
        assert "threshold" in result.failure_reason.lower()
