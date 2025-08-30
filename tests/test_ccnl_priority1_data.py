"""
Test suite for Priority 1 CCNL data structures with real Italian labor agreements.

This module tests the actual CCNL data for the 10 highest priority sectors,
ensuring data integrity and completeness for the most important Italian labor agreements.
"""

import pytest
from datetime import date
from decimal import Decimal
from typing import List, Dict, Any

from app.data.ccnl_priority1 import (
    get_metalmeccanici_industria_ccnl,
    get_commercio_terziario_ccnl,
    get_edilizia_industria_ccnl,
    get_pubblici_esercizi_ccnl,
    get_turismo_ccnl,
    get_trasporti_logistica_ccnl,
    get_chimici_farmaceutici_ccnl,
    get_tessili_ccnl,
    get_metalmeccanici_artigiani_ccnl,
    get_edilizia_artigianato_ccnl,
    get_all_priority1_ccnl_data,
    validate_ccnl_data_completeness
)
from app.models.ccnl_data import (
    CCNLAgreement,
    CCNLSector,
    WorkerCategory,
    JobLevel,
    SalaryTable,
    WorkingHours,
    LeaveEntitlement,
    NoticePerioD,
    SpecialAllowance,
    GeographicArea,
    LeaveType,
    AllowanceType
)


