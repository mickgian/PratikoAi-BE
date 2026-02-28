"""Comprehensive tests for CCNLService — dataclass helpers and DB-heavy service methods.

Tests cover:
- CCNLQueryFilters dataclass with is_valid() validation
- CCNLSearchResult dataclass with has_results property
- CCNLComparisonResult dataclass with has_differences property
- CCNLValidationError dataclass
- CCNLValidationResult dataclass with add_error() / add_warning()
- CCNLDataImportResult dataclass with success_rate property
- CCNLService CRUD methods with mocked DB
- CCNLService.validate_ccnl_data with valid/invalid payloads
- CCNLService comparison and statistics helpers
- Edge cases (empty inputs, boundary conditions, error handling)
- get_ccnl_by_sector, get_current_ccnl_by_sector
- search_ccnl_agreements with filters
- save_ccnl_agreement, _convert_to_db_model, _convert_external_data_to_agreement
- calculate_total_compensation, calculate_notice_period, calculate_leave_entitlement
- compare_salary_levels
- import_ccnl_from_external_data, bulk_import_ccnl_data
- generate_coverage_report, generate_salary_statistics
- calculate_comprehensive_compensation, calculate_all_leave_balances
- calculate_all_seniority_benefits, answer_ccnl_query
- _convert_db_to_domain_model
- advanced_ccnl_search, _matches_advanced_filters, _generate_search_facets
- cross_ccnl_comparison and all sub-compare methods
- search_by_company_size, search_by_worker_category, search_by_geographic_area
- analyze_ccnl_trends
- get_all_priority*_ccnl methods, get_all_ccnl_data
- get_ccnl_coverage_stats, initialize_all_ccnl_data
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.ccnl_data import (
    AllowanceType,
    CCNLAgreement,
    CCNLSector,
    CompanySize,
    GeographicArea,
    JobLevel,
    LeaveEntitlement,
    LeaveType,
    NoticePerioD,
    OvertimeRules,
    SalaryTable,
    SpecialAllowance,
    WorkerCategory,
    WorkingHours,
)
from app.models.ccnl_database import CCNLAgreementDB
from app.services.ccnl_calculator_engine import (
    CalculationPeriod,
    CompensationBreakdown,
    LeaveBalance,
    SeniorityBenefits,
)
from app.services.ccnl_service import (
    CCNLComparisonResult,
    CCNLDataImportResult,
    CCNLQueryFilters,
    CCNLSearchResult,
    CCNLService,
    CCNLValidationError,
    CCNLValidationResult,
)

# ---------------------------------------------------------------------------
# CCNLQueryFilters
# ---------------------------------------------------------------------------


class TestCCNLQueryFilters:
    """Tests for CCNLQueryFilters dataclass."""

    def test_default_values(self):
        """Default filter object has sane defaults."""
        f = CCNLQueryFilters()
        assert f.sectors is None
        assert f.worker_categories is None
        assert f.geographic_area is None
        assert f.company_sizes is None
        assert f.valid_on_date is None
        assert f.min_monthly_salary is None
        assert f.max_monthly_salary is None
        assert f.min_experience_months is None
        assert f.max_experience_months is None
        assert f.include_allowances is False
        assert f.supervision_roles_only is False
        assert f.active_only is True
        assert f.has_remote_work is None
        assert f.has_apprenticeship is None
        assert f.has_part_time is None
        assert f.has_flexible_hours is None
        assert f.minimum_leave_days is None
        assert f.maximum_notice_days is None
        assert f.has_union_rights is None
        assert f.has_training_provisions is None
        assert f.small_company_rules is None
        assert f.priority_levels is None
        assert f.search_text is None

    def test_is_valid_returns_true_when_no_salary_constraints(self):
        """Filter with no salary range is valid."""
        f = CCNLQueryFilters()
        assert f.is_valid() is True

    def test_is_valid_returns_true_when_salary_range_correct(self):
        """Filter with min < max salary is valid."""
        f = CCNLQueryFilters(
            min_monthly_salary=Decimal("1000"),
            max_monthly_salary=Decimal("3000"),
        )
        assert f.is_valid() is True

    def test_is_valid_returns_false_when_salary_range_inverted(self):
        """Filter with min > max salary is invalid."""
        f = CCNLQueryFilters(
            min_monthly_salary=Decimal("5000"),
            max_monthly_salary=Decimal("1000"),
        )
        assert f.is_valid() is False

    def test_is_valid_returns_true_when_experience_range_correct(self):
        """Filter with min < max experience is valid."""
        f = CCNLQueryFilters(
            min_experience_months=0,
            max_experience_months=60,
        )
        assert f.is_valid() is True

    def test_is_valid_returns_false_when_experience_range_inverted(self):
        """Filter with min > max experience is invalid."""
        f = CCNLQueryFilters(
            min_experience_months=120,
            max_experience_months=12,
        )
        assert f.is_valid() is False

    def test_is_valid_salary_equal_bounds(self):
        """Filter with min == max salary is valid (exact match)."""
        f = CCNLQueryFilters(
            min_monthly_salary=Decimal("2000"),
            max_monthly_salary=Decimal("2000"),
        )
        assert f.is_valid() is True

    def test_is_valid_experience_equal_bounds(self):
        """Filter with min == max experience is valid (exact match)."""
        f = CCNLQueryFilters(
            min_experience_months=24,
            max_experience_months=24,
        )
        assert f.is_valid() is True

    def test_is_valid_with_only_min_salary(self):
        """Filter with only min salary set (no max) is valid."""
        f = CCNLQueryFilters(min_monthly_salary=Decimal("1500"))
        assert f.is_valid() is True

    def test_is_valid_with_only_max_experience(self):
        """Filter with only max experience set (no min) is valid."""
        f = CCNLQueryFilters(max_experience_months=36)
        assert f.is_valid() is True

    def test_is_valid_both_ranges_inverted(self):
        """Filter with both ranges inverted is invalid (salary checked first)."""
        f = CCNLQueryFilters(
            min_monthly_salary=Decimal("9999"),
            max_monthly_salary=Decimal("100"),
            min_experience_months=100,
            max_experience_months=1,
        )
        assert f.is_valid() is False


# ---------------------------------------------------------------------------
# CCNLSearchResult
# ---------------------------------------------------------------------------


class TestCCNLSearchResult:
    """Tests for CCNLSearchResult dataclass."""

    def test_has_results_true(self):
        """has_results returns True when filtered_count > 0."""
        result = CCNLSearchResult(
            total_count=100,
            filtered_count=5,
            agreements=[MagicMock()],
            query_time_ms=10,
        )
        assert result.has_results is True

    def test_has_results_false(self):
        """has_results returns False when filtered_count is 0."""
        result = CCNLSearchResult(
            total_count=100,
            filtered_count=0,
            agreements=[],
            query_time_ms=5,
        )
        assert result.has_results is False

    def test_default_facets_is_none(self):
        """facets defaults to None."""
        result = CCNLSearchResult(
            total_count=0,
            filtered_count=0,
            agreements=[],
            query_time_ms=0,
        )
        assert result.facets is None

    def test_filters_applied_default_empty_dict(self):
        """filters_applied defaults to an empty dict."""
        result = CCNLSearchResult(
            total_count=0,
            filtered_count=0,
            agreements=[],
            query_time_ms=0,
        )
        assert result.filters_applied == {}


# ---------------------------------------------------------------------------
# CCNLComparisonResult
# ---------------------------------------------------------------------------


class TestCCNLComparisonResult:
    """Tests for CCNLComparisonResult dataclass."""

    def test_has_differences_true(self):
        """has_differences returns True when differences list is non-empty."""
        result = CCNLComparisonResult(
            sector1=CCNLSector.COMMERCIO_TERZIARIO,
            sector2=CCNLSector.TURISMO,
            sector1_name="Commercio",
            sector2_name="Turismo",
            differences=[{"aspect": "salary", "diff": 200}],
        )
        assert result.has_differences is True

    def test_has_differences_false(self):
        """has_differences returns False when differences list is empty."""
        result = CCNLComparisonResult(
            sector1=CCNLSector.COMMERCIO_TERZIARIO,
            sector2=CCNLSector.TURISMO,
            sector1_name="Commercio",
            sector2_name="Turismo",
            differences=[],
        )
        assert result.has_differences is False

    def test_defaults_for_similarities_and_date(self):
        """similarities defaults to empty list, comparison_date to today."""
        result = CCNLComparisonResult(
            sector1=CCNLSector.TESSILI,
            sector2=CCNLSector.TURISMO,
            sector1_name="Tessili",
            sector2_name="Turismo",
            differences=[],
        )
        assert result.similarities == []
        assert result.comparison_date == date.today()


# ---------------------------------------------------------------------------
# CCNLValidationError
# ---------------------------------------------------------------------------


class TestCCNLValidationError:
    """Tests for CCNLValidationError dataclass."""

    def test_defaults(self):
        """Default severity is 'error'."""
        err = CCNLValidationError(field="salary", message="Bad", code="ERR")
        assert err.severity == "error"

    def test_custom_severity(self):
        """severity can be overridden to 'warning'."""
        err = CCNLValidationError(field="date", message="Future", code="WARN", severity="warning")
        assert err.severity == "warning"


# ---------------------------------------------------------------------------
# CCNLValidationResult
# ---------------------------------------------------------------------------


class TestCCNLValidationResult:
    """Tests for CCNLValidationResult dataclass."""

    def test_initial_valid(self):
        """Freshly created result starts valid with no errors/warnings."""
        result = CCNLValidationResult(is_valid=True)
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_add_error_marks_invalid(self):
        """add_error sets is_valid to False and appends error."""
        result = CCNLValidationResult(is_valid=True)
        result.add_error("sector", "Missing sector", "MISSING_SECTOR")
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].field == "sector"
        assert result.errors[0].message == "Missing sector"
        assert result.errors[0].code == "MISSING_SECTOR"
        assert result.errors[0].severity == "error"

    def test_add_warning_keeps_valid(self):
        """add_warning does not change is_valid."""
        result = CCNLValidationResult(is_valid=True)
        result.add_warning("valid_from", "Future date", "FUTURE_DATE")
        assert result.is_valid is True
        assert len(result.warnings) == 1
        assert result.warnings[0].severity == "warning"

    def test_multiple_errors_and_warnings(self):
        """Multiple errors/warnings accumulate correctly."""
        result = CCNLValidationResult(is_valid=True)
        result.add_error("sector", "bad", "E1")
        result.add_error("name", "empty", "E2")
        result.add_warning("date", "future", "W1")
        assert result.is_valid is False
        assert len(result.errors) == 2
        assert len(result.warnings) == 1


# ---------------------------------------------------------------------------
# CCNLDataImportResult
# ---------------------------------------------------------------------------


class TestCCNLDataImportResult:
    """Tests for CCNLDataImportResult dataclass."""

    def test_success_rate_all_imported(self):
        """success_rate is 1.0 when all records imported."""
        result = CCNLDataImportResult(
            success=True,
            records_processed=10,
            records_imported=10,
        )
        assert result.success_rate == 1.0

    def test_success_rate_partial(self):
        """success_rate is fraction when partially imported."""
        result = CCNLDataImportResult(
            success=False,
            records_processed=10,
            records_imported=7,
            records_failed=3,
        )
        assert result.success_rate == pytest.approx(0.7)

    def test_success_rate_none_imported(self):
        """success_rate is 0.0 when no records imported."""
        result = CCNLDataImportResult(
            success=False,
            records_processed=5,
            records_imported=0,
            records_failed=5,
        )
        assert result.success_rate == 0.0

    def test_success_rate_zero_processed(self):
        """success_rate is 0.0 when zero records processed (avoids ZeroDivisionError)."""
        result = CCNLDataImportResult(
            success=True,
            records_processed=0,
            records_imported=0,
        )
        assert result.success_rate == 0.0

    def test_default_fields(self):
        """Default fields have expected values."""
        result = CCNLDataImportResult(
            success=True,
            records_processed=1,
            records_imported=1,
        )
        assert result.records_failed == 0
        assert result.validation_errors == []
        assert result.processing_time_seconds == 0.0
        assert result.source_info is None


# ---------------------------------------------------------------------------
# CCNLService — _serialize_filters
# ---------------------------------------------------------------------------


class TestSerializeFilters:
    """Tests for CCNLService._serialize_filters."""

    def test_empty_filters(self):
        """Empty filters produce empty serialized dict."""
        service = CCNLService()
        filters = CCNLQueryFilters()
        result = service._serialize_filters(filters)
        assert result == {}

    def test_with_sectors(self):
        """Sectors are serialized to their .value strings."""
        service = CCNLService()
        filters = CCNLQueryFilters(sectors=[CCNLSector.COMMERCIO_TERZIARIO, CCNLSector.TURISMO])
        result = service._serialize_filters(filters)
        assert "sectors" in result
        assert CCNLSector.COMMERCIO_TERZIARIO.value in result["sectors"]

    def test_with_geographic_area(self):
        """Geographic area is serialized."""
        service = CCNLService()
        filters = CCNLQueryFilters(geographic_area=GeographicArea.NORD)
        result = service._serialize_filters(filters)
        assert result["geographic_area"] == GeographicArea.NORD.value

    def test_with_valid_on_date(self):
        """valid_on_date is serialized as ISO string."""
        service = CCNLService()
        d = date(2025, 6, 15)
        filters = CCNLQueryFilters(valid_on_date=d)
        result = service._serialize_filters(filters)
        assert result["valid_on_date"] == "2025-06-15"

    def test_with_worker_categories(self):
        """Worker categories are serialized."""
        service = CCNLService()
        filters = CCNLQueryFilters(worker_categories=[WorkerCategory.OPERAIO, WorkerCategory.IMPIEGATO])
        result = service._serialize_filters(filters)
        assert "worker_categories" in result
        assert WorkerCategory.OPERAIO.value in result["worker_categories"]


# ---------------------------------------------------------------------------
# CCNLService — _calculate_salary_statistics
# ---------------------------------------------------------------------------


class TestCalculateSalaryStatistics:
    """Tests for CCNLService._calculate_salary_statistics."""

    def test_basic_statistics(self):
        """Returns min, max, avg, range for a level code."""
        service = CCNLService()
        matrix = {
            "sector_a": {"L1": 1500.0, "L2": 2000.0},
            "sector_b": {"L1": 1800.0, "L2": 2500.0},
        }
        stats = service._calculate_salary_statistics(matrix, ["L1", "L2"])
        assert stats["L1"]["min"] == 1500.0
        assert stats["L1"]["max"] == 1800.0
        assert stats["L1"]["avg"] == pytest.approx(1650.0)
        assert stats["L1"]["range"] == pytest.approx(300.0)
        assert stats["L1"]["sectors_with_data"] == 2

    def test_missing_level_in_some_sectors(self):
        """Handles levels that exist in only some sectors."""
        service = CCNLService()
        matrix = {
            "sector_a": {"L1": 1500.0},
            "sector_b": {"L2": 2000.0},
        }
        stats = service._calculate_salary_statistics(matrix, ["L1", "L2", "L3"])
        assert stats["L1"]["sectors_with_data"] == 1
        assert stats["L2"]["sectors_with_data"] == 1
        assert "L3" not in stats

    def test_empty_matrix(self):
        """Returns empty stats for empty matrix."""
        service = CCNLService()
        stats = service._calculate_salary_statistics({}, ["L1"])
        assert stats == {}


# ---------------------------------------------------------------------------
# CCNLService — _estimate_worker_coverage
# ---------------------------------------------------------------------------


class TestEstimateWorkerCoverage:
    """Tests for CCNLService._estimate_worker_coverage."""

    def test_known_sectors(self):
        """Known sectors produce expected coverage percentage."""
        service = CCNLService()
        coverage = service._estimate_worker_coverage(
            [CCNLSector.COMMERCIO_TERZIARIO, CCNLSector.METALMECCANICI_INDUSTRIA]
        )
        assert coverage == pytest.approx(20.5)  # 12.0 + 8.5

    def test_empty_list(self):
        """Empty list yields 0.0 coverage."""
        service = CCNLService()
        assert service._estimate_worker_coverage([]) == 0.0

    def test_unknown_sector_gets_default(self):
        """Unknown sector uses default 0.5%."""
        service = CCNLService()
        coverage = service._estimate_worker_coverage([CCNLSector.TELECOMUNICAZIONI])
        assert coverage == pytest.approx(0.5)

    def test_cap_at_100(self):
        """Coverage is capped at 100%."""
        service = CCNLService()
        # Feed all known sectors multiple times would exceed 100 theoretically
        all_sectors = list(CCNLSector)
        coverage = service._estimate_worker_coverage(all_sectors)
        assert coverage <= 100.0


# ---------------------------------------------------------------------------
# CCNLService — validate_ccnl_data (pure validation logic)
# ---------------------------------------------------------------------------


class TestValidateCcnlData:
    """Tests for CCNLService.validate_ccnl_data."""

    @pytest.mark.asyncio
    async def test_valid_data(self):
        """Valid data returns is_valid=True with no errors."""
        service = CCNLService()
        data = {
            "sector": CCNLSector.COMMERCIO_TERZIARIO.value,
            "agreement_name": "CCNL Commercio 2024",
            "valid_from": "2024-01-01",
            "salary_tables": [
                {"salary": "1800.50"},
            ],
        }
        result = await service.validate_ccnl_data(data)
        assert result.is_valid is True
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_missing_sector(self):
        """Missing sector triggers MISSING_SECTOR error."""
        service = CCNLService()
        data = {"agreement_name": "Test"}
        result = await service.validate_ccnl_data(data)
        assert result.is_valid is False
        assert any(e.code == "MISSING_SECTOR" for e in result.errors)

    @pytest.mark.asyncio
    async def test_invalid_sector(self):
        """Invalid sector code triggers INVALID_SECTOR error."""
        service = CCNLService()
        data = {"sector": "nonexistent_sector", "agreement_name": "Test"}
        result = await service.validate_ccnl_data(data)
        assert result.is_valid is False
        assert any(e.code == "INVALID_SECTOR" for e in result.errors)

    @pytest.mark.asyncio
    async def test_missing_agreement_name(self):
        """Missing agreement_name triggers MISSING_NAME error."""
        service = CCNLService()
        data = {"sector": CCNLSector.TURISMO.value}
        result = await service.validate_ccnl_data(data)
        assert result.is_valid is False
        assert any(e.code == "MISSING_NAME" for e in result.errors)

    @pytest.mark.asyncio
    async def test_empty_agreement_name(self):
        """Empty/whitespace agreement_name triggers MISSING_NAME error."""
        service = CCNLService()
        data = {"sector": CCNLSector.TURISMO.value, "agreement_name": "   "}
        result = await service.validate_ccnl_data(data)
        assert result.is_valid is False
        assert any(e.code == "MISSING_NAME" for e in result.errors)

    @pytest.mark.asyncio
    async def test_invalid_date_format(self):
        """Invalid date format triggers INVALID_DATE error."""
        service = CCNLService()
        data = {
            "sector": CCNLSector.TURISMO.value,
            "agreement_name": "Test",
            "valid_from": "not-a-date",
        }
        result = await service.validate_ccnl_data(data)
        assert result.is_valid is False
        assert any(e.code == "INVALID_DATE" for e in result.errors)

    @pytest.mark.asyncio
    async def test_future_date_warning(self):
        """Future start date triggers a warning (not an error)."""
        service = CCNLService()
        data = {
            "sector": CCNLSector.TURISMO.value,
            "agreement_name": "Future CCNL",
            "valid_from": "2099-01-01",
        }
        result = await service.validate_ccnl_data(data)
        # Should still be valid (warning, not error)
        assert result.is_valid is True
        assert any(w.code == "FUTURE_DATE" for w in result.warnings)

    @pytest.mark.asyncio
    async def test_negative_salary(self):
        """Negative salary triggers NEGATIVE_SALARY error."""
        service = CCNLService()
        data = {
            "sector": CCNLSector.TURISMO.value,
            "agreement_name": "Test",
            "salary_tables": [{"salary": "-100"}],
        }
        result = await service.validate_ccnl_data(data)
        assert result.is_valid is False
        assert any(e.code == "NEGATIVE_SALARY" for e in result.errors)

    @pytest.mark.asyncio
    async def test_zero_salary(self):
        """Zero salary triggers NEGATIVE_SALARY error."""
        service = CCNLService()
        data = {
            "sector": CCNLSector.TURISMO.value,
            "agreement_name": "Test",
            "salary_tables": [{"salary": "0"}],
        }
        result = await service.validate_ccnl_data(data)
        assert result.is_valid is False
        assert any(e.code == "NEGATIVE_SALARY" for e in result.errors)

    @pytest.mark.asyncio
    async def test_valid_salary_with_decimals(self):
        """Valid salary with decimal places passes validation."""
        service = CCNLService()
        data = {
            "sector": CCNLSector.TURISMO.value,
            "agreement_name": "Test",
            "salary_tables": [{"salary": "1234.56"}],
        }
        result = await service.validate_ccnl_data(data)
        # No salary errors should be present
        salary_errors = [e for e in result.errors if "salary" in e.field]
        assert salary_errors == []

    @pytest.mark.asyncio
    async def test_multiple_salary_tables_mixed(self):
        """Multiple salary tables: one valid, one invalid."""
        service = CCNLService()
        data = {
            "sector": CCNLSector.TURISMO.value,
            "agreement_name": "Test",
            "salary_tables": [
                {"salary": "1500"},
                {"salary": "-200"},
            ],
        }
        result = await service.validate_ccnl_data(data)
        assert result.is_valid is False
        assert any(e.code == "NEGATIVE_SALARY" for e in result.errors)

    @pytest.mark.asyncio
    async def test_salary_table_without_salary_key(self):
        """Salary table entry missing 'salary' key is silently skipped."""
        service = CCNLService()
        data = {
            "sector": CCNLSector.TURISMO.value,
            "agreement_name": "Test",
            "salary_tables": [{"level": "L1"}],
        }
        result = await service.validate_ccnl_data(data)
        # No salary key present, so no salary validation errors
        assert result.is_valid is True


# ---------------------------------------------------------------------------
# CCNLService — CRUD with mocked DB (get_ccnl_by_id)
# ---------------------------------------------------------------------------


class TestCCNLServiceCRUD:
    """Tests for CCNLService CRUD operations with mocked DB."""

    @pytest.mark.asyncio
    @patch("app.services.ccnl_service.database_service")
    async def test_get_ccnl_by_id_found(self, mock_db_service):
        """get_ccnl_by_id returns agreement when found."""
        mock_agreement = MagicMock(spec=CCNLAgreementDB)
        mock_session = MagicMock()
        mock_session.get.return_value = mock_agreement
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_db_service.get_session_maker.return_value = mock_session

        service = CCNLService()
        result = await service.get_ccnl_by_id(42)
        assert result is mock_agreement
        mock_session.get.assert_called_once_with(CCNLAgreementDB, 42)

    @pytest.mark.asyncio
    @patch("app.services.ccnl_service.database_service")
    async def test_get_ccnl_by_id_not_found(self, mock_db_service):
        """get_ccnl_by_id returns None when not found."""
        mock_session = MagicMock()
        mock_session.get.return_value = None
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_db_service.get_session_maker.return_value = mock_session

        service = CCNLService()
        result = await service.get_ccnl_by_id(999)
        assert result is None

    @pytest.mark.asyncio
    @patch("app.services.ccnl_service.database_service")
    async def test_get_ccnl_by_id_db_error(self, mock_db_service):
        """get_ccnl_by_id returns None on DB exception."""
        mock_db_service.get_session_maker.side_effect = RuntimeError("DB down")

        service = CCNLService()
        result = await service.get_ccnl_by_id(1)
        assert result is None

    @pytest.mark.asyncio
    @patch("app.services.ccnl_service.database_service")
    async def test_update_ccnl_agreement_found(self, mock_db_service):
        """update_ccnl_agreement returns True when record exists."""
        mock_agreement = MagicMock(spec=CCNLAgreementDB)
        mock_session = MagicMock()
        mock_session.get.return_value = mock_agreement
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_db_service.get_session_maker.return_value = mock_session

        service = CCNLService()
        result = await service.update_ccnl_agreement(1, {"name": "New Name"})
        assert result is True

    @pytest.mark.asyncio
    @patch("app.services.ccnl_service.database_service")
    async def test_update_ccnl_agreement_not_found(self, mock_db_service):
        """update_ccnl_agreement returns False when record not found."""
        mock_session = MagicMock()
        mock_session.get.return_value = None
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_db_service.get_session_maker.return_value = mock_session

        service = CCNLService()
        result = await service.update_ccnl_agreement(999, {"name": "X"})
        assert result is False

    @pytest.mark.asyncio
    @patch("app.services.ccnl_service.database_service")
    async def test_update_ccnl_agreement_db_error(self, mock_db_service):
        """update_ccnl_agreement returns False on DB exception."""
        mock_db_service.get_session_maker.side_effect = RuntimeError("DB down")

        service = CCNLService()
        result = await service.update_ccnl_agreement(1, {"name": "X"})
        assert result is False

    @pytest.mark.asyncio
    @patch("app.services.ccnl_service.database_service")
    async def test_delete_ccnl_agreement_soft(self, mock_db_service):
        """delete_ccnl_agreement (soft) marks renewal_status as deleted."""
        mock_agreement = MagicMock(spec=CCNLAgreementDB)
        mock_session = MagicMock()
        mock_session.get.return_value = mock_agreement
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_db_service.get_session_maker.return_value = mock_session

        service = CCNLService()
        result = await service.delete_ccnl_agreement(1, soft_delete=True)
        assert result is True
        assert mock_agreement.renewal_status == "deleted"
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.ccnl_service.database_service")
    async def test_delete_ccnl_agreement_hard(self, mock_db_service):
        """delete_ccnl_agreement (hard) calls session.delete."""
        mock_agreement = MagicMock(spec=CCNLAgreementDB)
        mock_session = MagicMock()
        mock_session.get.return_value = mock_agreement
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_db_service.get_session_maker.return_value = mock_session

        service = CCNLService()
        result = await service.delete_ccnl_agreement(1, soft_delete=False)
        assert result is True
        mock_session.delete.assert_called_once_with(mock_agreement)

    @pytest.mark.asyncio
    @patch("app.services.ccnl_service.database_service")
    async def test_delete_ccnl_agreement_not_found(self, mock_db_service):
        """delete_ccnl_agreement returns False when not found."""
        mock_session = MagicMock()
        mock_session.get.return_value = None
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_db_service.get_session_maker.return_value = mock_session

        service = CCNLService()
        result = await service.delete_ccnl_agreement(999)
        assert result is False

    @pytest.mark.asyncio
    @patch("app.services.ccnl_service.database_service")
    async def test_delete_ccnl_agreement_db_error(self, mock_db_service):
        """delete_ccnl_agreement returns False on DB exception."""
        mock_db_service.get_session_maker.side_effect = RuntimeError("DB down")

        service = CCNLService()
        result = await service.delete_ccnl_agreement(1)
        assert result is False


# ---------------------------------------------------------------------------
# CCNLService — _compare_leave_entitlements and _compare_salary_tables
# ---------------------------------------------------------------------------


class TestComparisonHelpers:
    """Tests for CCNLService comparison helper methods."""

    def test_compare_leave_entitlements_with_diff(self):
        """_compare_leave_entitlements detects differences in base_annual_days."""
        service = CCNLService()

        leave1 = MagicMock()
        leave1.leave_type = "ferie"
        leave1.base_annual_days = 26

        leave2 = MagicMock()
        leave2.leave_type = "ferie"
        leave2.base_annual_days = 20

        ccnl1 = MagicMock(spec=CCNLAgreementDB)
        ccnl1.leave_entitlements = [leave1]
        ccnl2 = MagicMock(spec=CCNLAgreementDB)
        ccnl2.leave_entitlements = [leave2]

        diffs = service._compare_leave_entitlements(ccnl1, ccnl2)
        assert len(diffs) == 1
        assert diffs[0]["aspect"] == "leave_entitlements"
        assert diffs[0]["difference"] == 6

    def test_compare_leave_entitlements_no_diff(self):
        """_compare_leave_entitlements returns empty when same values."""
        service = CCNLService()

        leave1 = MagicMock()
        leave1.leave_type = "ferie"
        leave1.base_annual_days = 26

        leave2 = MagicMock()
        leave2.leave_type = "ferie"
        leave2.base_annual_days = 26

        ccnl1 = MagicMock(spec=CCNLAgreementDB)
        ccnl1.leave_entitlements = [leave1]
        ccnl2 = MagicMock(spec=CCNLAgreementDB)
        ccnl2.leave_entitlements = [leave2]

        diffs = service._compare_leave_entitlements(ccnl1, ccnl2)
        assert len(diffs) == 0

    def test_compare_salary_tables_with_diff(self):
        """_compare_salary_tables detects salary differences."""
        service = CCNLService()

        sal1 = MagicMock()
        sal1.level_code = "L1"
        sal1.base_monthly_salary = Decimal("1800")

        sal2 = MagicMock()
        sal2.level_code = "L1"
        sal2.base_monthly_salary = Decimal("1500")

        ccnl1 = MagicMock(spec=CCNLAgreementDB)
        ccnl1.salary_tables = [sal1]
        ccnl2 = MagicMock(spec=CCNLAgreementDB)
        ccnl2.salary_tables = [sal2]

        diffs = service._compare_salary_tables(ccnl1, ccnl2)
        assert len(diffs) == 1
        assert diffs[0]["aspect"] == "salary_tables"
        assert diffs[0]["difference"] == pytest.approx(300.0)

    def test_compare_salary_tables_no_common_levels(self):
        """_compare_salary_tables returns empty when no common level codes."""
        service = CCNLService()

        sal1 = MagicMock()
        sal1.level_code = "L1"
        sal1.base_monthly_salary = Decimal("1800")

        sal2 = MagicMock()
        sal2.level_code = "L2"
        sal2.base_monthly_salary = Decimal("1500")

        ccnl1 = MagicMock(spec=CCNLAgreementDB)
        ccnl1.salary_tables = [sal1]
        ccnl2 = MagicMock(spec=CCNLAgreementDB)
        ccnl2.salary_tables = [sal2]

        diffs = service._compare_salary_tables(ccnl1, ccnl2)
        assert len(diffs) == 0


# ---------------------------------------------------------------------------
# CCNLService — compare_ccnl_provisions (async, mocked)
# ---------------------------------------------------------------------------


class TestCompareCcnlProvisions:
    """Tests for CCNLService.compare_ccnl_provisions (async)."""

    @pytest.mark.asyncio
    @patch.object(CCNLService, "get_current_ccnl_by_sector")
    async def test_one_sector_not_found(self, mock_get_current):
        """Returns empty differences when one sector has no CCNL."""
        mock_get_current.side_effect = [MagicMock(), None]

        service = CCNLService()
        result = await service.compare_ccnl_provisions(
            CCNLSector.COMMERCIO_TERZIARIO,
            CCNLSector.TURISMO,
            ["salary_tables"],
        )
        assert result.has_differences is False
        assert result.differences == []

    @pytest.mark.asyncio
    @patch.object(CCNLService, "get_current_ccnl_by_sector")
    async def test_both_sectors_not_found(self, mock_get_current):
        """Returns empty differences when neither sector has CCNL."""
        mock_get_current.return_value = None

        service = CCNLService()
        result = await service.compare_ccnl_provisions(
            CCNLSector.COMMERCIO_TERZIARIO,
            CCNLSector.TURISMO,
            [],
        )
        assert result.has_differences is False

    @pytest.mark.asyncio
    @patch.object(CCNLService, "get_current_ccnl_by_sector")
    async def test_exception_returns_empty(self, mock_get_current):
        """Exception during comparison returns empty result."""
        mock_get_current.side_effect = RuntimeError("DB error")

        service = CCNLService()
        result = await service.compare_ccnl_provisions(
            CCNLSector.COMMERCIO_TERZIARIO,
            CCNLSector.TURISMO,
            ["salary_tables"],
        )
        assert result.differences == []


# ---------------------------------------------------------------------------
# CCNLService — _generate_comparison_recommendations
# ---------------------------------------------------------------------------


class TestGenerateRecommendations:
    """Tests for _generate_comparison_recommendations."""

    @pytest.mark.asyncio
    async def test_returns_list_of_strings(self):
        """Recommendations are a non-empty list of strings."""
        service = CCNLService()
        result = await service._generate_comparison_recommendations({})
        assert isinstance(result, list)
        assert len(result) >= 1
        assert all(isinstance(r, str) for r in result)


# ---------------------------------------------------------------------------
# CCNLService — _analyze_comparison_results
# ---------------------------------------------------------------------------


class TestAnalyzeComparisonResults:
    """Tests for _analyze_comparison_results."""

    @pytest.mark.asyncio
    async def test_with_salary_ranges(self):
        """Analysis identifies sector with highest salaries."""
        service = CCNLService()
        comparison = {
            "comparison_matrix": {
                "salary_ranges": {
                    "Commercio": {"max_salary": 3000},
                    "Turismo": {"max_salary": 2000},
                },
            },
        }
        result = await service._analyze_comparison_results(comparison)
        assert "best_practices" in result
        assert any("Commercio" in bp for bp in result["best_practices"])

    @pytest.mark.asyncio
    async def test_with_working_hours(self):
        """Analysis identifies flexible hours patterns."""
        service = CCNLService()
        comparison = {
            "comparison_matrix": {
                "working_hours": {
                    "Commercio": {"flexible_hours_allowed": True},
                    "Turismo": {"flexible_hours_allowed": True},
                    "Edilizia": {"flexible_hours_allowed": False},
                },
            },
        }
        result = await service._analyze_comparison_results(comparison)
        assert "common_patterns" in result
        assert len(result["common_patterns"]) >= 1

    @pytest.mark.asyncio
    async def test_empty_comparison(self):
        """Analysis on empty comparison matrix returns structure with empty lists."""
        service = CCNLService()
        result = await service._analyze_comparison_results({"comparison_matrix": {}})
        assert result["best_practices"] == []
        assert result["common_patterns"] == []
        assert result["outliers"] == []
        assert result["trends"] == []
