# Payment Integration Setup Guide

This document provides setup instructions for the Stripe payment integration in NormoAI.

## 🔧 Prerequisites

1. **Stripe Account**: Create a Stripe account at [stripe.com](https://stripe.com)
2. **Database**: PostgreSQL database with payment tables migrated
3. **Environment Variables**: Stripe API keys configured

## 📋 Environment Variables

Add these environment variables to your `.env` file:

```bash
# Stripe Configuration
STRIPE_PUBLISHABLE_KEY=pk_test_... # or pk_live_... for production
STRIPE_SECRET_KEY=sk_test_...      # or sk_live_... for production
STRIPE_WEBHOOK_SECRET=whsec_...    # Webhook endpoint secret
STRIPE_MONTHLY_PRICE_ID=price_...  # €69/month price ID from Stripe
STRIPE_TRIAL_PERIOD_DAYS=7         # Trial period duration
STRIPE_SUCCESS_URL=https://yourapp.com/payment/success
STRIPE_CANCEL_URL=https://yourapp.com/payment/cancel
```

## 🗄️ Database Setup

Run the payment tables migration:

```bash
# Connect to your PostgreSQL database and run:
psql -d your_database -f migrations/create_payment_tables.sql
```

This creates the following tables:
- `customers` - Stripe customer records
- `subscriptions` - User subscription data
- `payments` - Payment transaction history
- `invoices` - Invoice records
- `webhook_events` - Webhook processing log

## 🎯 Stripe Product Setup

### 1. Create Product in Stripe Dashboard

1. Go to **Products** in your Stripe Dashboard
2. Click **+ Add product**
3. Fill in product details:
   - **Name**: "NormoAI Professional"
   - **Description**: "AI assistant for Italian tax/legal professionals"
   - **Image**: Upload your product image

### 2. Create Pricing

1. In the product, click **+ Add pricing**
2. Configure pricing:
   - **Pricing model**: Standard pricing
   - **Price**: €69.00
   - **Billing interval**: Monthly
   - **Currency**: EUR
3. Copy the **Price ID** (starts with `price_`) to `STRIPE_MONTHLY_PRICE_ID`

### 3. Set Up Webhook Endpoint

1. Go to **Developers > Webhooks** in Stripe Dashboard
2. Click **+ Add endpoint**
3. Configure webhook:
   - **Endpoint URL**: `https://yourapi.com/api/v1/payments/webhook`
   - **Events to send**:
     - `customer.subscription.created`
     - `customer.subscription.updated` 
     - `customer.subscription.deleted`
     - `invoice.payment_succeeded`
     - `invoice.payment_failed`
     - `payment_intent.succeeded`
4. Copy the **Webhook secret** to `STRIPE_WEBHOOK_SECRET`

## 🚀 API Endpoints

The payment integration provides these endpoints:

### Customer Management
- `POST /api/v1/payments/customer` - Create Stripe customer
- `GET /api/v1/payments/subscription` - Get user subscription
- `POST /api/v1/payments/subscription/cancel` - Cancel subscription

### Billing
- `POST /api/v1/payments/checkout/session` - Create checkout session
- `GET /api/v1/payments/invoices` - Get invoice history
- `GET /api/v1/payments/pricing` - Get pricing information

### Webhooks
- `POST /api/v1/payments/webhook` - Handle Stripe webhooks

## 🧪 Testing

### Test Payment Flow

1. **Create Customer**:
```bash
curl -X POST "http://localhost:8000/api/v1/payments/customer" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"email": "test@normoai.it", "name": "Test User"}'
```

2. **Create Checkout Session**:
```bash
curl -X POST "http://localhost:8000/api/v1/payments/checkout/session" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{}'
```

3. **Check Subscription Status**:
```bash
curl -X GET "http://localhost:8000/api/v1/payments/subscription" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Test Cards

Use Stripe's test cards:
- **Success**: `4242424242424242`
- **Decline**: `4000000000000002`
- **3D Secure**: `4000002500003155`

## 📊 Monitoring

### Payment Analytics

Access payment metrics via:
- Usage tracking in `/api/v1/analytics/usage/current`
- Cost breakdown in `/api/v1/analytics/cost/breakdown`
- Payment history in `/api/v1/payments/invoices`

### Logging

Payment events are logged with structured logging:
- `stripe_customer_created`
- `subscription_created_from_stripe`
- `payment_created_from_stripe`
- `webhook_event_processing_failed`

## 🔒 Security

### Webhook Security
- All webhooks verify Stripe signatures
- Duplicate events are automatically handled
- Failed webhook processing is logged and retried

### Cost Limits
- Daily cost limit: €0.10 per user
- Monthly cost limit: €2.00 per user (target)
- Automatic quota enforcement via middleware

## 🐛 Troubleshooting

### Common Issues

1. **Webhook Signature Verification Failed**
   - Check `STRIPE_WEBHOOK_SECRET` matches Stripe dashboard
   - Ensure webhook endpoint is publicly accessible

2. **Price ID Not Found**
   - Verify `STRIPE_MONTHLY_PRICE_ID` exists in Stripe
   - Check if price is active in Stripe dashboard

3. **Customer Creation Failed**
   - Check Stripe API keys are valid
   - Verify network connectivity to Stripe

### Debug Mode

Enable debug logging:
```bash
LOG_LEVEL=DEBUG
LOG_FORMAT=console
```

### Health Check

Verify payment system health:
```bash
curl -X GET "http://localhost:8000/api/v1/payments/pricing"
```

## 🌍 Localization

### Italian Market
- Prices displayed in EUR
- VAT handling automatic via Stripe Tax
- Italian tax ID collection enabled
- GDPR compliant data handling

### Payment Methods
- Credit/Debit cards (Visa, Mastercard, Amex)
- SEPA Direct Debit (for European customers)
- Automatic currency conversion

## 📈 Business Metrics

### Target KPIs
- Monthly Recurring Revenue: €3,450 (50 customers × €69)
- Customer Acquisition Cost: <€20
- Churn Rate: <5% monthly
- Trial-to-Paid Conversion: >20%

### Revenue Tracking
- Real-time subscription analytics
- Usage-based cost optimization
- Automated invoice generation
- Revenue recognition compliance

## 🔄 Maintenance

### Regular Tasks
1. Monitor webhook processing (should be >99% success)
2. Review failed payments weekly
3. Update pricing based on market analysis
4. Optimize API costs to maintain €2/user target

### Backup Strategy
- Payment data replicated to backup database
- Stripe data accessible via API/dashboard
- Invoice PDFs stored in Stripe (10-year retention)