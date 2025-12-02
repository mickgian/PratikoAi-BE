"""Add Expert Feedback System tables for quality analysis and expert validation

Revision ID: 20251121_expert_feedback
Revises: 20251111_add_pub_date
Create Date: 2025-11-21

This migration creates tables for the Expert Feedback System (DEV-BE-72 + Task Automation):
1. expert_profiles - Expert user credentials, trust scores, and performance metrics
2. expert_feedback - Feedback from experts on AI-generated answers (with task automation fields)
3. expert_faq_candidates - FAQ candidates generated from expert feedback
4. expert_generated_tasks - Tracks tasks automatically created from expert feedback

TASK AUTOMATION FEATURE:
When experts mark responses as 'Incompleta' or 'Errata' and provide additional_details,
the system automatically creates development tasks in SUPER_USER_TASKS.md.

Fields in expert_feedback for task automation:
- additional_details: Expert's description of what needs to be fixed/implemented
- generated_task_id: The DEV-BE-XXX ID of the created task
- task_creation_attempted: Whether system tried to create a task
- task_creation_success: TRUE if task created, FALSE if failed, NULL if not attempted
- task_creation_error: Error message if task creation failed

CRITICAL NOTES:
- User table is named "user" (singular), not "users"
- User.id is INTEGER, expert_profiles.user_id and expert_generated_tasks.expert_id are INTEGER
- ExpertProfile model expects UUID but database uses INTEGER (application handles conversion)

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "20251121_expert_feedback"
down_revision = "20251111_add_pub_date"
branch_labels = None
depends_on = None


def upgrade():
    """Create Expert Feedback System tables."""
    # Create PostgreSQL enum types for expert feedback system
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE feedback_type AS ENUM ('correct', 'incomplete', 'incorrect');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE italian_feedback_category AS ENUM (
                'normativa_obsoleta',
                'interpretazione_errata',
                'caso_mancante',
                'calcolo_sbagliato',
                'troppo_generico'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE expert_credential_type AS ENUM (
                'dottore_commercialista',
                'revisore_legale',
                'consulente_fiscale',
                'consulente_lavoro',
                'caf_operator'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # 1. Create expert_profiles table
    # NOTE: user_id is UUID but references user.id (INTEGER)
    # This is intentional for future-proofing when user table migrates to UUID
    op.execute("""
        CREATE TABLE IF NOT EXISTS expert_profiles (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id INTEGER NOT NULL UNIQUE REFERENCES "user"(id) ON DELETE CASCADE,

            -- Professional credentials
            credentials TEXT[] DEFAULT '{}',
            credential_types expert_credential_type[] DEFAULT '{}',
            experience_years INTEGER DEFAULT 0,
            specializations TEXT[] DEFAULT '{}',

            -- Performance metrics
            feedback_count INTEGER DEFAULT 0,
            feedback_accuracy_rate DOUBLE PRECISION DEFAULT 0.0,
            average_response_time_seconds INTEGER DEFAULT 0,
            trust_score DOUBLE PRECISION DEFAULT 0.5,

            -- Professional information
            professional_registration_number VARCHAR(50),
            organization VARCHAR(200),
            location_city VARCHAR(100),

            -- Status and verification
            is_verified BOOLEAN DEFAULT FALSE,
            verification_date TIMESTAMPTZ,
            is_active BOOLEAN DEFAULT TRUE,

            -- Metadata
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),

            -- Constraints
            CONSTRAINT trust_score_range CHECK (trust_score >= 0.0 AND trust_score <= 1.0),
            CONSTRAINT accuracy_rate_range CHECK (feedback_accuracy_rate >= 0.0 AND feedback_accuracy_rate <= 1.0),
            CONSTRAINT non_negative_experience CHECK (experience_years >= 0),
            CONSTRAINT non_negative_feedback_count CHECK (feedback_count >= 0)
        );
    """)

    # Create indexes for expert_profiles
    op.execute("CREATE INDEX IF NOT EXISTS idx_expert_profiles_trust_score ON expert_profiles(trust_score);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_expert_profiles_active ON expert_profiles(is_active, is_verified);")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_expert_profiles_specializations ON expert_profiles USING GIN(specializations);"
    )

    # 2. Create expert_feedback table
    op.execute("""
        CREATE TABLE IF NOT EXISTS expert_feedback (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            query_id UUID NOT NULL,
            expert_id UUID NOT NULL REFERENCES expert_profiles(id) ON DELETE CASCADE,

            -- Feedback details
            feedback_type feedback_type NOT NULL,
            category italian_feedback_category,

            -- Original content
            query_text TEXT NOT NULL,
            original_answer TEXT NOT NULL,

            -- Expert input
            expert_answer TEXT,
            improvement_suggestions TEXT[] DEFAULT '{}',
            regulatory_references TEXT[] DEFAULT '{}',

            -- Quality metrics
            confidence_score DOUBLE PRECISION DEFAULT 0.0,
            time_spent_seconds INTEGER NOT NULL,
            complexity_rating INTEGER CHECK (complexity_rating >= 1 AND complexity_rating <= 5),

            -- Processing metadata
            processing_time_ms INTEGER,
            feedback_timestamp TIMESTAMPTZ DEFAULT NOW(),

            -- System response
            action_taken VARCHAR(100),
            improvement_applied BOOLEAN DEFAULT FALSE,

            -- Metadata
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),

            -- Constraints
            CONSTRAINT confidence_score_range CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
            CONSTRAINT positive_time_spent CHECK (time_spent_seconds > 0)
        );
    """)

    # Create indexes for expert_feedback
    op.execute("CREATE INDEX IF NOT EXISTS idx_expert_feedback_query_id ON expert_feedback(query_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_expert_feedback_expert_id ON expert_feedback(expert_id);")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_expert_feedback_type_category ON expert_feedback(feedback_type, category);"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_expert_feedback_timestamp ON expert_feedback(feedback_timestamp DESC);")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_expert_feedback_improvement_applied ON expert_feedback(improvement_applied) WHERE improvement_applied = FALSE;"
    )

    # 3. Create expert_faq_candidates table (different from faq_automation.FAQCandidate)
    # This table stores FAQ candidates specifically from expert feedback
    op.execute("""
        CREATE TABLE IF NOT EXISTS expert_faq_candidates (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            question TEXT NOT NULL,
            answer TEXT NOT NULL,

            -- Source information
            source VARCHAR(20) NOT NULL DEFAULT 'expert_feedback' CHECK (source IN ('expert_feedback', 'auto_generated')),
            expert_id UUID REFERENCES expert_profiles(id) ON DELETE SET NULL,
            expert_trust_score DOUBLE PRECISION,

            -- Approval workflow
            approval_status VARCHAR(20) DEFAULT 'pending' CHECK (approval_status IN ('pending', 'approved', 'rejected')),
            approved_by INTEGER REFERENCES "user"(id) ON DELETE SET NULL,
            approved_at TIMESTAMPTZ,

            -- Classification
            suggested_category VARCHAR(100),
            suggested_tags TEXT[] DEFAULT '{}',
            regulatory_references TEXT[] DEFAULT '{}',

            -- Business metrics
            frequency INTEGER DEFAULT 0,
            estimated_monthly_savings NUMERIC(10, 2) DEFAULT 0,
            roi_score NUMERIC(10, 2) DEFAULT 0,
            priority_score NUMERIC(10, 2) DEFAULT 0,

            -- Metadata
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),

            -- Constraints
            CONSTRAINT non_negative_frequency CHECK (frequency >= 0),
            CONSTRAINT non_negative_savings CHECK (estimated_monthly_savings >= 0)
        );
    """)

    # Create indexes for expert_faq_candidates
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_expert_faq_candidates_status ON expert_faq_candidates(approval_status, created_at DESC);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_expert_faq_candidates_priority ON expert_faq_candidates(priority_score DESC, approval_status);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_expert_faq_candidates_expert ON expert_faq_candidates(expert_id, expert_trust_score DESC);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_expert_faq_candidates_category ON expert_faq_candidates(suggested_category);"
    )

    # 4. Add task automation fields to expert_feedback table
    op.execute("""
        ALTER TABLE expert_feedback
        ADD COLUMN IF NOT EXISTS additional_details TEXT,
        ADD COLUMN IF NOT EXISTS generated_task_id VARCHAR(50),
        ADD COLUMN IF NOT EXISTS task_creation_attempted BOOLEAN DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS task_creation_success BOOLEAN,
        ADD COLUMN IF NOT EXISTS task_creation_error TEXT;
    """)

    # Create index on generated_task_id for lookups
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_expert_feedback_task_id ON expert_feedback(generated_task_id) WHERE generated_task_id IS NOT NULL;"
    )

    # 5. Create expert_generated_tasks table for tracking automatically created tasks
    op.execute("""
        CREATE TABLE IF NOT EXISTS expert_generated_tasks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            task_id VARCHAR(50) UNIQUE NOT NULL,
            task_name VARCHAR(50) NOT NULL,
            feedback_id UUID NOT NULL REFERENCES expert_feedback(id) ON DELETE CASCADE,
            expert_id UUID NOT NULL REFERENCES expert_profiles(id),
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            additional_details TEXT NOT NULL,
            file_path VARCHAR(200) DEFAULT 'SUPER_USER_TASKS.md',
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)

    # Create indexes for expert_generated_tasks
    op.execute("CREATE INDEX IF NOT EXISTS idx_egt_created_at ON expert_generated_tasks(created_at DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_egt_task_id ON expert_generated_tasks(task_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_egt_feedback_id ON expert_generated_tasks(feedback_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_egt_expert_id ON expert_generated_tasks(expert_id);")

    # Create trigger to update updated_at timestamp
    op.execute("""
        CREATE OR REPLACE FUNCTION update_expert_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER trigger_expert_profiles_updated_at
        BEFORE UPDATE ON expert_profiles
        FOR EACH ROW
        EXECUTE FUNCTION update_expert_updated_at();
    """)

    op.execute("""
        CREATE TRIGGER trigger_expert_feedback_updated_at
        BEFORE UPDATE ON expert_feedback
        FOR EACH ROW
        EXECUTE FUNCTION update_expert_updated_at();
    """)

    op.execute("""
        CREATE TRIGGER trigger_expert_faq_candidates_updated_at
        BEFORE UPDATE ON expert_faq_candidates
        FOR EACH ROW
        EXECUTE FUNCTION update_expert_updated_at();
    """)

    print("✅ Created Expert Feedback System tables:")
    print("   - expert_profiles (with trust scoring)")
    print("   - expert_feedback (with quality metrics + task automation fields)")
    print("   - expert_faq_candidates (auto-approval workflow)")
    print("   - expert_generated_tasks (tracks auto-generated development tasks)")
    print("   - PostgreSQL enum types (feedback_type, italian_feedback_category, expert_credential_type)")
    print("   - All indexes and constraints")
    print("   - Updated_at triggers")
    print("")
    print("✅ Task Automation Fields Added to expert_feedback:")
    print("   - additional_details: Expert's fix description")
    print("   - generated_task_id: DEV-BE-XXX task ID")
    print("   - task_creation_attempted: Whether task creation was tried")
    print("   - task_creation_success: Success status of task creation")
    print("   - task_creation_error: Error message if failed")


