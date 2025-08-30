-- OAuth fields migration for user table
-- Add OAuth support fields to user table

BEGIN;

-- Add OAuth profile fields
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS name VARCHAR(255);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(512);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS provider VARCHAR(50) DEFAULT 'email' NOT NULL;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS provider_id VARCHAR(255);

-- Make hashed_password nullable for OAuth users
ALTER TABLE "user" ALTER COLUMN hashed_password DROP NOT NULL;

-- Create indexes for OAuth fields
CREATE INDEX IF NOT EXISTS ix_user_provider ON "user" (provider);
CREATE INDEX IF NOT EXISTS ix_user_provider_id ON "user" (provider_id);

-- Add composite unique constraint for provider + provider_id to prevent duplicates
-- Drop first in case it exists
ALTER TABLE "user" DROP CONSTRAINT IF EXISTS uq_user_provider_provider_id;
ALTER TABLE "user" ADD CONSTRAINT uq_user_provider_provider_id 
    UNIQUE (provider, provider_id);

-- Add check constraint for valid providers
ALTER TABLE "user" DROP CONSTRAINT IF EXISTS ck_user_provider_valid;
ALTER TABLE "user" ADD CONSTRAINT ck_user_provider_valid 
    CHECK (provider IN ('email', 'google', 'linkedin'));

-- Add check constraint to ensure OAuth users have provider_id
ALTER TABLE "user" DROP CONSTRAINT IF EXISTS ck_user_oauth_provider_id;
ALTER TABLE "user" ADD CONSTRAINT ck_user_oauth_provider_id 
    CHECK ((provider = 'email' AND provider_id IS NULL) OR (provider != 'email' AND provider_id IS NOT NULL));

-- Add check constraint to ensure email users have password or OAuth users don't require it
ALTER TABLE "user" DROP CONSTRAINT IF EXISTS ck_user_auth_method;
ALTER TABLE "user" ADD CONSTRAINT ck_user_auth_method 
    CHECK ((provider = 'email' AND hashed_password IS NOT NULL) OR (provider != 'email'));

-- Add comments for documentation
COMMENT ON COLUMN "user".name IS 'User full name from OAuth provider or manual registration';
COMMENT ON COLUMN "user".avatar_url IS 'URL to user profile picture from OAuth provider';
COMMENT ON COLUMN "user".provider IS 'Authentication provider: email, google, linkedin';
COMMENT ON COLUMN "user".provider_id IS 'Unique user ID from OAuth provider';

COMMIT;