-- Payment and subscription tables for Stripe integration
-- Migration: create_payment_tables.sql
-- Created: 2025-01-29

-- Create customers table
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) UNIQUE NOT NULL,
    stripe_customer_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    
    -- Billing address
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    address_city VARCHAR(255),
    address_state VARCHAR(255),
    address_postal_code VARCHAR(255),
    address_country VARCHAR(255),
    
    -- Tax information
    tax_id VARCHAR(255),
    tax_exempt BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Additional data
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create subscriptions table
CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    
    -- Stripe-specific fields
    stripe_subscription_id VARCHAR(255) UNIQUE NOT NULL,
    stripe_customer_id VARCHAR(255) NOT NULL,
    stripe_price_id VARCHAR(255) NOT NULL,
    
    -- Subscription details
    status VARCHAR(50) NOT NULL DEFAULT 'inactive',
    plan_type VARCHAR(50) NOT NULL DEFAULT 'monthly',
    amount_eur DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'eur',
    
    -- Billing cycle
    current_period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    current_period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Trial information
    trial_start TIMESTAMP WITH TIME ZONE,
    trial_end TIMESTAMP WITH TIME ZONE,
    
    -- Subscription lifecycle
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    canceled_at TIMESTAMP WITH TIME ZONE,
    ended_at TIMESTAMP WITH TIME ZONE,
    
    -- Additional data
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create payments table
CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    subscription_id INTEGER,
    
    -- Stripe-specific fields
    stripe_payment_intent_id VARCHAR(255) UNIQUE NOT NULL,
    stripe_invoice_id VARCHAR(255),
    stripe_charge_id VARCHAR(255),
    
    -- Payment details
    amount_eur DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'eur',
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    
    -- Payment method
    payment_method_type VARCHAR(50),
    payment_method_last4 VARCHAR(4),
    payment_method_brand VARCHAR(50),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    paid_at TIMESTAMP WITH TIME ZONE,
    failed_at TIMESTAMP WITH TIME ZONE,
    
    -- Failure information
    failure_reason TEXT,
    failure_code VARCHAR(255),
    
    -- Additional data
    metadata JSONB DEFAULT '{}'::jsonb,
    
    FOREIGN KEY (subscription_id) REFERENCES subscriptions(id) ON DELETE SET NULL
);

-- Create invoices table
CREATE TABLE IF NOT EXISTS invoices (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    subscription_id INTEGER,
    payment_id INTEGER,
    
    -- Stripe-specific fields
    stripe_invoice_id VARCHAR(255) UNIQUE NOT NULL,
    stripe_subscription_id VARCHAR(255),
    
    -- Invoice details
    invoice_number VARCHAR(255) NOT NULL,
    amount_eur DECIMAL(10,2) NOT NULL,
    tax_eur DECIMAL(10,2) DEFAULT 0.00,
    total_eur DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'eur',
    
    -- Invoice status
    status VARCHAR(50) NOT NULL,
    paid BOOLEAN DEFAULT FALSE,
    
    -- Billing period
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    due_date TIMESTAMP WITH TIME ZONE,
    paid_at TIMESTAMP WITH TIME ZONE,
    
    -- Download URLs
    invoice_pdf_url TEXT,
    hosted_invoice_url TEXT,
    
    -- Additional data
    metadata JSONB DEFAULT '{}'::jsonb,
    
    FOREIGN KEY (subscription_id) REFERENCES subscriptions(id) ON DELETE SET NULL,
    FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE SET NULL
);