class TestMetalmeccaniciIndustriaCCNL:
    """Test Metalmeccanici Industria CCNL data - largest industrial sector."""
    
    def test_metalmeccanici_ccnl_structure(self):
        """Test basic structure of Metalmeccanici CCNL."""
        ccnl = get_metalmeccanici_industria_ccnl()
        
        assert isinstance(ccnl, CCNLAgreement)
        assert ccnl.sector == CCNLSector.METALMECCANICI_INDUSTRIA
        assert ccnl.name == "CCNL Metalmeccanici Industria 2024-2027"
        assert ccnl.valid_from == date(2024, 1, 1)
        assert ccnl.valid_to == date(2027, 12, 31)
        assert len(ccnl.signatory_unions) >= 3  # FIOM, FIM, UILM
        assert len(ccnl.signatory_employers) >= 2  # Federmeccanica, Assistal
    
    def test_metalmeccanici_job_levels(self):
        """Test job level structure for Metalmeccanici."""
        ccnl = get_metalmeccanici_industria_ccnl()
        
        # Should have complete job level structure
        assert len(ccnl.job_levels) >= 8  # Operai C1-C3, Impiegati D1-D3, Quadri Q1-Q2
        
        # Check operai levels
        operai_levels = [level for level in ccnl.job_levels if level.category == WorkerCategory.OPERAIO]
        assert len(operai_levels) >= 3
        assert any(level.level_code == "C1" for level in operai_levels)
        assert any(level.level_code == "C2" for level in operai_levels) 
        assert any(level.level_code == "C3" for level in operai_levels)
        
        # Check impiegati levels
        impiegati_levels = [level for level in ccnl.job_levels if level.category == WorkerCategory.IMPIEGATO]
        assert len(impiegati_levels) >= 3
        assert any(level.level_code == "D1" for level in impiegati_levels)
        assert any(level.level_code == "D2" for level in impiegati_levels)
        assert any(level.level_code == "D3" for level in impiegati_levels)
    
    def test_metalmeccanici_salary_tables(self):
        """Test salary table completeness for Metalmeccanici."""
        ccnl = get_metalmeccanici_industria_ccnl()
        
        assert len(ccnl.salary_tables) >= 6  # At least main job levels
        
        # Check C1 operaio salary
        c1_salary = next((s for s in ccnl.salary_tables if s.level_code == "C1"), None)
        assert c1_salary is not None
        assert c1_salary.base_monthly_salary >= Decimal('1450.00')
        assert c1_salary.thirteenth_month is True
        
        # Check C2 operaio salary  
        c2_salary = next((s for s in ccnl.salary_tables if s.level_code == "C2"), None)
        assert c2_salary is not None
        assert c2_salary.base_monthly_salary > c1_salary.base_monthly_salary
        assert c2_salary.fourteenth_month is True
        
        # Check D1 impiegato salary
        d1_salary = next((s for s in ccnl.salary_tables if s.level_code == "D1"), None)
        assert d1_salary is not None
        assert d1_salary.base_monthly_salary > c2_salary.base_monthly_salary
    
    def test_metalmeccanici_working_hours(self):
        """Test working hours configuration for Metalmeccanici."""
        ccnl = get_metalmeccanici_industria_ccnl()
        
        assert ccnl.working_hours is not None
        assert ccnl.working_hours.ordinary_weekly_hours == 40
        assert ccnl.working_hours.maximum_weekly_hours == 48
        assert ccnl.working_hours.flexible_hours_allowed is True
        assert ccnl.working_hours.shift_work_allowed is True
    
    def test_metalmeccanici_leave_entitlements(self):
        """Test leave entitlements for Metalmeccanici."""
        ccnl = get_metalmeccanici_industria_ccnl()
        
        # Should have ferie, permessi, ROL
        assert len(ccnl.leave_entitlements) >= 3
        
        # Check ferie (vacation)
        ferie = next((l for l in ccnl.leave_entitlements if l.leave_type == LeaveType.FERIE), None)
        assert ferie is not None
        assert ferie.base_annual_days >= 24
        assert len(ferie.seniority_bonus_schedule) > 0  # Seniority bonuses
        
        # Check permessi retribuiti
        permessi = next((l for l in ccnl.leave_entitlements if l.leave_type == LeaveType.PERMESSI_RETRIBUITI), None)
        assert permessi is not None
        assert permessi.base_annual_hours >= 64
    
    def test_metalmeccanici_notice_periods(self):
        """Test notice periods for Metalmeccanici."""
        ccnl = get_metalmeccanici_industria_ccnl()
        
        assert len(ccnl.notice_periods) >= 4  # Different categories and seniority levels
        
        # Check operai notice periods
        operai_notices = [n for n in ccnl.notice_periods if n.worker_category == WorkerCategory.OPERAIO]
        assert len(operai_notices) >= 2  # Different seniority levels
        
        # Check impiegati notice periods
        impiegati_notices = [n for n in ccnl.notice_periods if n.worker_category == WorkerCategory.IMPIEGATO]
        assert len(impiegati_notices) >= 2
    
    def test_metalmeccanici_allowances(self):
        """Test special allowances for Metalmeccanici."""
        ccnl = get_metalmeccanici_industria_ccnl()
        
        assert len(ccnl.special_allowances) >= 3
        
        # Check for buoni pasto
        buoni_pasto = next((a for a in ccnl.special_allowances 
                           if a.allowance_type == AllowanceType.BUONI_PASTO), None)
        assert buoni_pasto is not None
        assert buoni_pasto.amount >= Decimal('7.00')
        assert buoni_pasto.frequency == "daily"


class TestCommercioTerziarioCCNL:
    """Test Commercio e Terziario CCNL data - largest commercial sector."""
    
    def test_commercio_ccnl_structure(self):
        """Test basic structure of Commercio CCNL."""
        ccnl = get_commercio_terziario_ccnl()
        
        assert isinstance(ccnl, CCNLAgreement)
        assert ccnl.sector == CCNLSector.COMMERCIO_TERZIARIO
        assert ccnl.name == "CCNL Commercio e Terziario 2024-2027"
        assert ccnl.valid_from == date(2024, 1, 1)
        assert len(ccnl.signatory_unions) >= 3  # FILCAMS, FISASCAT, UILTuCS
        assert len(ccnl.signatory_employers) >= 1  # Confcommercio
    
    def test_commercio_job_levels_with_geographic_differences(self):
        """Test job levels with geographic salary differences."""
        ccnl = get_commercio_terziario_ccnl()
        
        assert len(ccnl.job_levels) >= 6
        
        # Check for geographic salary differences
        has_geographic_differences = any(
            s.geographic_area != GeographicArea.NAZIONALE 
            for s in ccnl.salary_tables
        )
        assert has_geographic_differences  # Commercio has North/South differences
    
    def test_commercio_working_hours_flexibility(self):
        """Test flexible working hours for Commercio."""
        ccnl = get_commercio_terziario_ccnl()
        
        assert ccnl.working_hours.ordinary_weekly_hours == 38  # Often 38 hours for commerce
        assert ccnl.working_hours.flexible_hours_allowed is True
        assert ccnl.working_hours.part_time_allowed is True


