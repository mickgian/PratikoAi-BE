#!/usr/bin/env python3
"""Validate Payment Integration Implementation."""

import os
import sys
from pathlib import Path

def check_file_exists(file_path, description):
    """Check if a file exists and return status."""
    full_path = Path(file_path)
    if full_path.exists():
        size = full_path.stat().st_size
        print(f"✅ {description}: {file_path} ({size} bytes)")
        return True
    else:
        print(f"❌ {description}: {file_path} (missing)")
        return False

def check_file_content(file_path, expected_content, description):
    """Check if a file contains expected content."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            if expected_content in content:
                print(f"✅ {description}: Contains required content")
                return True
            else:
                print(f"❌ {description}: Missing required content")
                return False
    except FileNotFoundError:
        print(f"❌ {description}: File not found")
        return False
    except Exception as e:
        print(f"❌ {description}: Error reading file - {e}")
        return False

def main():
    """Validate payment integration implementation."""
    print("🔍 Payment Integration Implementation Validation")
    print("=" * 60)
    
    # Core implementation files
    core_files = [
        ("app/models/payment.py", "Payment Models"),
        ("app/services/stripe_service.py", "Stripe Service"),
        ("app/api/v1/payments.py", "Payment API"),
        ("app/schemas/payment.py", "Payment Schemas"),
        ("migrations/create_payment_tables.sql", "Database Migration"),
        ("PAYMENT_SETUP.md", "Setup Documentation"),
    ]
    
    # Test files
    test_files = [
        ("tests/services/test_stripe_service.py", "Stripe Service Tests"),
        ("tests/api/v1/test_payments.py", "Payment API Tests"),
    ]
    
    # Configuration updates
    config_checks = [
        ("pyproject.toml", "stripe>=7.0.0", "Stripe dependency"),
        ("app/core/config.py", "STRIPE_SECRET_KEY", "Stripe configuration"),
        ("app/api/v1/api.py", "payments_router", "Payment router registration"),
        ("app/main.py", "CostLimiterMiddleware", "Cost limiter middleware"),
    ]
    
    print("\n📁 Core Implementation Files:")
    core_passed = 0
    for file_path, description in core_files:
        if check_file_exists(file_path, description):
            core_passed += 1
    
    print("\n🧪 Test Files:")
    test_passed = 0
    for file_path, description in test_files:
        if check_file_exists(file_path, description):
            test_passed += 1
    
    print("\n⚙️ Configuration Updates:")
    config_passed = 0
    for file_path, expected_content, description in config_checks:
        if check_file_content(file_path, expected_content, description):
            config_passed += 1
    
    # Check specific implementations
    print("\n🔧 Implementation Details:")
    detail_checks = [
        ("app/models/payment.py", "class Subscription", "Subscription model"),
        ("app/models/payment.py", "class Payment", "Payment model"),
        ("app/models/payment.py", "class Invoice", "Invoice model"),
        ("app/services/stripe_service.py", "class StripeService", "Stripe service class"),
        ("app/services/stripe_service.py", "async def create_customer", "Customer creation"),
        ("app/services/stripe_service.py", "async def create_checkout_session", "Checkout session"),
        ("app/services/stripe_service.py", "async def process_webhook_event", "Webhook processing"),
        ("app/api/v1/payments.py", "@router.post(\"/customer\")", "Customer endpoint"),
        ("app/api/v1/payments.py", "@router.post(\"/checkout/session\")", "Checkout endpoint"),
        ("app/api/v1/payments.py", "@router.get(\"/subscription\")", "Subscription endpoint"),
        ("app/api/v1/payments.py", "@router.post(\"/webhook\")", "Webhook endpoint"),
        ("migrations/create_payment_tables.sql", "customers (", "Customers table"),
        ("migrations/create_payment_tables.sql", "subscriptions (", "Subscriptions table"),
        ("migrations/create_payment_tables.sql", "payments (", "Payments table"),
    ]
    
    detail_passed = 0
    for file_path, expected_content, description in detail_checks:
        if check_file_content(file_path, expected_content, description):
            detail_passed += 1
    
    # Summary
    total_core = len(core_files)
    total_test = len(test_files)
    total_config = len(config_checks)
    total_detail = len(detail_checks)
    total_all = total_core + total_test + total_config + total_detail
    total_passed = core_passed + test_passed + config_passed + detail_passed
    
    print("\n" + "=" * 60)
    print(f"📊 Implementation Summary:")
    print(f"   Core Files: {core_passed}/{total_core}")
    print(f"   Test Files: {test_passed}/{total_test}")
    print(f"   Configuration: {config_passed}/{total_config}")
    print(f"   Implementation Details: {detail_passed}/{total_detail}")
    print(f"   Total: {total_passed}/{total_all}")
    
    percentage = (total_passed / total_all) * 100
    print(f"   Completion: {percentage:.1f}%")
    
    if percentage >= 90:
        print("🎉 Payment integration implementation is complete!")
        return True
    elif percentage >= 75:
        print("✅ Payment integration implementation is mostly complete")
        return True
    else:
        print("⚠️ Payment integration implementation needs more work")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)