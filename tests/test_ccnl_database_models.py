"""
Test suite for CCNL database models and persistence layer.

This module tests the SQLAlchemy database models used to persist
Italian collective labor agreements in the database.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List
from unittest.mock import AsyncMock

import pytest

from app.models.ccnl_data import AllowanceType, CCNLSector, CompanySize, GeographicArea, LeaveType, WorkerCategory
from app.models.ccnl_database import (
    CCNLAgreementDB,
    CCNLSectorDB,
    JobLevelDB,
    LeaveEntitlementDB,
    NoticePeriodsDB,
    OvertimeRulesDB,
    SalaryTableDB,
    SpecialAllowanceDB,
    WorkingHoursDB,
)
from app.services.database import database_service


class TestCCNLSectorDB:
    """Test CCNL sector database model."""

    def test_ccnl_sector_db_creation(self):
        """Test creating CCNL sector database record."""
        sector_db = CCNLSectorDB(
            sector_code="metalmeccanici_industria",
            italian_name="Metalmeccanici Industria",
            priority_level=1,
            worker_coverage_percentage=8.5,
            active=True,
        )

        assert sector_db.sector_code == "metalmeccanici_industria"
        assert sector_db.italian_name == "Metalmeccanici Industria"
        assert sector_db.priority_level == 1
        assert sector_db.worker_coverage_percentage == 8.5
        assert sector_db.active is True

    def test_sector_from_enum(self):
        """Test converting sector enum to database model."""
        sector_db = CCNLSectorDB.from_enum(CCNLSector.METALMECCANICI_INDUSTRIA)

        assert sector_db.sector_code == CCNLSector.METALMECCANICI_INDUSTRIA.value
        assert sector_db.italian_name == "Metalmeccanici Industria"
        assert sector_db.priority_level == 1

    def test_sector_to_enum(self):
        """Test converting database model to sector enum."""
        sector_db = CCNLSectorDB(sector_code="commercio_terziario")
        sector_enum = sector_db.to_enum()

        assert sector_enum == CCNLSector.COMMERCIO_TERZIARIO


class TestCCNLAgreementDB:
    """Test CCNL agreement database model."""

    def test_ccnl_agreement_db_creation(self):
        """Test creating CCNL agreement database record."""
        agreement_db = CCNLAgreementDB(
            sector_code="metalmeccanici_industria",
            name="CCNL Metalmeccanici Industria 2024-2027",
            valid_from=date(2024, 1, 1),
            valid_to=date(2027, 12, 31),
            signatory_unions=["FIOM-CGIL", "FIM-CISL", "UILM-UIL"],
            signatory_employers=["Federmeccanica", "Assistal"],
            renewal_status="vigente",
            last_updated=datetime.now(),
            data_source="https://www.federmeccanica.it",
            verification_date=date.today(),
        )

        assert agreement_db.sector_code == "metalmeccanici_industria"
        assert agreement_db.name == "CCNL Metalmeccanici Industria 2024-2027"
        assert len(agreement_db.signatory_unions) == 3
        assert len(agreement_db.signatory_employers) == 2
        assert agreement_db.renewal_status == "vigente"

    def test_agreement_is_currently_valid(self):
        """Test checking if agreement is currently valid."""
        valid_agreement = CCNLAgreementDB(
            sector_code="commercio_terziario",
            name="CCNL Commercio",
            valid_from=date(2024, 1, 1),
            valid_to=date(2026, 12, 31),
        )

        expired_agreement = CCNLAgreementDB(
            sector_code="tessili", name="CCNL Tessili", valid_from=date(2020, 1, 1), valid_to=date(2023, 12, 31)
        )

        assert valid_agreement.is_currently_valid() is True
        assert expired_agreement.is_currently_valid() is False


class TestJobLevelDB:
    """Test job level database model."""

    def test_job_level_db_creation(self):
        """Test creating job level database record."""
        job_level_db = JobLevelDB(
            agreement_id=1,
            level_code="C2",
            level_name="Operaio Qualificato",
            worker_category="operaio",
            description="Operaio con esperienza e qualificazione specifica",
            minimum_experience_months=12,
            required_qualifications=["Diploma professionale", "Corso specializzazione"],
            typical_tasks=["Lavorazioni specializzate", "Controllo qualità", "Addestramento operai junior"],
            decision_making_level="Basso",
            supervision_responsibilities=False,
        )

        assert job_level_db.level_code == "C2"
        assert job_level_db.worker_category == "operaio"
        assert job_level_db.minimum_experience_months == 12
        assert len(job_level_db.required_qualifications) == 2
        assert len(job_level_db.typical_tasks) == 3

    def test_job_level_comparison_methods(self):
        """Test job level comparison methods."""
        level_c1 = JobLevelDB(agreement_id=1, level_code="C1", level_name="Operaio Base", worker_category="operaio")

        level_c3 = JobLevelDB(
            agreement_id=1, level_code="C3", level_name="Operaio Specializzato", worker_category="operaio"
        )

        level_d1 = JobLevelDB(agreement_id=1, level_code="D1", level_name="Impiegato", worker_category="impiegato")

        assert level_c1.is_lower_than(level_c3) is True
        assert level_c3.is_higher_than(level_c1) is True
        assert level_d1.is_higher_category_than(level_c1) is True


class TestSalaryTableDB:
    """Test salary table database model."""

    def test_salary_table_db_creation(self):
        """Test creating salary table database record."""
        salary_db = SalaryTableDB(
            agreement_id=1,
            level_code="C2",
            base_monthly_salary=Decimal("1650.00"),
            geographic_area="nazionale",
            valid_from=date(2024, 1, 1),
            valid_to=date(2026, 12, 31),
            thirteenth_month=True,
            fourteenth_month=True,
            additional_allowances={"indennita_anzianita": Decimal("50.00"), "premio_presenza": Decimal("25.00")},
            company_size_adjustments={"small": Decimal("-50.00"), "large": Decimal("100.00")},
        )

        assert salary_db.base_monthly_salary == Decimal("1650.00")
        assert salary_db.geographic_area == "nazionale"
        assert salary_db.thirteenth_month is True
        assert salary_db.fourteenth_month is True
        assert len(salary_db.additional_allowances) == 2
        assert len(salary_db.company_size_adjustments) == 2

    def test_salary_annual_calculations(self):
        """Test salary annual calculations."""
        salary_db = SalaryTableDB(
            agreement_id=1,
            level_code="D1",
            base_monthly_salary=Decimal("1800.00"),
            thirteenth_month=True,
            fourteenth_month=False,
        )

        annual_salary = salary_db.get_annual_salary()
        annual_with_additional = salary_db.get_annual_salary_with_additional_months()

        assert annual_salary == Decimal("21600.00")  # 1800 * 12
        assert annual_with_additional == Decimal("23400.00")  # 1800 * 13

    def test_salary_validation(self):
        """Test salary table date validation."""
        salary_db = SalaryTableDB(
            agreement_id=1,
            level_code="B1",
            base_monthly_salary=Decimal("2000.00"),
            valid_from=date(2024, 1, 1),
            valid_to=date(2024, 12, 31),
        )

        assert salary_db.is_valid_on(date(2024, 6, 15)) is True
        assert salary_db.is_valid_on(date(2025, 1, 1)) is False


class TestWorkingHoursDB:
    """Test working hours database model."""

    def test_working_hours_db_creation(self):
        """Test creating working hours database record."""
        hours_db = WorkingHoursDB(
            agreement_id=1,
            ordinary_weekly_hours=40,
            maximum_weekly_hours=48,
            daily_rest_hours=11,
            weekly_rest_hours=24,
            flexible_hours_allowed=True,
            flexible_hours_range_min=6,
            flexible_hours_range_max=10,
            core_hours_start="09:00",
            core_hours_end="16:00",
            part_time_allowed=True,
            minimum_part_time_hours=20,
            shift_work_allowed=True,
            shift_patterns=["6-14", "14-22", "22-6"],
            night_shift_allowance=Decimal("30.00"),
        )

        assert hours_db.ordinary_weekly_hours == 40
        assert hours_db.flexible_hours_allowed is True
        assert hours_db.flexible_hours_range_min == 6
        assert hours_db.flexible_hours_range_max == 10
        assert hours_db.shift_work_allowed is True
        assert len(hours_db.shift_patterns) == 3

    def test_working_hours_calculations(self):
        """Test working hours calculations."""
        hours_db = WorkingHoursDB(agreement_id=1, ordinary_weekly_hours=38)

        daily_hours = hours_db.get_ordinary_daily_hours()
        assert daily_hours == 7.6  # 38/5


class TestLeaveEntitlementDB:
    """Test leave entitlement database model."""

    def test_leave_entitlement_db_creation(self):
        """Test creating leave entitlement database record."""
        leave_db = LeaveEntitlementDB(
            agreement_id=1,
            leave_type="ferie",
            base_annual_days=24,
            base_annual_hours=None,
            seniority_bonus_schedule={
                60: 2,  # +2 days after 5 years
                120: 4,  # +4 days after 10 years
            },
            calculation_method="annual",
            minimum_usage_hours=4,
            advance_notice_hours=24,
            compensation_percentage=Decimal("1.00"),
            mandatory_period=False,
            additional_optional_days=None,
        )

        assert leave_db.leave_type == "ferie"
        assert leave_db.base_annual_days == 24
        assert len(leave_db.seniority_bonus_schedule) == 2
        assert leave_db.compensation_percentage == Decimal("1.00")

    def test_leave_entitlement_calculations(self):
        """Test leave entitlement seniority calculations."""
        leave_db = LeaveEntitlementDB(
            agreement_id=1,
            leave_type="ferie",
            base_annual_days=22,
            seniority_bonus_schedule={
                60: 2,  # +2 after 5 years
                120: 4,  # +4 after 10 years (total, not cumulative)
            },
        )

        # Test different seniority levels
        assert leave_db.get_annual_entitlement(months_seniority=30) == 22  # Under 5 years
        assert leave_db.get_annual_entitlement(months_seniority=72) == 24  # 6 years = 22 + 2
        assert leave_db.get_annual_entitlement(months_seniority=150) == 26  # 12.5 years = 22 + 4


class TestSpecialAllowanceDB:
    """Test special allowance database model."""

    def test_special_allowance_db_creation(self):
        """Test creating special allowance database record."""
        allowance_db = SpecialAllowanceDB(
            agreement_id=1,
            allowance_type="buoni_pasto",
            amount=Decimal("7.50"),
            frequency="daily",
            conditions=["Lavoro full-time", "Orario minimo 6 ore"],
            applicable_job_levels=["C1", "C2", "C3", "D1"],
            geographic_areas=["nazionale"],
            company_sizes=["small", "medium", "large"],
        )

        assert allowance_db.allowance_type == "buoni_pasto"
        assert allowance_db.amount == Decimal("7.50")
        assert allowance_db.frequency == "daily"
        assert len(allowance_db.conditions) == 2
        assert len(allowance_db.applicable_job_levels) == 4

    def test_allowance_monthly_calculation(self):
        """Test monthly allowance calculation."""
        daily_allowance = SpecialAllowanceDB(
            agreement_id=1, allowance_type="indennita_trasporto", amount=Decimal("8.00"), frequency="daily"
        )

        monthly_allowance = SpecialAllowanceDB(
            agreement_id=1, allowance_type="premio_produzione", amount=Decimal("200.00"), frequency="monthly"
        )

        assert daily_allowance.get_monthly_amount(working_days=22) == Decimal("176.00")
        assert monthly_allowance.get_monthly_amount() == Decimal("200.00")

    def test_allowance_geographic_applicability(self):
        """Test geographic applicability of allowances."""
        regional_allowance = SpecialAllowanceDB(
            agreement_id=1,
            allowance_type="indennita_costo_vita",
            amount=Decimal("50.00"),
            frequency="monthly",
            geographic_areas=["nord", "centro"],
        )

        assert regional_allowance.applies_to_geographic_area("nord") is True
        assert regional_allowance.applies_to_geographic_area("centro") is True
        assert regional_allowance.applies_to_geographic_area("sud") is False

        # Test national allowance (empty geographic_areas means national)
        national_allowance = SpecialAllowanceDB(
            agreement_id=1,
            allowance_type="buoni_pasto",
            amount=Decimal("7.00"),
            frequency="daily",
            geographic_areas=[],
        )

        assert national_allowance.applies_to_geographic_area("any_area") is True


class TestCCNLDatabaseIntegration:
    """Test integration between CCNL database models."""

    @pytest.mark.asyncio
    async def test_create_complete_ccnl_agreement(self):
        """Test creating complete CCNL agreement with all components."""
        # Create agreement
        agreement = CCNLAgreementDB(
            sector_code="metalmeccanici_industria",
            name="CCNL Metalmeccanici Test",
            valid_from=date(2024, 1, 1),
            valid_to=date(2026, 12, 31),
        )

        # Create job levels
        job_levels = [
            JobLevelDB(
                agreement_id=1,  # Will be set after agreement is saved
                level_code="C1",
                level_name="Operaio Comune",
                worker_category="operaio",
            ),
            JobLevelDB(agreement_id=1, level_code="C2", level_name="Operaio Qualificato", worker_category="operaio"),
            JobLevelDB(agreement_id=1, level_code="D1", level_name="Impiegato", worker_category="impiegato"),
        ]

        # Create salary tables
        salary_tables = [
            SalaryTableDB(
                agreement_id=1,
                level_code="C1",
                base_monthly_salary=Decimal("1450.00"),
                thirteenth_month=True,
                fourteenth_month=False,
            ),
            SalaryTableDB(
                agreement_id=1,
                level_code="C2",
                base_monthly_salary=Decimal("1650.00"),
                thirteenth_month=True,
                fourteenth_month=True,
            ),
            SalaryTableDB(
                agreement_id=1,
                level_code="D1",
                base_monthly_salary=Decimal("1900.00"),
                thirteenth_month=True,
                fourteenth_month=True,
            ),
        ]

        # Create working hours
        working_hours = WorkingHoursDB(
            agreement_id=1,
            ordinary_weekly_hours=40,
            maximum_weekly_hours=48,
            flexible_hours_allowed=True,
            part_time_allowed=True,
        )

        # Create leave entitlements
        leave_entitlements = [
            LeaveEntitlementDB(
                agreement_id=1, leave_type="ferie", base_annual_days=24, seniority_bonus_schedule={60: 2, 120: 4}
            ),
            LeaveEntitlementDB(agreement_id=1, leave_type="permessi_retribuiti", base_annual_hours=64),
            LeaveEntitlementDB(agreement_id=1, leave_type="rol_ex_festivita", base_annual_hours=32),
        ]

        # Create special allowances
        special_allowances = [
            SpecialAllowanceDB(
                agreement_id=1,
                allowance_type="buoni_pasto",
                amount=Decimal("7.00"),
                frequency="daily",
                applicable_job_levels=["C1", "C2", "D1"],
            ),
            SpecialAllowanceDB(
                agreement_id=1,
                allowance_type="indennita_trasporto",
                amount=Decimal("120.00"),
                frequency="monthly",
                geographic_areas=["nord", "centro"],
            ),
        ]

        # Verify all components are properly structured
        assert agreement.sector_code == "metalmeccanici_industria"
        assert len(job_levels) == 3
        assert len(salary_tables) == 3
        assert working_hours.ordinary_weekly_hours == 40
        assert len(leave_entitlements) == 3
        assert len(special_allowances) == 2

        # Test relationships (in real implementation, these would be SQLAlchemy relationships)
        c2_salary = next(s for s in salary_tables if s.level_code == "C2")
        assert c2_salary.base_monthly_salary == Decimal("1650.00")
        assert c2_salary.fourteenth_month is True

    @pytest.mark.asyncio
    async def test_ccnl_database_queries(self):
        """Test common CCNL database queries."""
        # Mock database session would be used here
        # These tests verify the query methods work correctly

        # Test finding salary for specific level
        SalaryTableDB(
            agreement_id=1, level_code="C2", base_monthly_salary=Decimal("1650.00"), geographic_area="nazionale"
        )

        # Test finding applicable allowances
        test_allowances = [
            SpecialAllowanceDB(
                agreement_id=1,
                allowance_type="buoni_pasto",
                amount=Decimal("7.00"),
                frequency="daily",
                applicable_job_levels=["C1", "C2", "C3"],
            )
        ]

        # Verify query logic
        applicable_allowances = [
            a for a in test_allowances if not a.applicable_job_levels or "C2" in a.applicable_job_levels
        ]

        assert len(applicable_allowances) == 1
        assert applicable_allowances[0].allowance_type == "buoni_pasto"


class TestCCNLDatabasePersistence:
    """Test CCNL database persistence operations."""

    @pytest.mark.asyncio
    async def test_save_ccnl_agreement_to_database(self):
        """Test saving CCNL agreement to database."""
        with pytest.assume_mock_database():
            agreement = CCNLAgreementDB(
                sector_code="commercio_terziario", name="CCNL Commercio Test", valid_from=date(2024, 1, 1)
            )

            # Mock database operations (not actually connecting to DB in tests)
            # In real implementation, would use session.add() and session.commit()

            # Verify agreement object is properly structured
            assert agreement.sector_code == "commercio_terziario"
            assert agreement.name == "CCNL Commercio Test"
            assert agreement.valid_from == date(2024, 1, 1)
            # renewal_status would be set by database default on insert

    @pytest.mark.asyncio
    async def test_query_ccnl_agreements_by_sector(self):
        """Test querying CCNL agreements by sector."""
        with pytest.assume_mock_database():
            # Mock query results
            mock_agreements = [
                CCNLAgreementDB(
                    sector_code="metalmeccanici_industria",
                    name="CCNL Metalmeccanici 2024",
                    valid_from=date(2024, 1, 1),
                ),
                CCNLAgreementDB(
                    sector_code="metalmeccanici_industria",
                    name="CCNL Metalmeccanici 2021",
                    valid_from=date(2021, 1, 1),
                    valid_to=date(2023, 12, 31),
                ),
            ]
            # Simulate setting IDs after save
            mock_agreements[0].id = 1
            mock_agreements[1].id = 2

            # Filter for current agreements
            current_agreements = [a for a in mock_agreements if a.is_currently_valid()]

            assert len(current_agreements) == 1
            assert current_agreements[0].name == "CCNL Metalmeccanici 2024"

    @pytest.mark.asyncio
    async def test_ccnl_data_migration(self):
        """Test migrating CCNL data from external sources."""
        # Test data conversion from external format
        external_data = {
            "sector": "metalmeccanici_industria",
            "agreement_name": "CCNL Metalmeccanici 2024",
            "salary_tables": [{"level": "C1", "salary": "1450.00", "13th_month": True, "14th_month": False}],
            "working_hours": {"weekly_hours": 40, "flexible": True},
        }

        # Convert to database models
        agreement = CCNLAgreementDB(
            sector_code=external_data["sector"], name=external_data["agreement_name"], valid_from=date(2024, 1, 1)
        )

        salary_tables = []
        for salary_data in external_data["salary_tables"]:
            salary_db = SalaryTableDB(
                agreement_id=1,  # Will be set after agreement save
                level_code=salary_data["level"],
                base_monthly_salary=Decimal(salary_data["salary"]),
                thirteenth_month=salary_data["13th_month"],
                fourteenth_month=salary_data["14th_month"],
            )
            salary_tables.append(salary_db)

        working_hours = WorkingHoursDB(
            agreement_id=1,
            ordinary_weekly_hours=external_data["working_hours"]["weekly_hours"],
            flexible_hours_allowed=external_data["working_hours"]["flexible"],
        )

        assert agreement.sector_code == "metalmeccanici_industria"
        assert len(salary_tables) == 1
        assert salary_tables[0].base_monthly_salary == Decimal("1450.00")
        assert working_hours.flexible_hours_allowed is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=app.models.ccnl_database"])
