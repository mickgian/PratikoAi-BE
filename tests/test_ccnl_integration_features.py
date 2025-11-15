"""
Test suite for CCNL integration features.

Tests real-time updates, alerts, INPS/INAIL integration, and multilingual support.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List

import pytest

from app.models.ccnl_data import AllowanceType, CCNLSector, WorkerCategory
from app.services.ccnl_update_service import AlertType, CCNLAlert, CCNLUpdate, UpdateType, ccnl_update_service
from app.services.i18n_service import Language, i18n_service
from app.services.inps_inail_service import ContributionType, RiskClass, inps_inail_service


class TestCCNLUpdateService:
    """Test CCNL update and alert functionality."""

    @pytest.mark.asyncio
    async def test_check_for_updates(self):
        """Test checking for CCNL updates."""
        updates = await ccnl_update_service.check_for_updates()

        assert isinstance(updates, list)

        for update in updates:
            assert isinstance(update, CCNLUpdate)
            assert update.sector in CCNLSector
            assert update.update_type in UpdateType
            assert isinstance(update.effective_date, date)
            assert isinstance(update.changes_summary, str)
            assert len(update.changes_summary) > 0

    @pytest.mark.asyncio
    async def test_generate_expiration_alerts(self):
        """Test generation of expiration alerts."""
        alerts = await ccnl_update_service.generate_expiration_alerts()

        assert isinstance(alerts, list)

        for alert in alerts:
            assert isinstance(alert, CCNLAlert)
            assert alert.sector in CCNLSector
            assert alert.alert_type in [AlertType.EXPIRING_SOON, AlertType.EXPIRED]
            assert isinstance(alert.title, str)
            assert isinstance(alert.message, str)
            assert alert.severity in ["INFO", "WARNING", "ERROR", "CRITICAL"]

    @pytest.mark.asyncio
    async def test_alert_acknowledgment(self):
        """Test alert acknowledgment functionality."""
        # Generate some alerts first
        alerts = await ccnl_update_service.generate_expiration_alerts()

        if alerts:
            alert = alerts[0]
            assert not alert.acknowledged

            # Acknowledge the alert
            await ccnl_update_service.acknowledge_alert(alert.id)

            # Verify acknowledgment
            active_alerts = await ccnl_update_service.get_active_alerts()
            acknowledged_alert = next((a for a in active_alerts if a.id == alert.id), None)

            if acknowledged_alert:  # Alert might be filtered out if expired
                assert acknowledged_alert.acknowledged

    @pytest.mark.asyncio
    async def test_renewal_monitoring_setup(self):
        """Test setting up renewal monitoring for a sector."""
        sector = CCNLSector.METALMECCANICI_INDUSTRIA
        recipients = ["hr@company.com", "manager@company.com"]

        await ccnl_update_service.setup_renewal_monitoring(sector, recipients)

        # Verify monitoring was set up
        assert sector in ccnl_update_service.renewal_notifications
        notification = ccnl_update_service.renewal_notifications[sector]

        assert notification.sector == sector
        assert notification.notification_recipients == recipients
        assert isinstance(notification.days_until_expiry, int)

    @pytest.mark.asyncio
    async def test_update_statistics(self):
        """Test getting update statistics."""
        stats = await ccnl_update_service.get_update_statistics()

        assert isinstance(stats, dict)
        assert "total_pending_updates" in stats
        assert "active_alerts_count" in stats
        assert "sectors_with_renewals" in stats
        assert "last_update_check" in stats
        assert "updates_by_type" in stats
        assert "alerts_by_severity" in stats

        # Verify data types
        assert isinstance(stats["total_pending_updates"], int)
        assert isinstance(stats["active_alerts_count"], int)
        assert isinstance(stats["sectors_with_renewals"], int)


class TestINPSINAILService:
    """Test INPS/INAIL contribution calculation functionality."""

    @pytest.mark.asyncio
    async def test_get_contribution_rates(self):
        """Test getting contribution rates for different sectors and categories."""
        test_cases = [
            (CCNLSector.METALMECCANICI_INDUSTRIA, WorkerCategory.OPERAIO),
            (CCNLSector.COMMERCIO_TERZIARIO, WorkerCategory.IMPIEGATO),
            (CCNLSector.ICT, WorkerCategory.QUADRO),
            (CCNLSector.CREDITO_ASSICURAZIONI, WorkerCategory.DIRIGENTE),
        ]

        for sector, category in test_cases:
            rates = await inps_inail_service.get_contribution_rates(sector, category)

            assert isinstance(rates, dict)
            assert "inps_employee" in rates
            assert "inps_employer" in rates
            assert "inail_employer" in rates

            # Verify rates are Decimal and non-negative
            for _rate_name, rate_value in rates.items():
                assert isinstance(rate_value, Decimal)
                assert rate_value >= 0

            # Test specific business rules
            if category == WorkerCategory.DIRIGENTE:
                # Executives don't pay standard INPS contributions
                assert rates["inps_employee"] == Decimal("0.00")
                assert rates["inps_employer"] == Decimal("0.00")
            else:
                # Other categories should have positive INPS rates
                assert rates["inps_employee"] > 0
                assert rates["inps_employer"] > 0

    @pytest.mark.asyncio
    async def test_calculate_contributions(self):
        """Test contribution calculation for various scenarios."""
        test_salaries = [Decimal("1500"), Decimal("2500"), Decimal("4000"), Decimal("6000")]
        sector = CCNLSector.METALMECCANICI_INDUSTRIA
        category = WorkerCategory.IMPIEGATO

        for salary in test_salaries:
            calc = await inps_inail_service.calculate_contributions(salary, sector, category)

            # Verify calculation structure
            assert calc.gross_salary == salary
            assert isinstance(calc.inps_employee, Decimal)
            assert isinstance(calc.inps_employer, Decimal)
            assert isinstance(calc.inail_employer, Decimal)
            assert isinstance(calc.net_salary, Decimal)

            # Verify mathematical relationships
            assert calc.net_salary == salary - calc.total_employee_contributions
            assert calc.total_employee_contributions == calc.inps_employee
            assert calc.total_employer_contributions > 0

            # Verify contributions are proportional to salary
            expected_inps_employee = salary * Decimal("0.0919")  # 9.19%
            assert abs(calc.inps_employee - expected_inps_employee) < Decimal("0.10")  # Within 10 cents

    @pytest.mark.asyncio
    async def test_sector_risk_classification(self):
        """Test INAIL risk class assignment for different sectors."""
        risk_classifications = {
            CCNLSector.COMMERCIO_TERZIARIO: RiskClass.CLASS_1,  # Low risk
            CCNLSector.METALMECCANICI_INDUSTRIA: RiskClass.CLASS_3,  # Medium risk
            CCNLSector.EDILIZIA_INDUSTRIA: RiskClass.CLASS_4,  # High risk
            CCNLSector.TRASPORTI_LOGISTICA: RiskClass.CLASS_5,  # Very high risk
        }

        for sector, expected_risk_class in risk_classifications.items():
            risk_class = await inps_inail_service.get_sector_risk_class(sector)
            assert risk_class == expected_risk_class

    @pytest.mark.asyncio
    async def test_annual_contribution_summary(self):
        """Test annual contribution summary generation."""
        annual_salary = Decimal("30000")  # €30,000 per year
        sector = CCNLSector.ICT
        category = WorkerCategory.IMPIEGATO

        summary = await inps_inail_service.get_annual_contribution_summary(sector, category, annual_salary)

        # Verify summary structure
        assert summary["annual_gross_salary"] == annual_salary
        assert summary["monthly_gross_salary"] == annual_salary / 12
        assert "annual_contributions" in summary
        assert "contribution_rates" in summary
        assert "risk_class" in summary

        # Verify annual calculations
        annual_contribs = summary["annual_contributions"]
        monthly_salary = annual_salary / 12

        # Check that annual contributions are 12x monthly
        expected_annual_inps_employee = monthly_salary * Decimal("0.0919") * 12
        actual_annual_inps_employee = annual_contribs["inps_employee"]

        assert abs(actual_annual_inps_employee - expected_annual_inps_employee) < Decimal("1.00")

    @pytest.mark.asyncio
    async def test_contribution_validation(self):
        """Test contribution calculation validation."""
        salary = Decimal("2500")
        sector = CCNLSector.COMMERCIO_TERZIARIO
        category = WorkerCategory.OPERAIO

        calc = await inps_inail_service.calculate_contributions(salary, sector, category)
        is_valid = await inps_inail_service.validate_contribution_calculation(calc)

        assert is_valid

        # Test with modified calculation (should fail validation)
        calc.inps_employee += Decimal("100")  # Artificially inflate employee contribution
        is_valid = await inps_inail_service.validate_contribution_calculation(calc)

        assert not is_valid


class TestI18nService:
    """Test multilingual support functionality."""

    def test_basic_translation(self):
        """Test basic key translation."""
        # Test Italian (default)
        italian_translation = i18n_service.translate("salary", Language.ITALIAN)
        assert italian_translation == "Retribuzione"

        # Test English
        english_translation = i18n_service.translate("salary", Language.ENGLISH)
        assert english_translation == "Salary"

        # Test non-existent key (should return key itself)
        missing_key = i18n_service.translate("non_existent_key")
        assert missing_key == "non_existent_key"

    def test_worker_category_translation(self):
        """Test worker category translations."""
        categories = [
            (WorkerCategory.OPERAIO, "Operaio", "Blue-collar Worker"),
            (WorkerCategory.IMPIEGATO, "Impiegato", "White-collar Employee"),
            (WorkerCategory.QUADRO, "Quadro", "Middle Management"),
            (WorkerCategory.DIRIGENTE, "Dirigente", "Executive"),
        ]

        for category, italian_name, english_name in categories:
            italian_result = i18n_service.translate_worker_category(category, Language.ITALIAN)
            english_result = i18n_service.translate_worker_category(category, Language.ENGLISH)

            assert italian_result == italian_name
            assert english_result == english_name

    def test_allowance_type_translation(self):
        """Test allowance type translations."""
        allowances = [
            (AllowanceType.BUONI_PASTO, "Buoni Pasto", "Meal Vouchers"),
            (AllowanceType.INDENNITA_RISCHIO, "Indennità di Rischio", "Risk Allowance"),
            (AllowanceType.PREMIO_PRODUZIONE, "Premio di Produzione", "Production Bonus"),
        ]

        for allowance_type, italian_name, english_name in allowances:
            italian_result = i18n_service.translate_allowance_type(allowance_type, Language.ITALIAN)
            english_result = i18n_service.translate_allowance_type(allowance_type, Language.ENGLISH)

            assert italian_result == italian_name
            assert english_result == english_name

    def test_sector_translation(self):
        """Test sector-specific translations."""
        sector = CCNLSector.METALMECCANICI_INDUSTRIA

        # Test sector name translation
        italian_name = i18n_service.translate_sector(sector, "name", Language.ITALIAN)
        english_name = i18n_service.translate_sector(sector, "name", Language.ENGLISH)

        assert isinstance(italian_name, str)
        assert isinstance(english_name, str)
        assert len(italian_name) > 0
        assert len(english_name) > 0

        # Test sector description
        italian_desc = i18n_service.translate_sector(sector, "description", Language.ITALIAN)
        english_desc = i18n_service.translate_sector(sector, "description", Language.ENGLISH)

        assert isinstance(italian_desc, str)
        assert isinstance(english_desc, str)

    def test_currency_formatting(self):
        """Test currency formatting for different languages."""
        amount = 1234.56

        # Test Italian formatting
        italian_format = i18n_service.format_currency(amount, Language.ITALIAN)
        assert "€" in italian_format
        assert "," in italian_format  # Italian uses comma as decimal separator

        # Test English formatting
        english_format = i18n_service.format_currency(amount, Language.ENGLISH)
        assert "€" in english_format
        assert "." in english_format  # English uses dot as decimal separator

    def test_date_formatting(self):
        """Test date formatting for different languages."""
        test_date = date(2024, 3, 15)

        # Test Italian formatting
        italian_format = i18n_service.format_date(test_date, Language.ITALIAN)
        assert "marzo" in italian_format  # Italian month name
        assert "15" in italian_format
        assert "2024" in italian_format

        # Test English formatting
        english_format = i18n_service.format_date(test_date, Language.ENGLISH)
        assert "March" in english_format  # English month name
        assert "15" in english_format
        assert "2024" in english_format

    def test_localized_ccnl_summary(self):
        """Test getting localized CCNL summary."""
        sector = CCNLSector.ICT

        # Test Italian summary
        italian_summary = i18n_service.get_localized_ccnl_summary(sector, Language.ITALIAN)

        assert isinstance(italian_summary, dict)
        required_fields = ["sector_name", "description", "typical_companies", "worker_category_label", "salary_label"]

        for field in required_fields:
            assert field in italian_summary
            assert isinstance(italian_summary[field], str)
            assert len(italian_summary[field]) > 0

        # Test English summary
        english_summary = i18n_service.get_localized_ccnl_summary(sector, Language.ENGLISH)

        for field in required_fields:
            assert field in english_summary
            # English and Italian summaries should be different
            if field in ["worker_category_label", "salary_label"]:
                assert italian_summary[field] != english_summary[field]

    def test_translation_validation(self):
        """Test translation completeness validation."""
        validation_result = i18n_service.validate_translations()

        assert isinstance(validation_result, dict)
        assert "missing_english_translations" in validation_result
        assert "missing_italian_translations" in validation_result
        assert "translation_completeness" in validation_result

        # Both languages should have some translations
        completeness = validation_result["translation_completeness"]
        assert completeness["italian"] > 0
        assert completeness["english"] > 0

    def test_language_management(self):
        """Test language management functionality."""
        # Test getting supported languages
        supported_langs = i18n_service.get_supported_languages()
        assert Language.ITALIAN in supported_langs
        assert Language.ENGLISH in supported_langs

        # Test default language
        original_default = i18n_service.default_language

        # Change default language
        i18n_service.set_default_language(Language.ENGLISH)
        assert i18n_service.default_language == Language.ENGLISH

        # Restore original default
        i18n_service.set_default_language(original_default)
        assert i18n_service.default_language == original_default


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple services."""

    @pytest.mark.asyncio
    async def test_multilingual_contribution_calculation(self):
        """Test contribution calculation with multilingual output."""
        salary = Decimal("3000")
        sector = CCNLSector.COMMERCIO_TERZIARIO
        category = WorkerCategory.IMPIEGATO

        # Calculate contributions
        calc = await inps_inail_service.calculate_contributions(salary, sector, category)

        # Get multilingual labels
        italian_labels = {
            "gross_salary": i18n_service.translate("gross_salary", Language.ITALIAN),
            "net_salary": i18n_service.translate("net_salary", Language.ITALIAN),
            "inps_contributions": i18n_service.translate("inps_contributions", Language.ITALIAN),
        }

        english_labels = {
            "gross_salary": i18n_service.translate("gross_salary", Language.ENGLISH),
            "net_salary": i18n_service.translate("net_salary", Language.ENGLISH),
            "inps_contributions": i18n_service.translate("inps_contributions", Language.ENGLISH),
        }

        # Verify translations are different
        assert italian_labels["gross_salary"] != english_labels["gross_salary"]
        assert italian_labels["net_salary"] != english_labels["net_salary"]

        # Verify calculation worked
        assert calc.gross_salary == salary
        assert calc.net_salary < salary

    @pytest.mark.asyncio
    async def test_localized_expiration_alerts(self):
        """Test expiration alerts with localized messages."""
        alerts = await ccnl_update_service.generate_expiration_alerts()

        if alerts:
            alert = alerts[0]

            # Get sector information in both languages
            italian_sector = i18n_service.translate_sector(alert.sector, "name", Language.ITALIAN)
            english_sector = i18n_service.translate_sector(alert.sector, "name", Language.ENGLISH)

            assert isinstance(italian_sector, str)
            assert isinstance(english_sector, str)

            # Verify we have localized content
            assert len(italian_sector) > 0
            assert len(english_sector) > 0

    @pytest.mark.asyncio
    async def test_comprehensive_sector_analysis(self):
        """Test comprehensive analysis of a sector with all integration features."""
        sector = CCNLSector.METALMECCANICI_INDUSTRIA
        category = WorkerCategory.IMPIEGATO
        salary = Decimal("2800")

        # 1. Get contribution calculation
        contribution_calc = await inps_inail_service.calculate_contributions(salary, sector, category)

        # 2. Get risk classification
        risk_class = await inps_inail_service.get_sector_risk_class(sector)

        # 3. Get localized information
        italian_info = i18n_service.get_localized_ccnl_summary(sector, Language.ITALIAN)
        english_info = i18n_service.get_localized_ccnl_summary(sector, Language.ENGLISH)

        # 4. Check for updates
        await ccnl_update_service.check_for_updates()
        sector_updates = [u for u in ccnl_update_service.pending_updates if u.sector == sector]

        # Verify comprehensive analysis
        analysis = {
            "sector": sector.value,
            "contribution_calculation": {
                "gross_salary": contribution_calc.gross_salary,
                "net_salary": contribution_calc.net_salary,
                "total_contributions": contribution_calc.total_employer_contributions,
            },
            "risk_classification": risk_class.value,
            "localized_info": {"italian": italian_info["sector_name"], "english": english_info["sector_name"]},
            "pending_updates": len(sector_updates),
        }

        # Verify all components are present
        assert analysis["contribution_calculation"]["gross_salary"] == salary
        assert analysis["contribution_calculation"]["net_salary"] < salary
        assert analysis["risk_classification"] in [rc.value for rc in RiskClass]
        assert len(analysis["localized_info"]["italian"]) > 0
        assert len(analysis["localized_info"]["english"]) > 0
        assert isinstance(analysis["pending_updates"], int)