class TestEdiliziaIndustriaCCNL:
    """Test Edilizia Industria CCNL data - construction industry."""
    
    def test_edilizia_ccnl_with_risk_allowances(self):
        """Test Edilizia CCNL with construction-specific allowances."""
        ccnl = get_edilizia_industria_ccnl()
        
        assert ccnl.sector == CCNLSector.EDILIZIA_INDUSTRIA
        assert ccnl.name == "CCNL Edilizia Industria 2024-2027"
        
        # Should have risk allowances for construction work
        risk_allowances = [a for a in ccnl.special_allowances 
                          if a.allowance_type == AllowanceType.INDENNITA_RISCHIO]
        assert len(risk_allowances) >= 1
        
        # Check for transport allowances (common in construction)
        transport_allowances = [a for a in ccnl.special_allowances
                               if a.allowance_type == AllowanceType.INDENNITA_TRASPORTO]
        assert len(transport_allowances) >= 1


class TestPubbliciEserciziCCNL:
    """Test Pubblici Esercizi CCNL data - bars, restaurants, hotels."""
    
    def test_pubblici_esercizi_shift_work(self):
        """Test Pubblici Esercizi with shift and weekend work provisions."""
        ccnl = get_pubblici_esercizi_ccnl()
        
        assert ccnl.sector == CCNLSector.PUBBLICI_ESERCIZI
        assert ccnl.name == "CCNL Pubblici Esercizi 2024-2027"
        
        # Should support shift work and weekend work
        assert ccnl.working_hours.shift_work_allowed is True
        assert len(ccnl.working_hours.shift_patterns) >= 2
        
        # Should have weekend/holiday overtime rates
        assert ccnl.overtime_rules is not None
        assert ccnl.overtime_rules.weekend_rate >= Decimal('1.50')
        assert ccnl.overtime_rules.holiday_rate >= Decimal('2.00')


class TestTurismoCCNL:
    """Test Turismo CCNL data - tourism and hospitality."""
    
    def test_turismo_seasonal_provisions(self):
        """Test Turismo CCNL with seasonal work considerations."""
        ccnl = get_turismo_ccnl()
        
        assert ccnl.sector == CCNLSector.TURISMO
        assert ccnl.name == "CCNL Turismo 2024-2027"
        
        # Tourism often has part-time and flexible arrangements
        assert ccnl.working_hours.part_time_allowed is True
        assert ccnl.working_hours.flexible_hours_allowed is True


class TestTrasportiLogisticaCCNL:
    """Test Trasporti e Logistica CCNL data - transport and logistics."""
    
    def test_trasporti_driving_allowances(self):
        """Test Transport CCNL with driving and travel allowances."""
        ccnl = get_trasporti_logistica_ccnl()
        
        assert ccnl.sector == CCNLSector.TRASPORTI_LOGISTICA
        assert ccnl.name == "CCNL Trasporti e Logistica 2024-2027"
        
        # Should have transport-specific allowances
        trasferta_allowances = [a for a in ccnl.special_allowances
                               if a.allowance_type == AllowanceType.INDENNITA_TRASFERTA]
        assert len(trasferta_allowances) >= 1