def downgrade():
    """Remove Expert Feedback System tables."""
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS trigger_expert_faq_candidates_updated_at ON expert_faq_candidates;")
    op.execute("DROP TRIGGER IF EXISTS trigger_expert_feedback_updated_at ON expert_feedback;")
    op.execute("DROP TRIGGER IF EXISTS trigger_expert_profiles_updated_at ON expert_profiles;")
    op.execute("DROP FUNCTION IF EXISTS update_expert_updated_at();")

    # Drop tables (in reverse order of dependencies)
    op.execute("DROP TABLE IF EXISTS expert_generated_tasks CASCADE;")
    op.execute("DROP TABLE IF EXISTS expert_faq_candidates CASCADE;")

    # Drop task automation columns from expert_feedback before dropping the table
    op.execute("""
        ALTER TABLE expert_feedback
        DROP COLUMN IF EXISTS task_creation_error,
        DROP COLUMN IF EXISTS task_creation_success,
        DROP COLUMN IF EXISTS task_creation_attempted,
        DROP COLUMN IF EXISTS generated_task_id,
        DROP COLUMN IF EXISTS additional_details;
    """)

    op.execute("DROP TABLE IF EXISTS expert_feedback CASCADE;")
    op.execute("DROP TABLE IF EXISTS expert_profiles CASCADE;")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS expert_credential_type CASCADE;")
    op.execute("DROP TYPE IF EXISTS italian_feedback_category CASCADE;")
    op.execute("DROP TYPE IF EXISTS feedback_type CASCADE;")

    print("✅ Removed Expert Feedback System tables, task automation fields, and enum types")
