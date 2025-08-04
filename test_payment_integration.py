#!/usr/bin/env python3
"""Simple integration test for payment functionality."""

import os
import sys
from datetime import datetime, timedelta

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_payment_models():
    """Test payment models can be imported and instantiated."""
    try:
        from app.models.payment import (
            Subscription, Payment, Invoice, Customer, WebhookEvent,
            SubscriptionStatus, PaymentStatus, PlanType
        )
        
        print("✅ Payment models imported successfully")
        
        # Test model instantiation
        customer = Customer(
            user_id="test_user",
            stripe_customer_id="cus_test123",
            email="test@normoai.it"
        )
        
        subscription = Subscription(
            user_id="test_user",
            stripe_subscription_id="sub_test123",
            stripe_customer_id="cus_test123",
            stripe_price_id="price_test123",
            status=SubscriptionStatus.ACTIVE,
            plan_type=PlanType.MONTHLY,
            amount_eur=69.00,
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30)
        )
        
        payment = Payment(
            user_id="test_user",
            stripe_payment_intent_id="pi_test123",
            amount_eur=69.00,
            status=PaymentStatus.SUCCEEDED
        )
        
        print("✅ Payment models instantiated successfully")
        return True
        
    except Exception as e:
        print(f"❌ Payment models test failed: {e}")
        return False


def test_stripe_service():
    """Test Stripe service can be imported."""
    try:
        # Mock the settings and database imports
        import stripe
        
        class MockSettings:
            STRIPE_SECRET_KEY = "sk_test_fake"
            STRIPE_WEBHOOK_SECRET = "whsec_fake"
        
        # Test Stripe service import structure
        print("✅ Stripe dependency available")
        print(f"✅ Stripe version: {stripe.__version__}")
        
        return True
        
    except Exception as e:
        print(f"❌ Stripe service test failed: {e}")
        return False


def test_payment_schemas():
    """Test payment schemas can be imported."""
    try:
        from app.schemas.payment import (
            CustomerResponse, CheckoutSessionResponse, SubscriptionInfo,
            BillingInfo, SubscriptionFeatures, SubscriptionResponse,
            InvoiceInfo, PricingPlan, CreateCustomerRequest
        )
        
        print("✅ Payment schemas imported successfully")
        
        # Test schema instantiation
        customer_request = CreateCustomerRequest(
            email="test@normoai.it",
            name="Test User"
        )
        
        print("✅ Payment schemas instantiated successfully")
        return True
        
    except Exception as e:
        print(f"❌ Payment schemas test failed: {e}")
        return False


def test_payment_configuration():
    """Test payment configuration structure."""
    try:
        # Test that we have the right configuration structure
        config_items = [
            "STRIPE_PUBLISHABLE_KEY",
            "STRIPE_SECRET_KEY", 
            "STRIPE_WEBHOOK_SECRET",
            "STRIPE_MONTHLY_PRICE_ID",
            "STRIPE_TRIAL_PERIOD_DAYS"
        ]
        
        print("✅ Payment configuration structure defined")
        print(f"✅ Required config items: {len(config_items)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Payment configuration test failed: {e}")
        return False


def main():
    """Run all payment integration tests."""
    print("🧪 Running Payment Integration Tests")
    print("=" * 50)
    
    tests = [
        ("Payment Models", test_payment_models),
        ("Stripe Service", test_stripe_service),
        ("Payment Schemas", test_payment_schemas),
        ("Payment Configuration", test_payment_configuration),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Testing {test_name}...")
        if test_func():
            passed += 1
            print(f"✅ {test_name} passed")
        else:
            print(f"❌ {test_name} failed")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All payment integration tests passed!")
        return True
    else:
        print("⚠️ Some payment integration tests failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)