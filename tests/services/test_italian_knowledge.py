"""Tests for Italian knowledge service."""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.italian_data import (
    ComplianceCheck,
    ComplianceStatus,
    DocumentType,
    ItalianLegalTemplate,
    ItalianTaxRate,
    TaxCalculation,
    TaxType,
)
from app.services.italian_knowledge import ItalianLegalService, ItalianTaxCalculator, italian_knowledge_service


class TestItalianTaxCalculator:
    """Test cases for Italian tax calculator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = ItalianTaxCalculator()

    def test_calculate_vat_standard(self):
        """Test standard VAT calculation."""
        result = self.calculator.calculate_vat(100.0, "standard")

        assert result["net_amount"] == 100.0
        assert result["vat_rate"] == 0.22
        assert result["vat_amount"] == 22.0
        assert result["gross_amount"] == 122.0
        assert result["vat_type"] == "standard"
        assert "legal_reference" in result

    def test_calculate_vat_reduced(self):
        """Test reduced VAT calculation."""
        result = self.calculator.calculate_vat(100.0, "reduced")

        assert result["vat_rate"] == 0.10
        assert result["vat_amount"] == 10.0
        assert result["gross_amount"] == 110.0

    def test_calculate_vat_zero(self):
        """Test zero VAT calculation."""
        result = self.calculator.calculate_vat(100.0, "zero")

        assert result["vat_rate"] == 0.00
        assert result["vat_amount"] == 0.0
        assert result["gross_amount"] == 100.0

    def test_calculate_vat_invalid_type(self):
        """Test VAT calculation with invalid type defaults to standard."""
        result = self.calculator.calculate_vat(100.0, "invalid")

        # Should default to standard rate
        assert result["vat_rate"] == 0.22

    def test_calculate_irpef_low_income(self):
        """Test IRPEF calculation for low income."""
        result = self.calculator.calculate_irpef(10000.0)

        assert result["gross_income"] == 10000.0
        assert result["taxable_income"] == 10000.0
        assert result["total_tax"] == 2300.0  # 10k * 23%
        assert result["effective_rate"] == 0.23
        assert len(result["breakdown"]) == 1

    def test_calculate_irpef_multiple_brackets(self):
        """Test IRPEF calculation across multiple brackets."""
        result = self.calculator.calculate_irpef(30000.0)

        assert result["gross_income"] == 30000.0
        assert result["taxable_income"] == 30000.0
        assert len(result["breakdown"]) == 2  # Should span 2 brackets

        # First bracket: 15k at 23% = 3450
        # Second bracket: 15k at 25% = 3750
        # Total should be 7200
        expected_tax = (15000 * 0.23) + (15000 * 0.25)
        assert abs(result["total_tax"] - expected_tax) < 1.0

    def test_calculate_irpef_with_deductions(self):
        """Test IRPEF calculation with deductions."""
        result = self.calculator.calculate_irpef(20000.0, deductions=5000.0)

        assert result["gross_income"] == 20000.0
        assert result["deductions"] == 5000.0
        assert result["taxable_income"] == 15000.0
        assert result["total_tax"] == 3450.0  # 15k * 23%

    def test_calculate_irpef_high_income(self):
        """Test IRPEF calculation for high income."""
        result = self.calculator.calculate_irpef(100000.0)

        assert result["gross_income"] == 100000.0
        assert len(result["breakdown"]) == 4  # Should span all brackets
        assert result["total_tax"] > 30000.0  # High income = high tax

    def test_calculate_withholding_professional(self):
        """Test professional withholding tax calculation."""
        result = self.calculator.calculate_withholding_tax(1000.0, "professional")

        assert result["gross_amount"] == 1000.0
        assert result["withholding_rate"] == 0.20
        assert result["withholding_amount"] == 200.0
        assert result["net_amount"] == 800.0
        assert result["tax_type"] == "professional"

    def test_calculate_withholding_employment(self):
        """Test employment withholding tax calculation."""
        result = self.calculator.calculate_withholding_tax(1000.0, "employment")

        assert result["withholding_rate"] == 0.23
        assert result["withholding_amount"] == 230.0
        assert result["net_amount"] == 770.0

    def test_calculate_withholding_dividends(self):
        """Test dividends withholding tax calculation."""
        result = self.calculator.calculate_withholding_tax(1000.0, "dividends")

        assert result["withholding_rate"] == 0.26
        assert result["withholding_amount"] == 260.0
        assert result["net_amount"] == 740.0

    def test_calculate_social_contributions_employee(self):
        """Test social contributions for employee."""
        result = self.calculator.calculate_social_contributions(30000.0, "employee")

        assert result["income"] == 30000.0
        assert result["category"] == "employee"
        assert "pension" in result["contributions"]
        assert "unemployment" in result["contributions"]
        assert result["total_contribution"] > 0
        assert result["net_income"] < result["income"]

    def test_calculate_social_contributions_self_employed(self):
        """Test social contributions for self-employed."""
        result = self.calculator.calculate_social_contributions(30000.0, "self_employed")

        assert result["category"] == "self_employed"
        assert "pension" in result["contributions"]
        assert "health" in result["contributions"]
        assert result["total_contribution"] > result["income"] * 0.30  # Should be > 30%

    def test_calculate_social_contributions_invalid_category(self):
        """Test social contributions with invalid category."""
        with pytest.raises(ValueError) as exc_info:
            self.calculator.calculate_social_contributions(30000.0, "invalid")

        assert "Unknown contributor category" in str(exc_info.value)

    def test_vat_calculation_error_handling(self):
        """Test VAT calculation error handling."""
        with pytest.raises(ValueError):
            self.calculator.calculate_vat("invalid_amount")

    def test_irpef_calculation_error_handling(self):
        """Test IRPEF calculation error handling."""
        with pytest.raises(ValueError):
            self.calculator.calculate_irpef("invalid_income")


class TestItalianLegalService:
    """Test cases for Italian legal service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = ItalianLegalService()

    @pytest.mark.asyncio
    @patch("app.services.italian_knowledge.database_service")
    async def test_get_tax_rates(self, mock_db):
        """Test getting tax rates."""
        # Mock tax rate
        mock_rate = ItalianTaxRate(
            id=1,
            tax_type=TaxType.VAT,
            tax_code="IVA22",
            description="Aliquota IVA ordinaria",
            rate_percentage=Decimal("22.0"),
            valid_from=date(2024, 1, 1),
            law_reference="DPR 633/1972",
        )

        mock_db.get_db.return_value.__aenter__.return_value.execute.return_value.scalars.return_value.all.return_value = [
            mock_rate
        ]

        rates = await self.service.get_tax_rates(TaxType.VAT)

        assert len(rates) == 1
        assert rates[0].tax_type == TaxType.VAT
        assert float(rates[0].rate_percentage) == 22.0

    @pytest.mark.asyncio
    @patch("app.services.italian_knowledge.database_service")
    async def test_get_legal_template(self, mock_db):
        """Test getting legal template."""
        # Mock template
        mock_template = ItalianLegalTemplate(
            id=1,
            template_code="contract_service_it",
            document_type=DocumentType.CONTRACT,
            title="Contratto di Prestazione",
            content="Contratto tra {client_name} e {provider_name}",
            variables={"client_name": "string", "provider_name": "string"},
            legal_basis="Art. 1321 CC",
            required_fields=["client_name", "provider_name"],
            category="commercial",
            valid_from=date(2024, 1, 1),
            author="Legal Dept",
            version="1.0",
        )

        mock_db.get_db.return_value.__aenter__.return_value.execute.return_value.scalar_one_or_none.return_value = (
            mock_template
        )

        template = await self.service.get_legal_template("contract_service_it")

        assert template is not None
        assert template.template_code == "contract_service_it"
        assert template.document_type == DocumentType.CONTRACT

    @pytest.mark.asyncio
    @patch("app.services.italian_knowledge.database_service")
    async def test_search_regulations(self, mock_db):
        """Test searching regulations."""
        # Mock regulation
        from app.models.italian_data import ItalianRegulation

        mock_regulation = ItalianRegulation(
            id=1,
            regulation_type="law",
            number="633",
            year=1972,
            title="Disciplina dell'imposta sul valore aggiunto",
            summary="Normativa IVA italiana",
            authority="State",
            enacted_date=date(1972, 10, 26),
            effective_date=date(1973, 1, 1),
            subjects=["tax", "vat"],
            keywords=["iva", "imposta", "valore aggiunto"],
            source_url="https://normattiva.it/test",
        )

        mock_db.get_db.return_value.__aenter__.return_value.execute.return_value.scalars.return_value.all.return_value = [
            mock_regulation
        ]

        regulations = await self.service.search_regulations(["iva", "imposta"])

        assert len(regulations) == 1
        assert regulations[0].number == "633"
        assert "vat" in regulations[0].subjects

    @pytest.mark.asyncio
    @patch("app.services.italian_knowledge.database_service")
    async def test_perform_tax_calculation_vat(self, mock_db):
        """Test performing VAT calculation."""
        mock_db.get_db.return_value.__aenter__.return_value.add = MagicMock()
        mock_db.get_db.return_value.__aenter__.return_value.commit = AsyncMock()
        mock_db.get_db.return_value.__aenter__.return_value.refresh = AsyncMock()

        calculation_request = {"tax_type": "iva", "amount": 1000.0, "vat_type": "standard"}

        calculation = await self.service.perform_tax_calculation(
            user_id="test_user", session_id="test_session", calculation_request=calculation_request
        )

        assert calculation.calculation_type == TaxType.VAT
        assert float(calculation.base_amount) == 1000.0
        assert float(calculation.tax_amount) == 220.0  # 22% VAT
        assert calculation.confidence_score == 0.95

    @pytest.mark.asyncio
    @patch("app.services.italian_knowledge.database_service")
    async def test_perform_tax_calculation_irpef(self, mock_db):
        """Test performing IRPEF calculation."""
        mock_db.get_db.return_value.__aenter__.return_value.add = MagicMock()
        mock_db.get_db.return_value.__aenter__.return_value.commit = AsyncMock()
        mock_db.get_db.return_value.__aenter__.return_value.refresh = AsyncMock()

        calculation_request = {"tax_type": "irpef", "amount": 25000.0, "deductions": 2000.0}

        calculation = await self.service.perform_tax_calculation(
            user_id="test_user", session_id="test_session", calculation_request=calculation_request
        )

        assert calculation.calculation_type == TaxType.INCOME_TAX
        assert float(calculation.base_amount) == 25000.0
        assert calculation.breakdown["deductions"] == 2000.0

    @pytest.mark.asyncio
    @patch("app.services.italian_knowledge.database_service")
    async def test_check_document_compliance_contract(self, mock_db):
        """Test document compliance check for contract."""
        mock_db.get_db.return_value.__aenter__.return_value.add = MagicMock()
        mock_db.get_db.return_value.__aenter__.return_value.commit = AsyncMock()
        mock_db.get_db.return_value.__aenter__.return_value.refresh = AsyncMock()

        document = {
            "type": "contratto",
            "content": "Contratto tra Mario Rossi e Azienda XYZ per prestazione di servizi al prezzo di €1000 firmato in data 01/01/2024",
        }

        check = await self.service.check_document_compliance(
            user_id="test_user", session_id="test_session", document=document
        )

        assert check.document_type == DocumentType.CONTRACT
        assert check.overall_status in [ComplianceStatus.COMPLIANT, ComplianceStatus.WARNING]
        assert check.compliance_score > 0
        assert len(check.findings) >= 0

    @pytest.mark.asyncio
    @patch("app.services.italian_knowledge.database_service")
    async def test_check_document_compliance_privacy_policy(self, mock_db):
        """Test document compliance check for privacy policy."""
        mock_db.get_db.return_value.__aenter__.return_value.add = MagicMock()
        mock_db.get_db.return_value.__aenter__.return_value.commit = AsyncMock()
        mock_db.get_db.return_value.__aenter__.return_value.refresh = AsyncMock()

        document = {
            "type": "privacy_policy",
            "content": "Il titolare del trattamento è XYZ. La base giuridica è il consenso. I diritti dell'interessato sono...",
        }

        check = await self.service.check_document_compliance(
            user_id="test_user", session_id="test_session", document=document
        )

        assert check.document_type == DocumentType.PRIVACY_POLICY
        assert len(check.recommendations) >= 0

    def test_check_contract_compliance_missing_elements(self):
        """Test contract compliance check with missing elements."""
        content = "Questo è un contratto senza elementi essenziali"

        findings = self.service._check_contract_compliance(content)

        # Should find multiple missing elements
        assert len(findings) > 0
        critical_findings = [f for f in findings if f["severity"] == "critical"]
        assert len(critical_findings) > 0

    def test_check_contract_compliance_complete(self):
        """Test contract compliance check with complete contract."""
        content = """
        Contratto di prestazione tra Mario Rossi (nome delle parti)
        per servizi di consulenza (oggetto) al corrispettivo di €1000
        firmato dalle parti in data 01/01/2024
        """

        findings = self.service._check_contract_compliance(content)

        # Should find fewer issues
        critical_findings = [f for f in findings if f["severity"] == "critical"]
        assert len(critical_findings) < 3  # Some elements should be found

    def test_check_invoice_compliance_missing_elements(self):
        """Test invoice compliance check with missing elements."""
        content = "Fattura senza elementi richiesti"

        findings = self.service._check_invoice_compliance(content)

        # Should find multiple missing critical elements
        critical_findings = [f for f in findings if f["severity"] == "critical"]
        assert len(critical_findings) >= 3  # Number, date, VAT number, VAT amount

    def test_check_invoice_compliance_complete(self):
        """Test invoice compliance check with complete invoice."""
        content = """
        Fattura n. 001/2024 del 15/01/2024
        P.IVA: 12345678901
        Codice Fiscale: RSSMRA80A01H501X
        Servizi di consulenza €1000 + IVA 22% = €220
        Totale: €1220
        """

        findings = self.service._check_invoice_compliance(content)

        # Should find no or few issues
        critical_findings = [f for f in findings if f["severity"] == "critical"]
        assert len(critical_findings) == 0  # All elements should be found

    def test_generate_recommendations(self):
        """Test recommendation generation."""
        findings = [
            {"severity": "critical", "message": "Critical issue 1"},
            {"severity": "critical", "message": "Critical issue 2"},
            {"severity": "warning", "message": "Warning issue 1"},
        ]

        recommendations = self.service._generate_recommendations(findings)

        assert len(recommendations) > 0
        assert any("critical" in rec.lower() for rec in recommendations)

    @pytest.mark.asyncio
    async def test_generate_document_from_template(self):
        """Test document generation from template."""
        # Mock template retrieval
        with patch.object(self.service, "get_legal_template") as mock_get_template:
            template = ItalianLegalTemplate(
                template_code="test_template",
                document_type=DocumentType.CONTRACT,
                title="Test Template",
                content="Contratto tra {client_name} e {provider_name} per {service_description}",
                variables={"client_name": "string", "provider_name": "string", "service_description": "string"},
                legal_basis="Test",
                required_fields=["client_name"],
                category="test",
                valid_from=date.today(),
                author="Test",
                version="1.0",
            )
            mock_get_template.return_value = template

            variables = {
                "client_name": "Mario Rossi",
                "provider_name": "Azienda XYZ",
                "service_description": "consulenza fiscale",
            }

            content = await self.service.generate_document_from_template("test_template", variables)

            assert content is not None
            assert "Mario Rossi" in content
            assert "Azienda XYZ" in content
            assert "consulenza fiscale" in content

    @pytest.mark.asyncio
    async def test_generate_document_template_not_found(self):
        """Test document generation with non-existent template."""
        with patch.object(self.service, "get_legal_template") as mock_get_template:
            mock_get_template.return_value = None

            content = await self.service.generate_document_from_template("nonexistent", {})

            assert content is None


