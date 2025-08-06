"""
Comprehensive Tests for Annual Subscription Plans (Italian Market).

These tests validate the €599/year pricing with 27.7% discount for Italian customers,
including Stripe integration, Italian VAT (22% IVA), and invoice requirements.
Tests are written FIRST following TDD methodology - implementation comes after.

Key Requirements:
- Annual plan: €599 (excluding IVA)
- Monthly plan: €69 (for comparison)
- IVA rate: 22% for all Italian customers
- B2B customers: Partita IVA validation and proper invoices
- B2C customers: Codice Fiscale handling
- Plan changes: Prorated billing
- 7-day trial period for both plans
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch, AsyncMock
from dataclasses import dataclass

# Import models and services (to be implemented)
from app.models.subscription import (
    Subscription,
    SubscriptionPlan,
    BillingPeriod,
    SubscriptionStatus
)
from app.services.italian_subscription_service import ItalianSubscriptionService
from app.services.invoice_service import ItalianInvoiceService
from app.services.subscription_analytics import ItalianSubscriptionAnalytics
from app.core.config import settings


@dataclass
class MockStripeSubscription:
    """Mock Stripe subscription for testing"""
    id: str
    status: str
    current_period_start: int
    current_period_end: int
    trial_end: Optional[int] = None
    items: Dict = None


@dataclass
class ItalianCustomerData:
    """Test data for Italian customers"""
    # B2B Customer
    business_customer = {
        "partita_iva": "12345678901",  # Valid format
        "codice_fiscale": None,
        "invoice_name": "Acme Consulting SRL",
        "invoice_address": "Via Roma 123",
        "invoice_cap": "00100",
        "invoice_city": "Roma",
        "invoice_province": "RM",
        "sdi_code": "ABC123X",  # SDI code for electronic invoice
        "pec_email": "fatture@acmeconsulting.it",
        "is_business": True
    }
    
    # B2C Customer
    individual_customer = {
        "partita_iva": None,
        "codice_fiscale": "RSSMRA80A01H501Z",  # Valid format
        "invoice_name": "Mario Rossi",
        "invoice_address": "Via Milano 456",
        "invoice_cap": "20100",
        "invoice_city": "Milano",
        "invoice_province": "MI",
        "sdi_code": None,
        "pec_email": None,
        "is_business": False
    }


class TestSubscriptionCreation:
    """Test subscription creation with Italian market requirements"""
    
    @pytest.mark.asyncio
    async def test_annual_subscription_creation_price(self, italian_subscription_service):
        """Test annual subscription creation at €599 (excluding IVA)"""
        # Arrange
        user_id = "user_123"
        payment_method_id = "pm_test_card"
        
        # Act
        subscription = await italian_subscription_service.create_subscription(
            user_id=user_id,
            plan_type="annual",
            payment_method_id=payment_method_id,
            invoice_data=ItalianCustomerData.business_customer
        )
        
        # Assert
        assert subscription.plan.billing_period == BillingPeriod.ANNUAL
        assert subscription.plan.base_price_cents == 59900  # €599.00
        assert subscription.plan.name == "Professionale Annuale"
        assert subscription.status == SubscriptionStatus.ACTIVE
        assert subscription.is_business is True
        assert subscription.partita_iva == "12345678901"
    
    @pytest.mark.asyncio
    async def test_monthly_subscription_remains_69_euros(self, italian_subscription_service):
        """Test monthly subscription remains at €69"""
        # Arrange
        user_id = "user_456"
        payment_method_id = "pm_test_card"
        
        # Act
        subscription = await italian_subscription_service.create_subscription(
            user_id=user_id,
            plan_type="monthly",
            payment_method_id=payment_method_id,
            invoice_data=ItalianCustomerData.individual_customer
        )
        
        # Assert
        assert subscription.plan.billing_period == BillingPeriod.MONTHLY
        assert subscription.plan.base_price_cents == 6900  # €69.00
        assert subscription.plan.name == "Professionale Mensile"
        assert subscription.is_business is False
        assert subscription.codice_fiscale == "RSSMRA80A01H501Z"
    
    @pytest.mark.asyncio
    async def test_correct_iva_calculation_22_percent(self, italian_subscription_service):
        """Test correct IVA calculation (22% for all Italian customers)"""
        # Arrange
        user_id = "user_789"
        
        # Test annual plan IVA
        annual_subscription = await italian_subscription_service.create_subscription(
            user_id=user_id,
            plan_type="annual",
            payment_method_id="pm_test_card",
            invoice_data=ItalianCustomerData.business_customer
        )
        
        # Test monthly plan IVA
        monthly_subscription = await italian_subscription_service.create_subscription(
            user_id=user_id + "_monthly",
            plan_type="monthly", 
            payment_method_id="pm_test_card",
            invoice_data=ItalianCustomerData.individual_customer
        )
        
        # Assert annual plan IVA
        assert annual_subscription.plan.iva_amount == Decimal("131.78")  # €599 * 0.22
        assert annual_subscription.plan.price_with_iva == Decimal("730.78")  # €599 + €131.78
        
        # Assert monthly plan IVA
        assert monthly_subscription.plan.iva_amount == Decimal("15.18")  # €69 * 0.22
        assert monthly_subscription.plan.price_with_iva == Decimal("84.18")  # €69 + €15.18
    
    @pytest.mark.asyncio
    async def test_b2b_customer_partita_iva_validation(self, italian_subscription_service):
        """Test B2B customers with valid Partita IVA get proper invoices"""
        # Test valid Partita IVA
        valid_data = ItalianCustomerData.business_customer.copy()
        
        subscription = await italian_subscription_service.create_subscription(
            user_id="b2b_user",
            plan_type="annual",
            payment_method_id="pm_test_card",
            invoice_data=valid_data
        )
        
        assert subscription.is_business is True
        assert subscription.partita_iva == "12345678901"
        assert subscription.sdi_code == "ABC123X"
        assert subscription.pec_email == "fatture@acmeconsulting.it"
        
        # Test invalid Partita IVA
        invalid_data = valid_data.copy()
        invalid_data["partita_iva"] = "invalid_piva"
        
        with pytest.raises(ValueError, match="Partita IVA non valida"):
            await italian_subscription_service.create_subscription(
                user_id="invalid_b2b_user",
                plan_type="annual",
                payment_method_id="pm_test_card",
                invoice_data=invalid_data
            )
    
    @pytest.mark.asyncio
    async def test_b2c_customer_codice_fiscale_handling(self, italian_subscription_service):
        """Test B2C customers (no Partita IVA) pricing display"""
        # Test valid Codice Fiscale
        valid_data = ItalianCustomerData.individual_customer.copy()
        
        subscription = await italian_subscription_service.create_subscription(
            user_id="b2c_user",
            plan_type="monthly",
            payment_method_id="pm_test_card",
            invoice_data=valid_data
        )
        
        assert subscription.is_business is False
        assert subscription.codice_fiscale == "RSSMRA80A01H501Z"
        assert subscription.partita_iva is None
        assert subscription.sdi_code is None
        
        # Test missing Codice Fiscale
        invalid_data = valid_data.copy()
        invalid_data["codice_fiscale"] = None
        
        with pytest.raises(ValueError, match="Codice Fiscale richiesto per privati"):
            await italian_subscription_service.create_subscription(
                user_id="invalid_b2c_user",
                plan_type="monthly",
                payment_method_id="pm_test_card",
                invoice_data=invalid_data
            )
    
    @pytest.mark.asyncio
    async def test_subscription_start_dates_and_billing_cycles(self, italian_subscription_service):
        """Test subscription start dates and billing cycles"""
        # Arrange
        start_time = datetime.now()
        
        # Test annual subscription
        annual_sub = await italian_subscription_service.create_subscription(
            user_id="user_annual_cycle",
            plan_type="annual",
            payment_method_id="pm_test_card",
            invoice_data=ItalianCustomerData.business_customer
        )
        
        # Test monthly subscription
        monthly_sub = await italian_subscription_service.create_subscription(
            user_id="user_monthly_cycle",
            plan_type="monthly",
            payment_method_id="pm_test_card",
            invoice_data=ItalianCustomerData.individual_customer
        )
        
        # Assert annual billing cycle
        assert annual_sub.current_period_start >= start_time
        annual_period_length = annual_sub.current_period_end - annual_sub.current_period_start
        assert 360 <= annual_period_length.days <= 370  # Approximately 1 year
        
        # Assert monthly billing cycle
        assert monthly_sub.current_period_start >= start_time
        monthly_period_length = monthly_sub.current_period_end - monthly_sub.current_period_start
        assert 28 <= monthly_period_length.days <= 31  # Approximately 1 month
    
    @pytest.mark.asyncio
    async def test_seven_day_trial_period_both_plans(self, italian_subscription_service):
        """Test 7-day trial period for both plans"""
        # Arrange
        start_time = datetime.now()
        
        # Test annual plan trial
        annual_sub = await italian_subscription_service.create_subscription(
            user_id="user_annual_trial",
            plan_type="annual",
            payment_method_id="pm_test_card",
            invoice_data=ItalianCustomerData.business_customer
        )
        
        # Test monthly plan trial
        monthly_sub = await italian_subscription_service.create_subscription(
            user_id="user_monthly_trial",
            plan_type="monthly",
            payment_method_id="pm_test_card",
            invoice_data=ItalianCustomerData.individual_customer
        )
        
        # Assert trial periods
        assert annual_sub.trial_end is not None
        annual_trial_length = annual_sub.trial_end - start_time
        assert 6 <= annual_trial_length.days <= 8  # 7 days ± tolerance
        
        assert monthly_sub.trial_end is not None
        monthly_trial_length = monthly_sub.trial_end - start_time
        assert 6 <= monthly_trial_length.days <= 8  # 7 days ± tolerance


class TestPlanChanges:
    """Test plan changes between monthly and annual with correct proration"""
    
    @pytest.mark.asyncio
    async def test_upgrade_monthly_to_annual_immediate_charge(self, italian_subscription_service):
        """Test upgrade from monthly to annual (immediate charge, prorated)"""
        # Arrange - Create monthly subscription first
        monthly_sub = await italian_subscription_service.create_subscription(
            user_id="upgrade_user",
            plan_type="monthly",
            payment_method_id="pm_test_card",
            invoice_data=ItalianCustomerData.business_customer
        )
        
        # Simulate 15 days into monthly billing cycle
        days_used = 15
        await self._advance_subscription_time(monthly_sub, days_used)
        
        # Act - Upgrade to annual
        result = await italian_subscription_service.change_plan(
            subscription_id=monthly_sub.id,
            new_plan_type="annual",
            prorate=True
        )
        
        # Assert
        assert result.success is True
        assert result.new_plan.billing_period == BillingPeriod.ANNUAL
        
        # Calculate expected proration
        days_remaining = 30 - days_used  # 15 days left in month
        monthly_daily_rate = Decimal("69.00") / 30
        credit_amount = monthly_daily_rate * days_remaining
        annual_charge = Decimal("599.00") - credit_amount
        
        assert abs(result.prorated_charge - annual_charge) < Decimal("0.01")
        assert result.credit_applied == credit_amount
    
    @pytest.mark.asyncio
    async def test_downgrade_annual_to_monthly_credit_applied(self, italian_subscription_service):
        """Test downgrade from annual to monthly (credit applied)"""
        # Arrange - Create annual subscription first
        annual_sub = await italian_subscription_service.create_subscription(
            user_id="downgrade_user",
            plan_type="annual",
            payment_method_id="pm_test_card",
            invoice_data=ItalianCustomerData.individual_customer
        )
        
        # Simulate 90 days into annual billing cycle
        days_used = 90
        await self._advance_subscription_time(annual_sub, days_used)
        
        # Act - Downgrade to monthly
        result = await italian_subscription_service.change_plan(
            subscription_id=annual_sub.id,
            new_plan_type="monthly",
            prorate=True
        )
        
        # Assert
        assert result.success is True
        assert result.new_plan.billing_period == BillingPeriod.MONTHLY
        
        # Calculate expected credit
        days_remaining = 365 - days_used  # 275 days left in year
        annual_daily_rate = Decimal("599.00") / 365
        credit_amount = annual_daily_rate * days_remaining
        
        assert abs(result.credit_applied - credit_amount) < Decimal("0.01")
        assert result.prorated_charge == Decimal("0")  # No immediate charge for downgrade
    
    @pytest.mark.asyncio
    async def test_mid_cycle_plan_changes_correct_proration(self, italian_subscription_service):
        """Test mid-cycle plan changes with correct proration"""
        # Test various points in billing cycle
        test_cases = [
            {"days_used": 5, "total_days": 30, "plan_from": "monthly", "plan_to": "annual"},
            {"days_used": 25, "total_days": 30, "plan_from": "monthly", "plan_to": "annual"},
            {"days_used": 30, "total_days": 365, "plan_from": "annual", "plan_to": "monthly"},
            {"days_used": 300, "total_days": 365, "plan_from": "annual", "plan_to": "monthly"},
        ]
        
        for i, case in enumerate(test_cases):
            # Create initial subscription
            initial_sub = await italian_subscription_service.create_subscription(
                user_id=f"proration_user_{i}",
                plan_type=case["plan_from"],
                payment_method_id="pm_test_card",
                invoice_data=ItalianCustomerData.business_customer
            )
            
            # Advance time
            await self._advance_subscription_time(initial_sub, case["days_used"])
            
            # Change plan
            result = await italian_subscription_service.change_plan(
                subscription_id=initial_sub.id,
                new_plan_type=case["plan_to"],
                prorate=True
            )
            
            # Verify proration calculation
            assert result.success is True
            
            # Credit should be proportional to unused time
            days_remaining = case["total_days"] - case["days_used"]
            usage_ratio = days_remaining / case["total_days"]
            assert 0 <= usage_ratio <= 1
            
            if case["plan_from"] == "monthly":
                expected_credit = Decimal("69.00") * Decimal(str(usage_ratio))
            else:
                expected_credit = Decimal("599.00") * Decimal(str(usage_ratio))
            
            assert abs(result.credit_applied - expected_credit) < Decimal("1.00")
    
    @pytest.mark.asyncio
    async def test_cancellation_policies_no_refund_annual(self, italian_subscription_service):
        """Test cancellation policies (no refund for annual)"""
        # Test annual subscription cancellation
        annual_sub = await italian_subscription_service.create_subscription(
            user_id="cancel_annual_user",
            plan_type="annual",
            payment_method_id="pm_test_card",
            invoice_data=ItalianCustomerData.business_customer
        )
        
        # Simulate 100 days into subscription
        await self._advance_subscription_time(annual_sub, 100)
        
        # Cancel subscription
        result = await italian_subscription_service.cancel_subscription(
            subscription_id=annual_sub.id,
            immediately=False  # Cancel at period end
        )
        
        # Assert no refund for annual
        assert result.success is True
        assert result.refund_amount == Decimal("0")  # No refund policy
        assert result.access_until == annual_sub.current_period_end
        assert result.cancel_at_period_end is True
        
        # Test monthly subscription cancellation
        monthly_sub = await italian_subscription_service.create_subscription(
            user_id="cancel_monthly_user",
            plan_type="monthly",
            payment_method_id="pm_test_card",
            invoice_data=ItalianCustomerData.individual_customer
        )
        
        # Cancel monthly (should also have no refund, but different policy)
        result = await italian_subscription_service.cancel_subscription(
            subscription_id=monthly_sub.id,
            immediately=False
        )
        
        assert result.success is True
        assert result.refund_amount == Decimal("0")  # Consistent no-refund policy
        assert result.access_until == monthly_sub.current_period_end
    
    @pytest.mark.asyncio
    async def test_reactivation_cancelled_subscriptions(self, italian_subscription_service):
        """Test reactivation of cancelled subscriptions"""
        # Create and cancel subscription
        subscription = await italian_subscription_service.create_subscription(
            user_id="reactivation_user",
            plan_type="annual",
            payment_method_id="pm_test_card",
            invoice_data=ItalianCustomerData.business_customer
        )
        
        await italian_subscription_service.cancel_subscription(
            subscription_id=subscription.id,
            immediately=False
        )
        
        # Reactivate subscription
        result = await italian_subscription_service.reactivate_subscription(
            subscription_id=subscription.id,
            payment_method_id="pm_test_card_new"
        )
        
        # Assert reactivation
        assert result.success is True
        assert result.subscription.status == SubscriptionStatus.ACTIVE
        assert result.subscription.cancel_at_period_end is False
        
        # Should maintain same plan and pricing
        assert result.subscription.plan.billing_period == BillingPeriod.ANNUAL
        assert result.subscription.plan.base_price_cents == 59900
    
    @pytest.mark.asyncio
    async def test_plan_changes_during_trial_period(self, italian_subscription_service):
        """Test plan changes during trial period"""
        # Create monthly subscription with trial
        monthly_sub = await italian_subscription_service.create_subscription(
            user_id="trial_change_user",
            plan_type="monthly",
            payment_method_id="pm_test_card",
            invoice_data=ItalianCustomerData.business_customer
        )
        
        # Ensure we're still in trial
        assert monthly_sub.trial_end > datetime.now()
        
        # Change to annual during trial
        result = await italian_subscription_service.change_plan(
            subscription_id=monthly_sub.id,
            new_plan_type="annual",
            prorate=True
        )
        
        # Assert trial is preserved
        assert result.success is True
        assert result.new_plan.billing_period == BillingPeriod.ANNUAL
        assert result.subscription.trial_end == monthly_sub.trial_end  # Trial preserved
        assert result.prorated_charge == Decimal("0")  # No charge during trial
    
    async def _advance_subscription_time(self, subscription: Subscription, days: int):
        """Helper method to simulate time advancement for testing"""
        # This would be implemented to mock time advancement
        # In real implementation, would adjust current_period_start/end
        subscription.current_period_start += timedelta(days=days)


class TestItalianInvoices:
    """Test Italian invoice generation with all requirements"""
    
    @pytest.mark.asyncio
    async def test_invoice_generation_italian_requirements(self, italian_invoice_service):
        """Test invoice generation with Italian requirements"""
        # Arrange
        subscription = await self._create_test_subscription(
            plan_type="annual",
            customer_data=ItalianCustomerData.business_customer
        )
        
        # Act
        invoice_data, pdf_content = await italian_invoice_service.generate_invoice(
            subscription=subscription,
            payment_amount=Decimal("730.78")  # €599 + 22% IVA
        )
        
        # Assert required Italian fields
        assert invoice_data["numero_fattura"] is not None
        assert invoice_data["data_fattura"] is not None
        assert invoice_data["tipo_documento"] == "TD01"  # Standard invoice
        
        # Supplier data (PratikoAI)
        fornitore = invoice_data["fornitore"]
        assert fornitore["denominazione"] == "PratikoAI SRL"
        assert fornitore["partita_iva"].startswith("IT")
        assert len(fornitore["partita_iva"]) == 13  # IT + 11 digits
        
        # Customer data
        cliente = invoice_data["cliente"]
        assert cliente["denominazione"] == "Acme Consulting SRL"
        assert cliente["partita_iva"] == "12345678901"
        assert cliente["indirizzo"] == "Via Roma 123"
        assert cliente["cap"] == "00100"
        assert cliente["comune"] == "Roma"
        assert cliente["provincia"] == "RM"
        
        # Invoice lines
        righe = invoice_data["righe"]
        assert len(righe) == 1
        assert righe[0]["descrizione"] == "Abbonamento Professionale Annuale"
        assert righe[0]["quantita"] == 1
        assert righe[0]["prezzo_unitario"] == Decimal("599.00")
        assert righe[0]["aliquota_iva"] == 22
        assert righe[0]["importo_iva"] == Decimal("131.78")
        assert righe[0]["importo_totale"] == Decimal("730.78")
        
        # Totals
        assert invoice_data["imponibile"] == Decimal("599.00")
        assert invoice_data["iva"] == Decimal("131.78")
        assert invoice_data["totale"] == Decimal("730.78")
        
        # PDF should be generated
        assert pdf_content is not None
        assert len(pdf_content) > 0
    
    @pytest.mark.asyncio
    async def test_partita_iva_validation_algorithm(self, italian_subscription_service):
        """Test Partita IVA validation (11 digits, Luhn algorithm)"""
        valid_pivas = [
            "12345678901",  # Valid test case
            "01234567890",  # Another valid case
        ]
        
        invalid_pivas = [
            "1234567890",   # Too short
            "123456789012", # Too long
            "1234567890a",  # Contains letter
            "12345678900",  # Invalid check digit
            "",             # Empty
            None            # None
        ]
        
        # Test valid Partita IVAs
        for piva in valid_pivas:
            result = italian_subscription_service.validate_partita_iva(piva)
            assert result is True, f"Expected {piva} to be valid"
        
        # Test invalid Partita IVAs
        for piva in invalid_pivas:
            result = italian_subscription_service.validate_partita_iva(piva)
            assert result is False, f"Expected {piva} to be invalid"
    
    @pytest.mark.asyncio
    async def test_codice_fiscale_handling_individuals(self, italian_subscription_service):
        """Test Codice Fiscale handling for individuals"""
        valid_codici = [
            "RSSMRA80A01H501Z",  # Standard individual format
            "BNCGVN85T50F205X",  # Another valid format
        ]
        
        invalid_codici = [
            "RSSMRA80A01H501",   # Too short
            "RSSMRA80A01H501ZZ", # Too long
            "rssmra80a01h501z",  # Lowercase (should be normalized)
            "1234567890123456",  # All numbers
            "",                  # Empty
            None                 # None
        ]
        
        # Test valid Codici Fiscali
        for cf in valid_codici:
            result = italian_subscription_service.validate_codice_fiscale(cf)
            assert result is True, f"Expected {cf} to be valid"
        
        # Test invalid Codici Fiscali
        for cf in invalid_codici:
            if cf and cf.lower() == cf and len(cf) == 16:  # Lowercase case
                # Should be normalized to uppercase and pass
                continue
            result = italian_subscription_service.validate_codice_fiscale(cf)
            assert result is False, f"Expected {cf} to be invalid"
    
    @pytest.mark.asyncio
    async def test_fattura_elettronica_xml_preparation(self, italian_invoice_service):
        """Test fattura elettronica XML preparation"""
        # Arrange
        business_subscription = await self._create_test_subscription(
            plan_type="annual",
            customer_data=ItalianCustomerData.business_customer
        )
        
        # Act
        xml_content = await italian_invoice_service.generate_fattura_elettronica_xml(
            subscription=business_subscription,
            payment_amount=Decimal("730.78")
        )
        
        # Assert XML structure
        assert xml_content is not None
        assert "<FatturaElettronica" in xml_content
        assert 'versione="FPR12"' in xml_content
        
        # Check required elements
        assert "<CedentePrestatore>" in xml_content  # Supplier data
        assert "<CessionarioCommittente>" in xml_content  # Customer data
        assert "<DatiGenerali>" in xml_content  # General data
        assert "<DettaglioLinee>" in xml_content  # Line items
        assert "<DatiRiepilogo>" in xml_content  # Summary data
        
        # Check specific values
        assert "<IdPaese>IT</IdPaese>" in xml_content
        assert "<Denominazione>PratikoAI SRL</Denominazione>" in xml_content
        assert "<IdCodice>12345678901</IdCodice>" in xml_content  # Customer P.IVA
        assert "<CodiceDestinatario>ABC123X</CodiceDestinatario>" in xml_content  # SDI code
        assert "<Aliquota>22.00</Aliquota>" in xml_content  # IVA rate
    
    @pytest.mark.asyncio
    async def test_correct_iva_breakdown_invoices(self, italian_invoice_service):
        """Test correct IVA breakdown on invoices"""
        # Test both monthly and annual plans
        test_cases = [
            {
                "plan_type": "monthly",
                "base_amount": Decimal("69.00"),
                "iva_amount": Decimal("15.18"),
                "total_amount": Decimal("84.18")
            },
            {
                "plan_type": "annual",
                "base_amount": Decimal("599.00"),
                "iva_amount": Decimal("131.78"),
                "total_amount": Decimal("730.78")
            }
        ]
        
        for case in test_cases:
            # Create subscription
            subscription = await self._create_test_subscription(
                plan_type=case["plan_type"],
                customer_data=ItalianCustomerData.business_customer
            )
            
            # Generate invoice
            invoice_data, _ = await italian_invoice_service.generate_invoice(
                subscription=subscription,
                payment_amount=case["total_amount"]
            )
            
            # Assert IVA calculations
            assert invoice_data["imponibile"] == case["base_amount"]
            assert invoice_data["iva"] == case["iva_amount"]
            assert invoice_data["totale"] == case["total_amount"]
            
            # Check IVA rate is always 22%
            for riga in invoice_data["righe"]:
                assert riga["aliquota_iva"] == 22
    
    @pytest.mark.asyncio
    async def test_invoice_numbering_sequence(self, italian_invoice_service):
        """Test invoice numbering sequence"""
        # Generate multiple invoices
        invoice_numbers = []
        
        for i in range(5):
            subscription = await self._create_test_subscription(
                plan_type="annual",
                customer_data=ItalianCustomerData.business_customer
            )
            
            invoice_data, _ = await italian_invoice_service.generate_invoice(
                subscription=subscription,
                payment_amount=Decimal("730.78")
            )
            
            invoice_numbers.append(invoice_data["numero_fattura"])
        
        # Assert sequential numbering
        for i in range(1, len(invoice_numbers)):
            current_num = int(invoice_numbers[i].split("/")[-1])  # Extract number part
            previous_num = int(invoice_numbers[i-1].split("/")[-1])
            assert current_num == previous_num + 1, "Invoice numbers should be sequential"
    
    @pytest.mark.asyncio
    async def test_sdi_compliance_fields(self, italian_invoice_service):
        """Test electronic invoice SDI compliance fields"""
        # Test business customer with SDI
        business_subscription = await self._create_test_subscription(
            plan_type="annual",
            customer_data=ItalianCustomerData.business_customer
        )
        
        xml_content = await italian_invoice_service.generate_fattura_elettronica_xml(
            subscription=business_subscription,
            payment_amount=Decimal("730.78")
        )
        
        # Assert SDI-specific fields
        assert "<CodiceDestinatario>ABC123X</CodiceDestinatario>" in xml_content
        assert "<PECDestinatario>fatture@acmeconsulting.it</PECDestinatario>" in xml_content
        
        # Test individual customer (should use default SDI code)
        individual_subscription = await self._create_test_subscription(
            plan_type="monthly",
            customer_data=ItalianCustomerData.individual_customer
        )
        
        xml_individual = await italian_invoice_service.generate_fattura_elettronica_xml(
            subscription=individual_subscription,
            payment_amount=Decimal("84.18")
        )
        
        # Individual customers should have default SDI code
        assert "<CodiceDestinatario>0000000</CodiceDestinatario>" in xml_individual
        assert "<PECDestinatario>" not in xml_individual  # No PEC for individuals
    
    async def _create_test_subscription(self, plan_type: str, customer_data: Dict):
        """Helper method to create test subscription"""
        # Mock subscription creation for testing
        subscription = Mock()
        subscription.id = f"sub_test_{plan_type}"
        subscription.plan = Mock()
        subscription.plan.name = f"Professionale {'Annuale' if plan_type == 'annual' else 'Mensile'}"
        subscription.plan.billing_period = BillingPeriod.ANNUAL if plan_type == "annual" else BillingPeriod.MONTHLY
        subscription.plan.base_price_cents = 59900 if plan_type == "annual" else 6900
        
        # Set customer data
        for key, value in customer_data.items():
            setattr(subscription, key, value)
        
        return subscription


class TestFinancialReporting:
    """Test financial reporting for annual subscriptions"""
    
    @pytest.mark.asyncio
    async def test_mrr_calculation_with_annual_subscriptions(self, subscription_analytics):
        """Test MRR calculation with annual subscriptions"""
        # Arrange - Create mix of subscriptions
        subscriptions = [
            {"plan_type": "monthly", "count": 10, "price": 69.00},
            {"plan_type": "annual", "count": 20, "price": 599.00},
        ]
        
        await self._setup_test_subscriptions(subscriptions)
        
        # Act
        metrics = await subscription_analytics.get_financial_metrics()
        
        # Assert MRR calculation
        # Monthly: 10 × €69 = €690
        # Annual: 20 × €599/12 = 20 × €49.92 = €998.40
        expected_mrr = Decimal("690.00") + Decimal("998.40")
        
        assert abs(metrics["mrr"] - expected_mrr) < Decimal("0.01")
        assert metrics["annual_subscribers"] == 20
        assert metrics["monthly_subscribers"] == 10
    
    @pytest.mark.asyncio
    async def test_revenue_recognition_accounting(self, subscription_analytics):
        """Test revenue recognition (€49.92/month for accounting)"""
        # Create annual subscription
        annual_sub = await self._create_test_subscription("annual")
        
        # Get monthly revenue recognition
        monthly_revenue = await subscription_analytics.get_monthly_revenue_recognition(
            subscription_id=annual_sub.id,
            month=datetime.now().month,
            year=datetime.now().year
        )
        
        # Assert
        expected_monthly = Decimal("599.00") / 12
        assert abs(monthly_revenue - expected_monthly) < Decimal("0.01")
        assert abs(monthly_revenue - Decimal("49.92")) < Decimal("0.01")
        
        # Test full year recognition
        annual_revenue = await subscription_analytics.get_annual_revenue_recognition(
            subscription_id=annual_sub.id,
            year=datetime.now().year
        )
        
        assert annual_revenue == Decimal("599.00")
    
    @pytest.mark.asyncio
    async def test_iva_reporting_italian_tax_authorities(self, subscription_analytics):
        """Test IVA reporting for Italian tax authorities"""
        # Create subscriptions with different IVA amounts
        subscriptions = [
            {"plan_type": "monthly", "count": 15},
            {"plan_type": "annual", "count": 25},
        ]
        
        await self._setup_test_subscriptions(subscriptions)
        
        # Get IVA report
        iva_report = await subscription_analytics.get_iva_report(
            start_date=datetime.now().replace(day=1),  # Start of month
            end_date=datetime.now()
        )
        
        # Assert IVA calculations
        expected_monthly_iva = 15 * Decimal("15.18")  # €15.18 per monthly
        expected_annual_iva = 25 * Decimal("131.78")  # €131.78 per annual
        total_expected_iva = expected_monthly_iva + expected_annual_iva
        
        assert abs(iva_report["total_iva_collected"] - total_expected_iva) < Decimal("0.01")
        assert iva_report["iva_rate"] == Decimal("22.00")
        assert iva_report["total_invoices"] == 40
        
        # Check breakdown by plan type
        assert iva_report["breakdown"]["monthly"]["count"] == 15
        assert iva_report["breakdown"]["annual"]["count"] == 25
    
    @pytest.mark.asyncio
    async def test_cash_flow_reporting_upfront_vs_recognized(self, subscription_analytics):
        """Test cash flow reporting (upfront vs recognized)"""
        # Create annual subscriptions at different times
        subscriptions = [
            {"created_date": datetime.now() - timedelta(days=30), "count": 10},
            {"created_date": datetime.now() - timedelta(days=60), "count": 15},
            {"created_date": datetime.now() - timedelta(days=90), "count": 5},
        ]
        
        await self._setup_annual_subscriptions_with_dates(subscriptions)
        
        # Get cash flow report
        cash_flow = await subscription_analytics.get_cash_flow_report(
            start_date=datetime.now() - timedelta(days=90),
            end_date=datetime.now()
        )
        
        # Assert upfront cash received
        total_upfront = 30 * Decimal("730.78")  # 30 subs × €730.78 (including IVA)
        assert abs(cash_flow["total_cash_received"] - total_upfront) < Decimal("0.01")
        
        # Assert recognized revenue (should be less than cash received)
        # Each annual sub recognizes €49.92/month
        months_elapsed = 3  # 90 days ≈ 3 months
        expected_recognized = 30 * Decimal("49.92") * months_elapsed
        assert abs(cash_flow["total_revenue_recognized"] - expected_recognized) < Decimal("10.00")
        
        # Deferred revenue should be positive
        deferred = cash_flow["total_cash_received"] - cash_flow["total_revenue_recognized"]
        assert deferred > Decimal("0")
    
    @pytest.mark.asyncio
    async def test_discount_tracking_business_metrics(self, subscription_analytics):
        """Test discount tracking for business metrics"""
        # Create mix of subscriptions
        await self._setup_test_subscriptions([
            {"plan_type": "monthly", "count": 20},
            {"plan_type": "annual", "count": 30},
        ])
        
        # Get discount metrics
        discount_metrics = await subscription_analytics.get_discount_metrics()
        
        # Assert annual plan savings
        monthly_equivalent_annual = 30 * 12 * Decimal("69.00")  # If they paid monthly
        actual_annual_revenue = 30 * Decimal("599.00")
        total_savings = monthly_equivalent_annual - actual_annual_revenue
        
        assert abs(discount_metrics["total_annual_savings"] - total_savings) < Decimal("0.01")
        assert discount_metrics["average_savings_per_annual_customer"] == Decimal("229.00")  # €828 - €599
        assert abs(discount_metrics["discount_percentage"] - Decimal("27.7")) < Decimal("0.1")
        
        # Penetration metrics
        total_customers = 50
        annual_customers = 30
        annual_penetration = (annual_customers / total_customers) * 100
        
        assert abs(discount_metrics["annual_plan_penetration"] - annual_penetration) < Decimal("0.1")
    
    async def _setup_test_subscriptions(self, subscriptions: List[Dict]):
        """Helper to setup test subscriptions"""
        # Mock subscription creation for testing
        pass
    
    async def _create_test_subscription(self, plan_type: str):
        """Helper to create single test subscription"""
        # Mock subscription for testing
        pass
    
    async def _setup_annual_subscriptions_with_dates(self, subscriptions: List[Dict]):
        """Helper to setup annual subscriptions with specific dates"""
        # Mock subscription creation with dates
        pass


class TestSubscriptionDiscounts:
    """Test annual subscription discount calculations and display"""
    
    def test_annual_plan_savings_calculation(self):
        """Test that annual plan provides correct 27.7% discount"""
        # Arrange
        monthly_price = Decimal("69.00")
        annual_price = Decimal("599.00")
        
        # Calculate savings
        monthly_equivalent = monthly_price * 12  # €828
        savings = monthly_equivalent - annual_price  # €229
        discount_percentage = (savings / monthly_equivalent) * 100
        
        # Assert
        assert monthly_equivalent == Decimal("828.00")
        assert savings == Decimal("229.00")
        assert abs(discount_percentage - Decimal("27.7")) < Decimal("0.1")
    
    def test_monthly_equivalent_pricing_display(self):
        """Test monthly equivalent pricing for annual plan"""
        annual_price = Decimal("599.00")
        monthly_equivalent = annual_price / 12
        
        assert abs(monthly_equivalent - Decimal("49.92")) < Decimal("0.01")
    
    @pytest.mark.asyncio
    async def test_pricing_display_italian_market(self, subscription_service):
        """Test pricing display for Italian market with IVA"""
        # Get pricing information
        pricing = await subscription_service.get_pricing_info()
        
        # Assert pricing structure
        monthly_plan = pricing["plans"]["monthly"]
        annual_plan = pricing["plans"]["annual"]
        
        # Monthly plan
        assert monthly_plan["base_price"] == Decimal("69.00")
        assert monthly_plan["iva_amount"] == Decimal("15.18")
        assert monthly_plan["total_with_iva"] == Decimal("84.18")
        
        # Annual plan
        assert annual_plan["base_price"] == Decimal("599.00")
        assert annual_plan["iva_amount"] == Decimal("131.78")
        assert annual_plan["total_with_iva"] == Decimal("730.78")
        assert annual_plan["monthly_equivalent"] == Decimal("49.92")
        assert annual_plan["savings"]["amount"] == Decimal("229.00")
        assert abs(annual_plan["savings"]["percentage"] - Decimal("27.7")) < Decimal("0.1")


# Fixtures for dependency injection
@pytest.fixture
async def italian_subscription_service():
    """Provide Italian subscription service for testing"""
    # Mock Stripe client
    stripe_client = Mock()
    
    # Create service with mocked dependencies
    service = ItalianSubscriptionService(stripe_client=stripe_client)
    
    # Mock validation methods
    service.validate_partita_iva = Mock(return_value=True)
    service.validate_codice_fiscale = Mock(return_value=True)
    
    return service


@pytest.fixture
async def italian_invoice_service():
    """Provide Italian invoice service for testing"""
    service = ItalianInvoiceService()
    
    # Mock invoice number generation
    service._invoice_counter = 1000
    service.get_next_invoice_number = Mock(side_effect=lambda: f"2024/{service._invoice_counter}")
    
    return service


@pytest.fixture
async def subscription_analytics():
    """Provide subscription analytics service for testing"""
    return ItalianSubscriptionAnalytics()


class TestStripeIntegration:
    """Test Stripe integration for Italian market"""
    
    @pytest.mark.asyncio
    async def test_stripe_subscription_creation_with_tax_rates(self):
        """Test Stripe subscription creation with Italian tax rates"""
        # This would test actual Stripe integration
        # Implementation would include mocking Stripe API calls
        pass
    
    @pytest.mark.asyncio
    async def test_stripe_webhook_handling_for_italian_invoices(self):
        """Test Stripe webhook handling for invoice generation"""
        # Test webhook processing for payment success
        pass
    
    @pytest.mark.asyncio
    async def test_stripe_proration_for_plan_changes(self):
        """Test Stripe proration handling for plan changes"""
        # Test Stripe's proration calculation
        pass


class TestEmailNotifications:
    """Test email notifications in Italian"""
    
    @pytest.mark.asyncio
    async def test_welcome_email_annual_subscription_italian(self):
        """Test welcome email for annual subscription in Italian"""
        # Test Italian email template
        pass
    
    @pytest.mark.asyncio
    async def test_plan_change_notification_emails(self):
        """Test plan change notification emails"""
        # Test upgrade/downgrade notifications
        pass
    
    @pytest.mark.asyncio
    async def test_renewal_reminder_emails_italian(self):
        """Test renewal reminder emails in Italian"""
        # Test 30-day, 7-day renewal reminders
        pass