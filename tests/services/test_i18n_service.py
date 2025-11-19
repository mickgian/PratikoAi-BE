"""Tests for i18n service."""

from datetime import datetime
from unittest.mock import patch

import pytest

from app.models.ccnl_data import AllowanceType, CCNLSector, LeaveType, WorkerCategory
from app.services.i18n_service import I18nService, Language


class TestI18nService:
    """Test I18nService class."""

    def test_initialization(self):
        """Test service initialization."""
        service = I18nService()

        assert service.translations is not None
        assert service.sector_translations is not None
        assert service.default_language == Language.ITALIAN
        assert Language.ITALIAN in service.translations
        assert Language.ENGLISH in service.translations

    def test_translate_italian_default(self):
        """Test translation defaults to Italian."""
        service = I18nService()

        result = service.translate("ccnl_agreement")

        assert result == "Contratto Collettivo Nazionale di Lavoro"

    def test_translate_english(self):
        """Test English translation."""
        service = I18nService()

        result = service.translate("ccnl_agreement", Language.ENGLISH)

        assert result == "National Collective Labor Agreement"

    def test_translate_italian_explicit(self):
        """Test explicit Italian translation."""
        service = I18nService()

        result = service.translate("sector", Language.ITALIAN)

        assert result == "Settore"

    def test_translate_missing_key(self):
        """Test translation with missing key returns key itself."""
        service = I18nService()

        result = service.translate("nonexistent_key", Language.ENGLISH)

        assert result == "nonexistent_key"

    def test_translate_sector_italian(self):
        """Test sector translation in Italian."""
        service = I18nService()

        result = service.translate_sector(CCNLSector.METALMECCANICI_INDUSTRIA, "name", Language.ITALIAN)

        assert result == "Metalmeccanici - Industria"

    def test_translate_sector_english(self):
        """Test sector translation in English."""
        service = I18nService()

        result = service.translate_sector(CCNLSector.ICT, "name", Language.ENGLISH)

        assert result == "Information Technology"

    def test_translate_sector_fallback_to_italian(self):
        """Test sector translation fallback to Italian when English not available."""
        service = I18nService()

        # Create a sector with only Italian translation
        service.sector_translations[CCNLSector.COMMERCIO_TERZIARIO] = {
            Language.ITALIAN: {"name": "Test IT"},
        }

        result = service.translate_sector(CCNLSector.COMMERCIO_TERZIARIO, "name", Language.ENGLISH)

        assert result == "Test IT"

    def test_translate_sector_missing_field(self):
        """Test sector translation with missing field."""
        service = I18nService()

        # Use a field that doesn't exist
        result = service.translate_sector(CCNLSector.ICT, "nonexistent_field", Language.ITALIAN)

        # Should return sector value + field name as fallback
        assert "nonexistent_field" in result

    def test_translate_worker_category_italian(self):
        """Test worker category translation in Italian."""
        service = I18nService()

        result = service.translate_worker_category(WorkerCategory.OPERAIO, Language.ITALIAN)

        assert result == "Operaio"

    def test_translate_worker_category_english(self):
        """Test worker category translation in English."""
        service = I18nService()

        result = service.translate_worker_category(WorkerCategory.DIRIGENTE, Language.ENGLISH)

        assert result == "Executive"

    def test_translate_leave_type_italian(self):
        """Test leave type translation in Italian."""
        service = I18nService()

        result = service.translate_leave_type(LeaveType.FERIE, Language.ITALIAN)

        assert result == "Ferie"

    def test_translate_leave_type_english(self):
        """Test leave type translation in English."""
        service = I18nService()

        result = service.translate_leave_type(LeaveType.MALATTIA, Language.ENGLISH)

        assert result == "Sick Leave"

    def test_translate_allowance_type_italian(self):
        """Test allowance type translation in Italian."""
        service = I18nService()

        result = service.translate_allowance_type(AllowanceType.BUONI_PASTO, Language.ITALIAN)

        assert result == "Buoni Pasto"

    def test_translate_allowance_type_english(self):
        """Test allowance type translation in English."""
        service = I18nService()

        result = service.translate_allowance_type(AllowanceType.INDENNITA_TRASPORTO, Language.ENGLISH)

        assert result == "Transport Allowance"

    def test_format_currency_italian(self):
        """Test Italian currency formatting."""
        service = I18nService()

        result = service.format_currency(1234.56, Language.ITALIAN)

        assert result == "€ 1.234,56"

    def test_format_currency_english(self):
        """Test English currency formatting."""
        service = I18nService()

        result = service.format_currency(1234.56, Language.ENGLISH)

        assert result == "€1,234.56"

    def test_format_currency_default_italian(self):
        """Test currency formatting defaults to Italian."""
        service = I18nService()

        result = service.format_currency(999.99)

        assert result == "€ 999,99"

    def test_format_date_italian(self):
        """Test Italian date formatting."""
        service = I18nService()
        date = datetime(2025, 3, 15)

        result = service.format_date(date, Language.ITALIAN)

        assert result == "15 marzo 2025"

    def test_format_date_english(self):
        """Test English date formatting."""
        service = I18nService()
        date = datetime(2025, 12, 25)

        result = service.format_date(date, Language.ENGLISH)

        assert result == "December 25, 2025"

    def test_format_date_all_months_italian(self):
        """Test all Italian month names."""
        service = I18nService()

        expected_months = [
            "gennaio",
            "febbraio",
            "marzo",
            "aprile",
            "maggio",
            "giugno",
            "luglio",
            "agosto",
            "settembre",
            "ottobre",
            "novembre",
            "dicembre",
        ]

        for month, name in enumerate(expected_months, 1):
            date = datetime(2025, month, 1)
            result = service.format_date(date, Language.ITALIAN)
            assert name in result

    def test_get_localized_ccnl_summary_italian(self):
        """Test localized CCNL summary in Italian."""
        service = I18nService()

        result = service.get_localized_ccnl_summary(CCNLSector.METALMECCANICI_INDUSTRIA, Language.ITALIAN)

        assert result["sector_name"] == "Metalmeccanici - Industria"
        assert "metalmeccanico" in result["description"]
        assert "worker_category_label" in result
        assert "salary_label" in result

    def test_get_localized_ccnl_summary_english(self):
        """Test localized CCNL summary in English."""
        service = I18nService()

        result = service.get_localized_ccnl_summary(CCNLSector.ICT, Language.ENGLISH)

        assert result["sector_name"] == "Information Technology"
        assert "IT" in result["description"]
        assert result["worker_category_label"] == "Worker Category"
        assert result["salary_label"] == "Monthly Salary"

    def test_get_localized_job_level_english(self):
        """Test localized job level in English."""
        service = I18nService()

        job_level_data = {
            "level_code": "L5",
            "level_name": "Senior Engineer",
            "category": WorkerCategory.IMPIEGATO,
            "description": "Senior technical role",
            "minimum_experience_months": 60,
        }

        result = service.get_localized_job_level(job_level_data, Language.ENGLISH)

        assert result["level_code"] == "L5"
        assert result["category"] == "White-collar Employee"
        assert "60 months minimum experience" in result["experience_required"]

    def test_get_localized_job_level_italian(self):
        """Test localized job level in Italian."""
        service = I18nService()

        job_level_data = {
            "level_code": "L3",
            "level_name": "Tecnico",
            "category": WorkerCategory.OPERAIO,
            "description": "Ruolo tecnico",
            "minimum_experience_months": 24,
        }

        result = service.get_localized_job_level(job_level_data, Language.ITALIAN)

        assert result["level_code"] == "L3"
        assert result["category"] == "Operaio"
        assert "24 mesi di esperienza minima" in result["experience_required"]

    def test_get_supported_languages(self):
        """Test getting supported languages."""
        service = I18nService()

        result = service.get_supported_languages()

        assert Language.ITALIAN in result
        assert Language.ENGLISH in result
        assert len(result) == 2

    def test_set_default_language(self):
        """Test setting default language."""
        service = I18nService()

        service.set_default_language(Language.ENGLISH)

        assert service.default_language == Language.ENGLISH

        # Test that translation now defaults to English
        result = service.translate("sector")
        assert result == "Sector"

    def test_validate_translations_complete(self):
        """Test translation validation when complete."""
        service = I18nService()

        result = service.validate_translations()

        # Italian and English should have same keys
        assert len(result["missing_english_translations"]) == 0
        assert len(result["missing_italian_translations"]) == 0
        assert result["translation_completeness"]["italian"] > 0
        assert result["translation_completeness"]["english"] > 0

    def test_validate_translations_incomplete(self):
        """Test translation validation when incomplete."""
        service = I18nService()

        # Add a key only to Italian
        service.translations[Language.ITALIAN]["test_key_italian_only"] = "Test"

        result = service.validate_translations()

        assert "test_key_italian_only" in result["missing_english_translations"]

    def test_export_translations_italian(self):
        """Test exporting Italian translations."""
        service = I18nService()

        result = service.export_translations(Language.ITALIAN)

        assert isinstance(result, dict)
        assert "ccnl_agreement" in result
        assert result["ccnl_agreement"] == "Contratto Collettivo Nazionale di Lavoro"

    def test_export_translations_english(self):
        """Test exporting English translations."""
        service = I18nService()

        result = service.export_translations(Language.ENGLISH)

        assert isinstance(result, dict)
        assert "sector" in result
        assert result["sector"] == "Sector"

    def test_import_translations_new_language(self):
        """Test importing translations for new language."""
        service = I18nService()

        new_translations = {"hello": "Ciao", "goodbye": "Arrivederci"}

        # Mock a new language
        fake_language = type("Language", (), {"value": "fr"})()
        service.import_translations(fake_language, new_translations)

        assert fake_language in service.translations
        assert service.translations[fake_language]["hello"] == "Ciao"

    def test_import_translations_update_existing(self):
        """Test importing translations updates existing language."""
        service = I18nService()

        new_translations = {"new_key": "Nuovo Valore"}

        service.import_translations(Language.ITALIAN, new_translations)

        assert service.translations[Language.ITALIAN]["new_key"] == "Nuovo Valore"
        # Original translations should still exist
        assert "ccnl_agreement" in service.translations[Language.ITALIAN]

    def test_sector_translations_coverage(self):
        """Test that main sectors have translations."""
        service = I18nService()

        # Check key sectors
        sectors = [
            CCNLSector.METALMECCANICI_INDUSTRIA,
            CCNLSector.COMMERCIO_TERZIARIO,
            CCNLSector.EDILIZIA_INDUSTRIA,
            CCNLSector.ICT,
            CCNLSector.SANITA_PRIVATA,
        ]

        for sector in sectors:
            assert sector in service.sector_translations
            assert Language.ITALIAN in service.sector_translations[sector]
            assert Language.ENGLISH in service.sector_translations[sector]

    def test_translation_keys_consistency(self):
        """Test that common translation keys exist in both languages."""
        service = I18nService()

        common_keys = [
            "ccnl_agreement",
            "sector",
            "salary",
            "active",
            "expired",
            "calculate",
            "gross_salary",
            "net_salary",
        ]

        for key in common_keys:
            assert key in service.translations[Language.ITALIAN]
            assert key in service.translations[Language.ENGLISH]

    def test_global_instance_exists(self):
        """Test that global i18n_service instance exists."""
        from app.services.i18n_service import i18n_service

        assert i18n_service is not None
        assert isinstance(i18n_service, I18nService)