class TestGlobalItalianKnowledgeService:
    """Test the global Italian knowledge service instance."""

    def test_global_instance_available(self):
        """Test that global service instance is available."""
        assert italian_knowledge_service is not None
        assert isinstance(italian_knowledge_service, ItalianLegalService)

    def test_tax_calculator_integration(self):
        """Test that tax calculator is properly integrated."""
        assert hasattr(italian_knowledge_service, "tax_calculator")
        assert isinstance(italian_knowledge_service.tax_calculator, ItalianTaxCalculator)

    def test_service_method_availability(self):
        """Test that all expected service methods are available."""
        expected_methods = [
            "get_tax_rates",
            "get_legal_template",
            "search_regulations",
            "perform_tax_calculation",
            "check_document_compliance",
            "generate_document_from_template",
        ]

        for method_name in expected_methods:
            assert hasattr(italian_knowledge_service, method_name)
            assert callable(getattr(italian_knowledge_service, method_name))


class TestTaxCalculationEdgeCases:
    """Test edge cases for tax calculations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = ItalianTaxCalculator()

    def test_zero_amount_calculations(self):
        """Test calculations with zero amounts."""
        vat_result = self.calculator.calculate_vat(0.0)
        assert vat_result["vat_amount"] == 0.0

        irpef_result = self.calculator.calculate_irpef(0.0)
        assert irpef_result["total_tax"] == 0.0

        withholding_result = self.calculator.calculate_withholding_tax(0.0)
        assert withholding_result["withholding_amount"] == 0.0

    def test_large_amount_calculations(self):
        """Test calculations with very large amounts."""
        large_amount = 1000000.0  # 1 million

        vat_result = self.calculator.calculate_vat(large_amount)
        assert vat_result["vat_amount"] == 220000.0  # 22% of 1M

        irpef_result = self.calculator.calculate_irpef(large_amount)
        assert irpef_result["total_tax"] > 400000.0  # Should be substantial

    def test_precision_handling(self):
        """Test decimal precision in calculations."""
        # Test with amount that could cause precision issues
        amount = 123.456789

        vat_result = self.calculator.calculate_vat(amount)
        # Should handle precision properly
        assert isinstance(vat_result["vat_amount"], float)
        assert vat_result["vat_amount"] > 27.0  # Approximately 22% of 123.46