-- Create webhook_events table
CREATE TABLE IF NOT EXISTS webhook_events (
    id SERIAL PRIMARY KEY,
    
    -- Stripe event details
    stripe_event_id VARCHAR(255) UNIQUE NOT NULL,
    event_type VARCHAR(255) NOT NULL,
    
    -- Processing status
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP WITH TIME ZONE,
    
    -- Error handling
    error_count INTEGER DEFAULT 0,
    last_error TEXT,
    last_error_at TIMESTAMP WITH TIME ZONE,
    
    -- Event data
    event_data JSONB NOT NULL,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for customers table
CREATE INDEX IF NOT EXISTS idx_customer_user_id ON customers(user_id);
CREATE INDEX IF NOT EXISTS idx_customer_stripe_id ON customers(stripe_customer_id);
CREATE INDEX IF NOT EXISTS idx_customer_email ON customers(email);

-- Create indexes for subscriptions table
CREATE INDEX IF NOT EXISTS idx_subscription_user_id ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscription_stripe_id ON subscriptions(stripe_subscription_id);
CREATE INDEX IF NOT EXISTS idx_subscription_customer_id ON subscriptions(stripe_customer_id);
CREATE INDEX IF NOT EXISTS idx_subscription_status ON subscriptions(status);

-- Create indexes for payments table
CREATE INDEX IF NOT EXISTS idx_payment_user_id ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payment_subscription_id ON payments(subscription_id);
CREATE INDEX IF NOT EXISTS idx_payment_stripe_intent_id ON payments(stripe_payment_intent_id);
CREATE INDEX IF NOT EXISTS idx_payment_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_payment_created_at ON payments(created_at);

-- Create indexes for invoices table
CREATE INDEX IF NOT EXISTS idx_invoice_user_id ON invoices(user_id);
CREATE INDEX IF NOT EXISTS idx_invoice_subscription_id ON invoices(subscription_id);
CREATE INDEX IF NOT EXISTS idx_invoice_stripe_id ON invoices(stripe_invoice_id);
CREATE INDEX IF NOT EXISTS idx_invoice_status ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_invoice_period ON invoices(period_start, period_end);

-- Create indexes for webhook_events table
CREATE INDEX IF NOT EXISTS idx_webhook_stripe_event_id ON webhook_events(stripe_event_id);
CREATE INDEX IF NOT EXISTS idx_webhook_event_type ON webhook_events(event_type);
CREATE INDEX IF NOT EXISTS idx_webhook_processed ON webhook_events(processed);
CREATE INDEX IF NOT EXISTS idx_webhook_created_at ON webhook_events(created_at);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers to automatically update updated_at
CREATE TRIGGER update_customers_updated_at 
    BEFORE UPDATE ON customers 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_subscriptions_updated_at 
    BEFORE UPDATE ON subscriptions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_payments_updated_at 
    BEFORE UPDATE ON payments 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert sample data for development (only if tables are empty)
DO $$
BEGIN
    -- Only insert if no subscriptions exist
    IF NOT EXISTS (SELECT 1 FROM subscriptions LIMIT 1) THEN
        -- This would typically be populated by Stripe webhooks
        INSERT INTO customers (user_id, stripe_customer_id, email, name, created_at) 
        VALUES ('test_user_1', 'cus_test123', 'test@normoai.it', 'Test User', NOW())
        ON CONFLICT (user_id) DO NOTHING;
        
        INSERT INTO subscriptions (
            user_id, stripe_subscription_id, stripe_customer_id, stripe_price_id,
            status, plan_type, amount_eur, current_period_start, current_period_end,
            trial_start, trial_end, created_at
        ) VALUES (
            'test_user_1', 'sub_test123', 'cus_test123', 'price_test123',
            'trialing', 'monthly', 69.00, 
            NOW() - INTERVAL '3 days', NOW() + INTERVAL '27 days',
            NOW() - INTERVAL '3 days', NOW() + INTERVAL '4 days',
            NOW() - INTERVAL '3 days'
        ) ON CONFLICT (stripe_subscription_id) DO NOTHING;
    END IF;
END $$;

-- Add comments for documentation
COMMENT ON TABLE customers IS 'Stripe customer records linked to users';
COMMENT ON TABLE subscriptions IS 'User subscription records with billing information';
COMMENT ON TABLE payments IS 'Payment transaction records from Stripe';
COMMENT ON TABLE invoices IS 'Invoice records for billing history';
COMMENT ON TABLE webhook_events IS 'Stripe webhook event processing log';

COMMENT ON COLUMN subscriptions.status IS 'active, inactive, past_due, canceled, unpaid, incomplete, incomplete_expired, trialing';
COMMENT ON COLUMN payments.status IS 'pending, succeeded, failed, canceled, refunded';
COMMENT ON COLUMN invoices.status IS 'draft, open, paid, void, uncollectible';