class TestChimiciFarmaceuticiCCNL:
    """Test Chimici e Farmaceutici CCNL data - chemicals and pharmaceuticals."""
    
    def test_chimici_specialized_allowances(self):
        """Test Chimici CCNL with specialized risk allowances."""
        ccnl = get_chimici_farmaceutici_ccnl()
        
        assert ccnl.sector == CCNLSector.CHIMICI_FARMACEUTICI
        assert ccnl.name == "CCNL Chimici e Farmaceutici 2024-2027"
        
        # Should have risk allowances for chemical work
        risk_allowances = [a for a in ccnl.special_allowances
                          if a.allowance_type == AllowanceType.INDENNITA_RISCHIO]
        assert len(risk_allowances) >= 1
        assert any(a.amount >= Decimal('50.00') for a in risk_allowances)


class TestTessiliCCNL:
    """Test Tessili CCNL data - textile industry."""
    
    def test_tessili_traditional_structure(self):
        """Test Tessili CCNL with traditional manufacturing structure."""
        ccnl = get_tessili_ccnl()
        
        assert ccnl.sector == CCNLSector.TESSILI
        assert ccnl.name == "CCNL Tessili 2024-2027"
        
        # Traditional manufacturing hours
        assert ccnl.working_hours.ordinary_weekly_hours == 40
        assert ccnl.working_hours.shift_work_allowed is True


class TestMetalmeccaniciArtigianiCCNL:
    """Test Metalmeccanici Artigiani CCNL data - artisan metalworkers."""
    
    def test_artigiani_smaller_scale_provisions(self):
        """Test Artigiani CCNL adapted for smaller businesses."""
        ccnl = get_metalmeccanici_artigiani_ccnl()
        
        assert ccnl.sector == CCNLSector.METALMECCANICI_ARTIGIANI
        assert ccnl.name == "CCNL Metalmeccanici Artigiani 2024-2027"
        
        # May have different salary scales for smaller businesses
        assert len(ccnl.salary_tables) >= 4


class TestEdiliziaArtigianatoCCNL:
    """Test Edilizia Artigianato CCNL data - artisan construction."""
    
    def test_edilizia_artigianato_flexibility(self):
        """Test Edilizia Artigianato with small business flexibility."""
        ccnl = get_edilizia_artigianato_ccnl()
        
        assert ccnl.sector == CCNLSector.EDILIZIA_ARTIGIANATO
        assert ccnl.name == "CCNL Edilizia Artigianato 2024-2027"
        
        # Should allow flexible arrangements for small construction companies
        assert ccnl.working_hours.flexible_hours_allowed is True


class TestPriority1CCNLDataIntegration:
    """Test integration and completeness of all Priority 1 CCNL data."""
    
    def test_all_priority1_ccnl_available(self):
        """Test that all 10 Priority 1 CCNLs are available."""
        all_ccnl = get_all_priority1_ccnl_data()
        
        assert len(all_ccnl) == 10
        
        # Check all expected sectors are present
        sectors = {ccnl.sector for ccnl in all_ccnl}
        expected_sectors = {
            CCNLSector.METALMECCANICI_INDUSTRIA,
            CCNLSector.METALMECCANICI_ARTIGIANI,
            CCNLSector.COMMERCIO_TERZIARIO,
            CCNLSector.EDILIZIA_INDUSTRIA,
            CCNLSector.EDILIZIA_ARTIGIANATO,
            CCNLSector.PUBBLICI_ESERCIZI,
            CCNLSector.TURISMO,
            CCNLSector.TRASPORTI_LOGISTICA,
            CCNLSector.CHIMICI_FARMACEUTICI,
            CCNLSector.TESSILI
        }
        
        assert sectors == expected_sectors
    
    def test_ccnl_data_completeness_validation(self):
        """Test that all CCNL data meets completeness requirements."""
        validation_results = validate_ccnl_data_completeness()
        
        assert validation_results["overall_completeness"] >= 0.90  # 90% complete
        assert validation_results["sectors_with_complete_data"] >= 8  # At least 8 of 10
        assert len(validation_results["missing_components"]) <= 5  # Few missing pieces
    
    def test_salary_data_realism(self):
        """Test that salary data is realistic for Italian market."""
        all_ccnl = get_all_priority1_ccnl_data()
        
        all_salaries = []
        for ccnl in all_ccnl:
            for salary_table in ccnl.salary_tables:
                all_salaries.append(float(salary_table.base_monthly_salary))
        
        # Italian minimum wage considerations (no official minimum, but practical minimums)
        assert min(all_salaries) >= 1200.00  # Reasonable minimum for 2024
        assert max(all_salaries) <= 5000.00  # Reasonable maximum for basic levels
        assert sum(all_salaries) / len(all_salaries) >= 1500.00  # Average should be reasonable
    
    def test_geographic_salary_differences(self):
        """Test that geographic salary differences are properly represented."""
        all_ccnl = get_all_priority1_ccnl_data()
        
        # Count how many CCNLs have geographic differentiation
        with_geographic_diff = 0
        for ccnl in all_ccnl:
            has_diff = any(
                s.geographic_area != GeographicArea.NAZIONALE 
                for s in ccnl.salary_tables
            )
            if has_diff:
                with_geographic_diff += 1
        
        # At least some sectors should have geographic differences (especially Commercio)
        assert with_geographic_diff >= 2
    
    def test_leave_entitlements_compliance(self):
        """Test that leave entitlements comply with Italian labor law minimums."""
        all_ccnl = get_all_priority1_ccnl_data()
        
        for ccnl in all_ccnl:
            # Find ferie (vacation) entitlement
            ferie = next((l for l in ccnl.leave_entitlements 
                         if l.leave_type == LeaveType.FERIE), None)
            
            if ferie:
                # Italian law minimum is 20 days, but CCNLs typically provide more
                assert ferie.base_annual_days >= 22
    
    def test_notice_period_progressivity(self):
        """Test that notice periods increase with seniority and category."""
        all_ccnl = get_all_priority1_ccnl_data()
        
        for ccnl in all_ccnl:
            # Group notice periods by worker category
            operai_notices = [n for n in ccnl.notice_periods 
                             if n.worker_category == WorkerCategory.OPERAIO]
            impiegati_notices = [n for n in ccnl.notice_periods 
                               if n.worker_category == WorkerCategory.IMPIEGATO]
            
            # Notice periods should generally increase with seniority
            if len(operai_notices) >= 2:
                operai_notices.sort(key=lambda n: n.seniority_months_min)
                assert operai_notices[0].notice_days <= operai_notices[-1].notice_days
            
            # Impiegati should generally have longer notice periods than operai
            if operai_notices and impiegati_notices:
                avg_operai_notice = sum(n.notice_days for n in operai_notices) / len(operai_notices)
                avg_impiegati_notice = sum(n.notice_days for n in impiegati_notices) / len(impiegati_notices)
                assert avg_impiegati_notice >= avg_operai_notice
    
    def test_data_quality_and_consistency(self):
        """Test overall data quality and consistency across all Priority 1 CCNLs."""
        all_ccnl = get_all_priority1_ccnl_data()
        
        for ccnl in all_ccnl:
            # Basic structure validation
            assert ccnl.name and len(ccnl.name) > 10
            assert ccnl.valid_from >= date(2020, 1, 1)
            assert ccnl.valid_from < ccnl.valid_to if ccnl.valid_to else True
            
            # Job levels validation
            assert len(ccnl.job_levels) >= 3  # At least some job levels
            level_codes = {level.level_code for level in ccnl.job_levels}
            assert len(level_codes) == len(ccnl.job_levels)  # No duplicates
            
            # Salary tables validation
            assert len(ccnl.salary_tables) >= 3  # At least some salary data
            for salary in ccnl.salary_tables:
                assert salary.base_monthly_salary > 0
                assert any(level.level_code == salary.level_code for level in ccnl.job_levels)
            
            # Leave entitlements validation
            assert len(ccnl.leave_entitlements) >= 2  # At least ferie and permessi
            
            # Working hours validation
            if ccnl.working_hours:
                assert 30 <= ccnl.working_hours.ordinary_weekly_hours <= 40
                assert ccnl.working_hours.maximum_weekly_hours >= ccnl.working_hours.ordinary_weekly_hours


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=app.data.ccnl_priority1"])