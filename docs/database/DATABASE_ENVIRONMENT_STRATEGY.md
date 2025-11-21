# Database Environment Strategy Guide

**Last Updated:** 2025-11-20
**Target Audience:** Developers (Technical but not database-expert level)
**Status:** Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Understanding the Database Architecture](#understanding-the-database-architecture)
3. [Environment Strategy at a Glance](#environment-strategy-at-a-glance)
4. [Development Environment](#development-environment-dev)
5. [QA Environment](#qa-environment-formerly-staging)
6. [Preprod Environment](#preprod-environment)
7. [Production Environment](#production-environment)
8. [Schema Consistency & Migrations](#schema-consistency--migrations)
9. [Data Strategy by Environment](#data-strategy-by-environment)
10. [Backup & Recovery Strategy](#backup--recovery-strategy)
11. [pgvector Index Management](#pgvector-index-management)
12. [Security Considerations](#security-considerations)
13. [Common Workflows](#common-workflows)
14. [Troubleshooting](#troubleshooting)
15. [Quick Reference](#quick-reference)

---

## Overview

PratikoAI uses **PostgreSQL 15+ with pgvector** for all database operations. Think of the database like your app's local storage on Android - it needs to work reliably in development, staging, and production, but each environment has different requirements.

### Why This Matters

Just like you wouldn't test Android app updates directly on users' phones, we don't test database changes directly in production. This guide shows you how to safely manage database changes across environments.

### Key Technologies

- **PostgreSQL 15+** - The database engine (like SQLite on Android, but more powerful)
- **pgvector extension** - Enables vector similarity search (think of it like a special index for AI embeddings)
- **Alembic** - Database migration tool (like database versioning/Git for schema changes)
- **Docker** - Containerization (makes PostgreSQL setup identical everywhere)

---

## Understanding the Database Architecture

### The Mobile App Analogy

Think of the database architecture like an Android app with different build variants:

| Mobile Development | PratikoAI Database |
|-------------------|-------------------|
| **Debug build** on emulator | **Development** - Local PostgreSQL in Docker |
| **Staging build** on test devices | **QA** - Shared database for testing |
| **Beta build** for limited users | **Preprod** - Production-like environment |
| **Production build** on Play Store | **Production** - Live user data |

### Current Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     PratikoAI Database                      │
│                 PostgreSQL 15+ + pgvector                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Core Tables:                                               │
│  ├── knowledge_items    (Document metadata)                │
│  ├── knowledge_chunks   (Text chunks + embeddings)         │
│  ├── conversations      (User chat sessions)               │
│  ├── messages          (Individual messages)               │
│  ├── users             (User accounts)                     │
│  └── feed_status       (RSS feed monitoring)               │
│                                                             │
│  Indexes:                                                   │
│  ├── GIN (Full-Text Search)    - Italian FTS              │
│  ├── IVFFlat (Vector Search)   - 1536-dim embeddings      │
│  └── B-tree (Standard)         - Primary keys, FK         │
│                                                             │
│  Extensions:                                                │
│  ├── pgvector (vector search)                              │
│  └── unaccent (Italian text normalization)                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Why PostgreSQL + pgvector?

**Think of it like choosing between local storage vs cloud storage:**

- **Local option (PostgreSQL + pgvector):** Everything in one place, simpler to manage
- **Cloud option (PostgreSQL + Pinecone):** Split between two services, more complex

We chose the local option because:
1. **Scale fits** - Our data (up to 500K vectors) fits comfortably in pgvector's sweet spot
2. **Italian language** - PostgreSQL has built-in Italian dictionary for text search
3. **Simpler** - One database instead of two services to manage
4. **Cost** - No extra $150-330/month for external vector DB

---

## Environment Strategy at a Glance

### The Four Environments

| Environment | Purpose | Data Type | Backup Needed? | Schema Match? | Accessibility |
|-------------|---------|-----------|----------------|---------------|---------------|
| **Development** | Local development, rapid iteration | Test/fake data | No | Yes (via migrations) | Developer's laptop only |
| **QA** | Feature testing, integration tests | Production-like data | Yes (daily) | Yes (same as prod) | Dev team + QA team |
| **Preprod** | Final production simulation | Sanitized production clone | Yes (daily) | Yes (exact prod mirror) | Ops team only |
| **Production** | Live user data | Real user data | **YES (hourly)** | Source of truth | Public (via API) |

### The Golden Rule

**Schema is ALWAYS the same across all environments** (enforced by Alembic migrations).
**Data varies** by environment (test data in Dev/QA, real data in Production).

**Why?** Like Android app builds - the code structure (schema) is identical, but the data (user preferences, local storage) differs.

---

## Development Environment (Dev)

### Purpose

Your local playground for rapid iteration. Like running an Android app on an emulator - fast, isolated, no risk to real users.

### Setup

**Using Docker (Recommended):**

```bash
# Start PostgreSQL + Redis locally
docker-compose up -d postgres redis

# Verify it's running
docker-compose ps
```

**Database URL:**
```
postgresql+asyncpg://aifinance:devpass@localhost:5433/aifinance
```

### Key Characteristics

| Aspect | Configuration | Why |
|--------|--------------|-----|
| **Data** | Fake/test data only | Safe to delete, reset anytime |
| **Backups** | Not needed | Data is disposable, can regenerate |
| **Schema** | Matches production | Same migrations as prod |
| **Performance** | Debug mode enabled | Slower but more logging |
| **Access** | Local only (localhost) | Isolated to your machine |
| **SSL** | Not required | Local traffic only |
| **Logging** | Verbose (DEBUG level) | Helps debug issues |

### Data Management

**Reset Database (Nuclear Option):**
```bash
# Delete all data and start fresh
docker-compose down -v  # Removes volumes (data)
docker-compose up -d postgres

# Re-run migrations
alembic upgrade head

# Optionally: Load test fixtures
python scripts/load_test_data.py
```

**Load Test Data:**
```bash
# Ingest 3 sample RSS documents
python scripts/diag/ingest_smoke.py

# Test hybrid retrieval
python scripts/diag/retrieval_smoke.py
```

### When to Reset

- Schema migration goes wrong (stuck in broken state)
- Testing data import from scratch
- Performance testing (need clean baseline)
- After major schema changes (to verify migrations work)

### Backups

**Short answer:** Not needed.

**Why?** Like clearing an Android emulator's data - you can always recreate it. Your schema is in Git (Alembic migrations), and test data can be regenerated.

**Exception:** If you've spent hours creating a complex test dataset, consider exporting it:
```bash
# Export test data (optional)
pg_dump -h localhost -p 5433 -U aifinance -d aifinance \
  --data-only --table=knowledge_items --table=knowledge_chunks \
  > dev_test_data.sql

# Restore later
psql -h localhost -p 5433 -U aifinance -d aifinance < dev_test_data.sql
```

---

## QA Environment (Formerly Staging)

### Purpose

Shared environment for feature testing and integration validation. Like a shared Android test device - multiple devs test features before production deployment.

### Setup

**Database Configuration:**
```bash
# .env.qa
APP_ENV=qa
POSTGRES_URL=postgresql+asyncpg://username:password@qa-db-host:5432/pratikoai_qa
LOG_LEVEL=INFO
DEBUG=false
```

### Key Characteristics

| Aspect | Configuration | Why |
|--------|--------------|-----|
| **Data** | Production-like (sanitized) | Realistic testing without real user data |
| **Backups** | Daily (automated) | Can restore if tests corrupt data |
| **Schema** | Matches production | Same migrations as prod |
| **Performance** | Production-like | Test performance under realistic load |
| **Access** | Dev team + QA team | Shared for collaboration |
| **SSL** | Optional | Depends on network setup |
| **Logging** | Moderate (INFO level) | Balance debugging vs noise |

### Data Management

**QA Data Strategy:**

1. **Start with production clone (sanitized):**
   ```bash
   # On production (or preprod)
   pg_dump -h prod-db-host -U pratikoai_prod -d pratikoai_prod \
     --exclude-table=users --exclude-table=conversations --exclude-table=messages \
     > prod_knowledge_base.sql

   # On QA
   psql -h qa-db-host -U pratikoai_qa -d pratikoai_qa < prod_knowledge_base.sql
   ```

2. **Add test users:**
   ```bash
   # Create test users for QA team
   python scripts/create_test_users.py --env qa
   ```

3. **Sanitize sensitive data:**
   ```sql
   -- Remove any accidentally copied user data
   DELETE FROM conversations;
   DELETE FROM messages;
   UPDATE users SET email = 'testuser' || id || '@pratikoai-qa.com';
   ```

**Why production-like data?**
- Tests realistic search queries (real Italian regulatory documents)
- Tests vector search with actual embedding distribution
- Tests FTS with real Italian text patterns

**What's different from production?**
- No real user PII (personally identifiable information)
- Test user accounts instead of real users
- Can reset without affecting real users

### Backups

**Frequency:** Daily (automated)

**Retention:** 7 days

**Why daily?** QA is a shared environment. If someone's test corrupts the data, you can restore yesterday's backup and continue testing.

**Backup script:**
```bash
#!/bin/bash
# scripts/backup_qa.sh

BACKUP_DIR="/backups/qa"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/qa_backup_$TIMESTAMP.sql.gz"

# Create backup
pg_dump -h qa-db-host -U pratikoai_qa -d pratikoai_qa | gzip > $BACKUP_FILE

# Keep only last 7 days
find $BACKUP_DIR -name "qa_backup_*.sql.gz" -mtime +7 -delete

echo "QA backup completed: $BACKUP_FILE"
```

**Restore:**
```bash
# Find latest backup
ls -lt /backups/qa/qa_backup_*.sql.gz | head -1

# Restore (drops existing data!)
gunzip -c /backups/qa/qa_backup_20251120_080000.sql.gz | \
  psql -h qa-db-host -U pratikoai_qa -d pratikoai_qa
```

---

## Preprod Environment

### Purpose

**Production dress rehearsal.** Like beta testing an Android app with a small group - final validation before full release. Preprod **mirrors production exactly** (same config, same security, same performance settings).

### Setup

**Database Configuration:**
```bash
# .env.preprod
APP_ENV=preprod
POSTGRES_URL=postgresql+asyncpg://username:password@preprod-db-host:5432/pratikoai_preprod?ssl=require
LOG_LEVEL=WARNING  # Same as production
DEBUG=false
SSL_REDIRECT=true  # Same as production
```

### Key Characteristics

| Aspect | Configuration | Why |
|--------|--------------|-----|
| **Data** | Production clone (sanitized) | Exact production scenario testing |
| **Backups** | Daily (automated) | Same backup strategy as prod |
| **Schema** | **EXACT** production match | Final schema validation |
| **Performance** | Production settings | Test performance tuning |
| **Access** | Ops team only | Restricted like production |
| **SSL** | **Required** (same as prod) | Test SSL certificate setup |
| **Logging** | Minimal (WARNING level) | Same as production |

### Data Management

**Preprod Data = Sanitized Production Clone**

**Why?** Test the exact database size, index performance, and query patterns you'll see in production.

**Clone Process:**
```bash
# 1. On production (during low-traffic window)
pg_dump -h prod-db-host -U pratikoai_prod -d pratikoai_prod \
  --exclude-table-data=conversations \
  --exclude-table-data=messages \
  --exclude-table-data=users \
  > prod_clone_knowledge_base.sql

# 2. Export anonymized users (for testing login)
pg_dump -h prod-db-host -U pratikoai_prod -d pratikoai_prod \
  --table=users --data-only | \
  sed 's/@/@preprod-/g' > prod_users_sanitized.sql

# 3. Restore to preprod
psql -h preprod-db-host -U pratikoai_preprod -d pratikoai_preprod < prod_clone_knowledge_base.sql
psql -h preprod-db-host -U pratikoai_preprod -d pratikoai_preprod < prod_users_sanitized.sql
```

**Sanitization Rules:**
- **Keep:** knowledge_items, knowledge_chunks, feed_status (entire knowledge base)
- **Sanitize:** users (change emails to @preprod-pratikoai.com)
- **Delete:** conversations, messages (user chat history contains PII)

### Backups

**Frequency:** Daily (same as production)

**Retention:** 30 days (same as production)

**Why?** Preprod is the final gate before production. If a migration breaks preprod, you need to restore and retry.

---

## Production Environment

### Purpose

**Live user data.** Like the Play Store production build - this is the real deal. Maximum security, reliability, and backup protection.

### Setup

**Database Configuration:**
```bash
# .env.production
ENVIRONMENT=production
POSTGRES_URL=postgresql+asyncpg://username:password@prod-db-host:5432/pratikoai_prod?ssl=require
LOG_LEVEL=WARNING
DEBUG=false
BACKUP_ENABLED=true
SSL_REDIRECT=true
```

### Key Characteristics

| Aspect | Configuration | Why |
|--------|--------------|-----|
| **Data** | **LIVE USER DATA** | Real users, real revenue |
| **Backups** | **Hourly** (automated) | Minimize data loss (max 1 hour) |
| **Schema** | Source of truth | All envs follow production schema |
| **Performance** | Optimized | Fast response for users |
| **Access** | Public (via API) | Internet-facing |
| **SSL** | **REQUIRED** | Encrypt data in transit |
| **Logging** | Minimal (WARNING only) | Reduce noise, focus on errors |

### Backups

**Critical:** Production backups are **mandatory** and **automated**.

**Backup Schedule:**

| Frequency | Retention | Purpose |
|-----------|-----------|---------|
| **Hourly** | 24 hours | Quick recovery from recent issues |
| **Daily** | 30 days | Monthly historical recovery |
| **Weekly** | 90 days | Quarterly historical recovery |
| **Monthly** | 1 year | Long-term compliance/audit |

**Backup Script (Automated):**
```bash
#!/bin/bash
# scripts/backup_production.sh
# Runs via cron: 0 * * * * (every hour)

BACKUP_DIR="/backups/production"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
HOUR=$(date +%H)
DAY=$(date +%d)

# Hourly backup (24-hour retention)
HOURLY_BACKUP="$BACKUP_DIR/hourly/prod_backup_$TIMESTAMP.sql.gz"
mkdir -p "$BACKUP_DIR/hourly"
pg_dump -h prod-db-host -U pratikoai_prod -d pratikoai_prod | gzip > $HOURLY_BACKUP
find "$BACKUP_DIR/hourly" -name "prod_backup_*.sql.gz" -mtime +1 -delete

# Daily backup at midnight (30-day retention)
if [ "$HOUR" = "00" ]; then
  DAILY_BACKUP="$BACKUP_DIR/daily/prod_backup_$TIMESTAMP.sql.gz"
  mkdir -p "$BACKUP_DIR/daily"
  cp $HOURLY_BACKUP $DAILY_BACKUP
  find "$BACKUP_DIR/daily" -name "prod_backup_*.sql.gz" -mtime +30 -delete
fi

# Weekly backup on Sundays at midnight (90-day retention)
if [ "$HOUR" = "00" ] && [ "$(date +%u)" = "7" ]; then
  WEEKLY_BACKUP="$BACKUP_DIR/weekly/prod_backup_$TIMESTAMP.sql.gz"
  mkdir -p "$BACKUP_DIR/weekly"
  cp $HOURLY_BACKUP $WEEKLY_BACKUP
  find "$BACKUP_DIR/weekly" -name "prod_backup_*.sql.gz" -mtime +90 -delete
fi

# Monthly backup on 1st of month at midnight (1-year retention)
if [ "$HOUR" = "00" ] && [ "$DAY" = "01" ]; then
  MONTHLY_BACKUP="$BACKUP_DIR/monthly/prod_backup_$TIMESTAMP.sql.gz"
  mkdir -p "$BACKUP_DIR/monthly"
  cp $HOURLY_BACKUP $MONTHLY_BACKUP
  find "$BACKUP_DIR/monthly" -name "prod_backup_*.sql.gz" -mtime +365 -delete
fi

echo "Production backup completed: $HOURLY_BACKUP"
```

**Cron Setup:**
```bash
# Edit crontab
crontab -e

# Add hourly backup
0 * * * * /path/to/scripts/backup_production.sh >> /var/log/backup_production.log 2>&1
```

**Backup Verification:**
```bash
# Test restore (on preprod, NOT production!)
gunzip -c /backups/production/hourly/prod_backup_20251120_080000.sql.gz | \
  psql -h preprod-db-host -U pratikoai_preprod -d pratikoai_preprod
```

### Disaster Recovery

**Scenario: Production database corrupted**

**Recovery Time Objective (RTO):** 15 minutes
**Recovery Point Objective (RPO):** 1 hour (max data loss)

**Recovery Steps:**

1. **Identify latest valid backup:**
   ```bash
   ls -lt /backups/production/hourly/prod_backup_*.sql.gz | head -5
   ```

2. **Create new database instance (if needed):**
   ```bash
   createdb -h prod-db-host -U postgres pratikoai_prod_restored
   ```

3. **Restore backup:**
   ```bash
   gunzip -c /backups/production/hourly/prod_backup_20251120_140000.sql.gz | \
     psql -h prod-db-host -U pratikoai_prod -d pratikoai_prod_restored
   ```

4. **Verify restore:**
   ```bash
   psql -h prod-db-host -U pratikoai_prod -d pratikoai_prod_restored -c "SELECT COUNT(*) FROM knowledge_chunks;"
   psql -h prod-db-host -U pratikoai_prod -d pratikoai_prod_restored -c "SELECT COUNT(*) FROM users;"
   ```

5. **Switch application to restored database:**
   ```bash
   # Update .env.production
   POSTGRES_URL=postgresql+asyncpg://username:password@prod-db-host:5432/pratikoai_prod_restored?ssl=require

   # Restart application
   docker-compose restart app
   ```

6. **Monitor for issues:**
   ```bash
   # Check logs
   docker-compose logs -f app

   # Check database performance
   psql -h prod-db-host -U pratikoai_prod -d pratikoai_prod_restored -c "SELECT * FROM pg_stat_activity;"
   ```

---

## Schema Consistency & Migrations

### The Golden Rule

**All environments MUST have identical schema** (table structure, columns, indexes, constraints).

**Why?** Like Android app builds - the code (schema) is the same everywhere, only the data differs.

### How Alembic Enforces Consistency

Think of Alembic like Git for database schema:
- Each migration = one commit
- `alembic upgrade head` = pull latest changes
- `alembic downgrade` = revert to previous version

### Migration Workflow

**1. Developer creates schema change:**
```bash
# On development
alembic revision -m "add_publication_date_column"
```

**2. Edit migration file:**
```python
# alembic/versions/XXXX_add_publication_date_column.py

def upgrade():
    op.add_column('knowledge_items',
        sa.Column('publication_date', sa.Date(), nullable=True)
    )
    op.create_index('idx_ki_publication_date', 'knowledge_items', ['publication_date'])

def downgrade():
    op.drop_index('idx_ki_publication_date')
    op.drop_column('knowledge_items', 'publication_date')
```

**3. Test migration locally:**
```bash
# On development
alembic upgrade head  # Apply migration
alembic downgrade -1  # Test rollback
alembic upgrade head  # Re-apply
```

**4. Commit migration to Git:**
```bash
git add alembic/versions/XXXX_add_publication_date_column.py
git commit -m "Add publication_date column to knowledge_items"
git push
```

**5. Deploy to QA:**
```bash
# On QA server
git pull
alembic upgrade head
```

**6. Test on QA:**
```bash
# Verify schema change
psql -h qa-db-host -U pratikoai_qa -d pratikoai_qa -c "\d knowledge_items"
```

**7. Deploy to Preprod (production dress rehearsal):**
```bash
# On Preprod server
git pull
alembic upgrade head
```

**8. Final test on Preprod:**
```bash
# Verify migration works with production-like data
psql -h preprod-db-host -U pratikoai_preprod -d pratikoai_preprod -c "SELECT COUNT(*) FROM knowledge_items WHERE publication_date IS NOT NULL;"
```

**9. Deploy to Production:**
```bash
# On Production server (during low-traffic window)
git pull
alembic upgrade head
```

### Migration Safety Checklist

Before running migration on production:

- [ ] Migration tested on development
- [ ] Migration tested on QA
- [ ] Migration tested on preprod (with production-like data)
- [ ] Downgrade path tested (rollback plan)
- [ ] Backup created immediately before migration
- [ ] Low-traffic window scheduled (if migration is slow)
- [ ] Team notified (Slack/email)
- [ ] Rollback plan documented

### Common Migration Patterns

**Add column (safe):**
```python
def upgrade():
    op.add_column('knowledge_items', sa.Column('new_field', sa.Text(), nullable=True))
```

**Add index (potentially slow):**
```python
def upgrade():
    # Use CONCURRENTLY to avoid locking table (PostgreSQL only)
    op.execute("CREATE INDEX CONCURRENTLY idx_new_field ON knowledge_items(new_field);")
```

**Rename column (safe if done in two steps):**
```python
# Step 1: Add new column
def upgrade():
    op.add_column('knowledge_items', sa.Column('new_name', sa.Text(), nullable=True))
    op.execute("UPDATE knowledge_items SET new_name = old_name;")

# Step 2 (separate migration): Drop old column
def upgrade():
    op.drop_column('knowledge_items', 'old_name')
```

**Drop column (DANGEROUS - requires downtime):**
```python
def upgrade():
    # WARNING: This deletes data permanently!
    # Ensure column is unused in application before running
    op.drop_column('knowledge_items', 'unused_field')
```

---

## Data Strategy by Environment

### Summary Table

| Environment | Data Source | PII? | Reset Frequency | Purpose |
|-------------|-------------|------|----------------|---------|
| **Development** | Fake/generated | No | Anytime | Rapid iteration |
| **QA** | Production clone (sanitized) | No | Weekly | Feature testing |
| **Preprod** | Production clone (sanitized) | No | Before each prod deploy | Final validation |
| **Production** | Live users | **YES** | Never | Real users |

### What Data Should Be the Same?

**Knowledge base (SAME everywhere):**
- `knowledge_items` (Italian regulations, tax documents)
- `knowledge_chunks` (text chunks + embeddings)
- `feed_status` (RSS feed monitoring)

**Why?** Search quality depends on having realistic Italian regulatory text. Can't test search with fake data.

### What Data Should Be Different?

**User data (DIFFERENT per environment):**
- `users` - Test accounts in Dev/QA/Preprod, real users in Production
- `conversations` - Empty in Dev/QA/Preprod, real chats in Production
- `messages` - Empty in Dev/QA/Preprod, real messages in Production

**Why?** User data contains PII (personally identifiable information). GDPR compliance requires protecting PII.

### Data Refresh Strategy

**QA Environment (weekly refresh):**
```bash
#!/bin/bash
# scripts/refresh_qa_data.sh
# Runs weekly: Sunday at 2 AM

# 1. Clone knowledge base from production
pg_dump -h prod-db-host -U pratikoai_prod -d pratikoai_prod \
  --table=knowledge_items --table=knowledge_chunks --table=feed_status \
  > prod_knowledge_base.sql

# 2. Restore to QA (drops existing data)
psql -h qa-db-host -U pratikoai_qa -d pratikoai_qa < prod_knowledge_base.sql

# 3. Reset user data to test accounts
psql -h qa-db-host -U pratikoai_qa -d pratikoai_qa <<EOF
TRUNCATE conversations, messages CASCADE;
DELETE FROM users;
INSERT INTO users (email, hashed_password) VALUES
  ('qa_test1@pratikoai.com', 'hashed_password_1'),
  ('qa_test2@pratikoai.com', 'hashed_password_2');
EOF

echo "QA data refreshed from production knowledge base"
```

**Preprod Environment (before each production deployment):**
```bash
#!/bin/bash
# scripts/refresh_preprod_data.sh
# Runs on-demand before production deployment

# Full production clone (sanitized)
pg_dump -h prod-db-host -U pratikoai_prod -d pratikoai_prod > prod_full_clone.sql

# Restore to preprod
psql -h preprod-db-host -U pratikoai_preprod -d pratikoai_preprod < prod_full_clone.sql

# Sanitize user emails
psql -h preprod-db-host -U pratikoai_preprod -d pratikoai_preprod <<EOF
UPDATE users SET email = REPLACE(email, '@', '@preprod-');
TRUNCATE conversations, messages CASCADE;
EOF

echo "Preprod refreshed from production (sanitized)"
```

---

## Backup & Recovery Strategy

### Backup Requirements by Environment

| Environment | Frequency | Retention | Automated? | Tested? |
|-------------|-----------|-----------|------------|---------|
| **Development** | Never | N/A | No | N/A |
| **QA** | Daily | 7 days | Yes | Monthly |
| **Preprod** | Daily | 30 days | Yes | Weekly |
| **Production** | **Hourly** | 24h/30d/90d/1y | **Yes** | **Weekly** |

### Why Different Backup Strategies?

**Development:** No backups needed - data is disposable, schema is in Git.

**QA:** Daily backups - can restore if tests corrupt data, but 7 days is enough (data refreshes weekly anyway).

**Preprod:** Daily backups - mirrors production backup strategy for realistic testing.

**Production:** Hourly backups - **critical for business continuity**. Max 1 hour of data loss acceptable.

### Backup Testing

**Monthly QA Backup Test:**
```bash
# 1. Restore latest QA backup to temporary database
gunzip -c /backups/qa/qa_backup_20251120_020000.sql.gz | \
  psql -h qa-db-host -U pratikoai_qa -d qa_backup_test

# 2. Verify data integrity
psql -h qa-db-host -U pratikoai_qa -d qa_backup_test -c "SELECT COUNT(*) FROM knowledge_chunks;"

# 3. Cleanup
dropdb -h qa-db-host -U pratikoai_qa qa_backup_test
```

**Weekly Production Backup Test (on Preprod!):**
```bash
# NEVER test production backups on production database!
# Use preprod environment for testing

# 1. Restore latest production backup to preprod
gunzip -c /backups/production/daily/prod_backup_20251120_000000.sql.gz | \
  psql -h preprod-db-host -U pratikoai_preprod -d preprod_restore_test

# 2. Verify data integrity
psql -h preprod-db-host -U pratikoai_preprod -d preprod_restore_test <<EOF
SELECT COUNT(*) FROM knowledge_chunks;
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM feed_status;
EOF

# 3. Test application against restored database
# Update preprod .env to point to preprod_restore_test
# Restart app and run smoke tests

# 4. Cleanup
dropdb -h preprod-db-host -U pratikoai_preprod preprod_restore_test
```

### Backup Storage

**Local Backups (sufficient for QA/Preprod):**
```
/backups/
├── qa/
│   └── qa_backup_YYYYMMDD_HHMMSS.sql.gz
└── preprod/
    └── preprod_backup_YYYYMMDD_HHMMSS.sql.gz
```

**Production Backups (multiple locations):**
```
Primary: /backups/production/hourly/
Secondary: S3 bucket (offsite)
Tertiary: Glacier (long-term archive)
```

**Production Backup Replication:**
```bash
#!/bin/bash
# scripts/replicate_production_backup.sh
# Runs after each backup: 5 * * * * (5 minutes past each hour)

LATEST_BACKUP=$(ls -t /backups/production/hourly/prod_backup_*.sql.gz | head -1)

# Upload to S3 (offsite backup)
aws s3 cp $LATEST_BACKUP s3://pratikoai-backups/production/hourly/

# Monthly: Archive to Glacier (long-term storage)
if [ "$(date +%d)" = "01" ] && [ "$(date +%H)" = "00" ]; then
  MONTHLY_BACKUP=$(ls -t /backups/production/monthly/prod_backup_*.sql.gz | head -1)
  aws s3 cp $MONTHLY_BACKUP s3://pratikoai-backups/production/archive/ --storage-class GLACIER
fi
```

---

## pgvector Index Management

### What Are pgvector Indexes?

Think of pgvector indexes like a search index in Android - they speed up lookups but take space and time to build.

**Without index:** Database scans every embedding (slow, like linear search)
**With index:** Database uses index to jump to similar embeddings (fast, like HashMap lookup)

### Index Types

| Index Type | Recall | Speed | Build Time | When to Use |
|------------|--------|-------|------------|-------------|
| **IVFFlat** | 85-90% | Fast | 30-60 min | Current production (500K vectors) |
| **HNSW** | 90-95% | Faster | 2-4 hours | Future upgrade (DEV-BE-79) |

**Analogy:** IVFFlat is like a HashMap (fast, 90% accurate). HNSW is like a TreeMap (faster, 95% accurate, but takes longer to build).

### Current Index Configuration

```sql
-- Vector similarity index (IVFFlat)
CREATE INDEX idx_kc_embedding_ivfflat_1536
ON knowledge_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);  -- 100 clusters for 500K vectors
```

**Parameters:**
- `lists = 100` - Divides 500K vectors into 100 clusters (5K vectors per cluster)
- Rule of thumb: `lists = sqrt(total_vectors)` → sqrt(500K) ≈ 707, but 100 is fine for now

### Index Consistency Across Environments

**Schema (index structure):** SAME everywhere (enforced by Alembic migrations)
**Data (index contents):** Different per environment

**Why?** Index structure is schema (how it's built). Index contents is data (what it indexes).

### Index Rebuild Strategy

**When to rebuild:**
- After bulk data import (100K+ new vectors)
- After upgrading pgvector extension
- After changing index parameters (e.g., lists = 100 → lists = 200)
- If index becomes bloated (check `pg_relation_size`)

**How to rebuild (zero-downtime):**
```sql
-- 1. Create new index (CONCURRENTLY = no table lock)
CREATE INDEX CONCURRENTLY idx_kc_embedding_ivfflat_new
ON knowledge_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 2. Verify new index works (EXPLAIN should use new index)
EXPLAIN ANALYZE
SELECT * FROM knowledge_chunks
ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector
LIMIT 10;

-- 3. Drop old index (CONCURRENTLY = no table lock)
DROP INDEX CONCURRENTLY idx_kc_embedding_ivfflat_1536;

-- 4. Rename new index
ALTER INDEX idx_kc_embedding_ivfflat_new RENAME TO idx_kc_embedding_ivfflat_1536;
```

**Rebuild time estimates:**

| Environment | Vector Count | Build Time | Downtime? |
|-------------|-------------|------------|-----------|
| **Development** | ~1K | 1 minute | No (CONCURRENTLY) |
| **QA** | ~100K | 10-15 minutes | No (CONCURRENTLY) |
| **Preprod** | ~500K | 30-60 minutes | No (CONCURRENTLY) |
| **Production** | ~500K | 30-60 minutes | No (CONCURRENTLY) |

### Monitoring Index Health

**Check index size:**
```sql
SELECT
  schemaname,
  tablename,
  indexname,
  pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE indexname LIKE '%embedding%'
ORDER BY pg_relation_size(indexrelid) DESC;
```

**Check index usage:**
```sql
SELECT
  schemaname,
  tablename,
  indexname,
  idx_scan AS index_scans,
  idx_tup_read AS tuples_read,
  idx_tup_fetch AS tuples_fetched
FROM pg_stat_user_indexes
WHERE indexname LIKE '%embedding%';
```

**If `idx_scan = 0`:** Index is not being used (query planner ignores it, check EXPLAIN).

---

## Security Considerations

### Database Access Control

| Environment | Access Level | Who Has Access | Authentication |
|-------------|-------------|----------------|----------------|
| **Development** | Full (superuser) | Individual developer | Password (local only) |
| **QA** | Read/write | Dev team + QA team | Password (VPN) |
| **Preprod** | Read/write | Ops team | Password + 2FA |
| **Production** | Read/write (app), Read-only (humans) | Application (full), Ops team (read-only) | Password + 2FA + SSL |

### SSL/TLS Requirements

| Environment | SSL Required? | Certificate Type |
|-------------|---------------|------------------|
| **Development** | No | N/A (local traffic) |
| **QA** | Optional | Self-signed OK |
| **Preprod** | **Yes** | Valid certificate (mirrors prod) |
| **Production** | **Yes** | Valid certificate (Let's Encrypt or commercial) |

**Production SSL setup:**
```bash
# .env.production
POSTGRES_URL=postgresql+asyncpg://username:password@prod-db-host:5432/pratikoai_prod?ssl=require
```

**Test SSL connection:**
```bash
psql "postgresql://username:password@prod-db-host:5432/pratikoai_prod?sslmode=require"
# Should show: SSL connection (protocol: TLSv1.3, cipher: ...)
```

### Credential Management

**Development:**
```bash
# Hardcoded credentials OK (local only, no sensitive data)
POSTGRES_URL=postgresql+asyncpg://aifinance:devpass@localhost:5433/aifinance
```

**QA:**
```bash
# Shared credentials in .env.qa (not committed to Git)
POSTGRES_URL=postgresql+asyncpg://pratikoai_qa:qa_secure_password@qa-db-host:5432/pratikoai_qa
```

**Preprod/Production:**
```bash
# Use secrets manager (AWS Secrets Manager, Azure Key Vault, etc.)
# Never hardcode production credentials!

# Example: AWS Secrets Manager
export POSTGRES_URL=$(aws secretsmanager get-secret-value \
  --secret-id pratikoai/prod/database_url \
  --query SecretString --output text)
```

### PII (Personally Identifiable Information) Protection

**What is PII?**
- User emails
- Chat messages
- Conversation history
- Payment information

**PII Protection Rules:**

| Environment | PII Allowed? | Sanitization Required? |
|-------------|-------------|------------------------|
| **Development** | No | N/A (no PII ever) |
| **QA** | No | Yes (sanitize before import) |
| **Preprod** | No | Yes (sanitize before import) |
| **Production** | **Yes** | N/A (real user data) |

**Sanitization script:**
```python
# scripts/sanitize_user_data.py

import psycopg2

def sanitize_qa_data(db_url):
    """Sanitize user PII for QA environment"""
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    # Anonymize user emails
    cursor.execute("""
        UPDATE users
        SET email = 'testuser' || id || '@pratikoai-qa.com',
            phone = NULL,
            address = NULL
    """)

    # Delete conversation history (contains user messages)
    cursor.execute("TRUNCATE conversations, messages CASCADE")

    # Keep knowledge base (no PII)
    # knowledge_items, knowledge_chunks unchanged

    conn.commit()
    cursor.close()
    conn.close()
    print("QA data sanitized successfully")

if __name__ == "__main__":
    sanitize_qa_data("postgresql://pratikoai_qa:password@qa-db-host:5432/pratikoai_qa")
```

---

## Common Workflows

### Workflow 1: Deploy Schema Change to Production

**Scenario:** Add `publication_date` column to `knowledge_items` table.

**Steps:**

1. **Develop migration locally:**
   ```bash
   # On development
   alembic revision -m "add_publication_date_to_knowledge_items"
   # Edit alembic/versions/XXXX_add_publication_date_to_knowledge_items.py
   alembic upgrade head  # Test locally
   ```

2. **Commit to Git:**
   ```bash
   git add alembic/versions/XXXX_add_publication_date_to_knowledge_items.py
   git commit -m "Add publication_date column to knowledge_items"
   git push
   ```

3. **Deploy to QA:**
   ```bash
   # On QA server
   git pull
   alembic upgrade head
   # Verify: psql -h qa-db-host -U pratikoai_qa -d pratikoai_qa -c "\d knowledge_items"
   ```

4. **Test on QA:**
   ```bash
   # Run integration tests
   pytest tests/integration/test_knowledge_items.py
   ```

5. **Deploy to Preprod:**
   ```bash
   # On Preprod server
   git pull
   alembic upgrade head
   # Verify schema matches production expectations
   ```

6. **Schedule production deployment:**
   ```bash
   # During low-traffic window (e.g., 2 AM Sunday)
   # 1. Create backup
   pg_dump -h prod-db-host -U pratikoai_prod -d pratikoai_prod | gzip > prod_backup_pre_migration.sql.gz

   # 2. Run migration
   git pull
   alembic upgrade head

   # 3. Verify
   psql -h prod-db-host -U pratikoai_prod -d pratikoai_prod -c "\d knowledge_items"

   # 4. Monitor application logs
   docker-compose logs -f app
   ```

---

### Workflow 2: Refresh QA Data from Production

**Scenario:** QA data is 2 weeks old, need fresh production data for testing.

**Steps:**

1. **Export production knowledge base:**
   ```bash
   # On production (during low-traffic window)
   pg_dump -h prod-db-host -U pratikoai_prod -d pratikoai_prod \
     --table=knowledge_items --table=knowledge_chunks --table=feed_status \
     > prod_knowledge_base_20251120.sql
   ```

2. **Transfer to QA server:**
   ```bash
   scp prod_knowledge_base_20251120.sql qa-server:/tmp/
   ```

3. **Restore to QA:**
   ```bash
   # On QA server
   psql -h qa-db-host -U pratikoai_qa -d pratikoai_qa < /tmp/prod_knowledge_base_20251120.sql
   ```

4. **Reset user data:**
   ```bash
   python scripts/sanitize_user_data.py --env qa
   ```

5. **Verify QA environment:**
   ```bash
   # Check knowledge base size
   psql -h qa-db-host -U pratikoai_qa -d pratikoai_qa -c "SELECT COUNT(*) FROM knowledge_chunks;"

   # Check users are test accounts
   psql -h qa-db-host -U pratikoai_qa -d pratikoai_qa -c "SELECT email FROM users;"
   # Should show: testuser1@pratikoai-qa.com, testuser2@pratikoai-qa.com, etc.
   ```

---

### Workflow 3: Disaster Recovery (Production Database Corrupted)

**Scenario:** Production database corrupted at 3:00 PM. Need to restore.

**Steps:**

1. **Identify issue:**
   ```bash
   # Check application logs
   docker-compose logs app | grep -i error

   # Check database connectivity
   psql -h prod-db-host -U pratikoai_prod -d pratikoai_prod -c "SELECT 1;"
   ```

2. **Find latest valid backup:**
   ```bash
   # List recent hourly backups
   ls -lt /backups/production/hourly/prod_backup_*.sql.gz | head -5

   # Use backup from 2:00 PM (1 hour data loss acceptable)
   BACKUP_FILE="/backups/production/hourly/prod_backup_20251120_140000.sql.gz"
   ```

3. **Create new database instance:**
   ```bash
   createdb -h prod-db-host -U postgres pratikoai_prod_restored
   ```

4. **Restore backup:**
   ```bash
   gunzip -c $BACKUP_FILE | psql -h prod-db-host -U pratikoai_prod -d pratikoai_prod_restored
   ```

5. **Verify restored database:**
   ```bash
   psql -h prod-db-host -U pratikoai_prod -d pratikoai_prod_restored <<EOF
   SELECT COUNT(*) FROM knowledge_chunks;
   SELECT COUNT(*) FROM users;
   SELECT COUNT(*) FROM conversations;
   SELECT MAX(created_at) FROM messages;  -- Latest message timestamp
   EOF
   ```

6. **Switch application to restored database:**
   ```bash
   # Update .env.production
   POSTGRES_URL=postgresql+asyncpg://pratikoai_prod:password@prod-db-host:5432/pratikoai_prod_restored?ssl=require

   # Restart application
   docker-compose restart app
   ```

7. **Monitor for issues:**
   ```bash
   # Watch logs for errors
   docker-compose logs -f app

   # Check user reports
   # Notify users of 1-hour data loss (messages sent between 2:00 PM - 3:00 PM)
   ```

8. **Post-incident:**
   ```bash
   # Once stable, rename databases
   psql -h prod-db-host -U postgres <<EOF
   ALTER DATABASE pratikoai_prod RENAME TO pratikoai_prod_corrupted_backup;
   ALTER DATABASE pratikoai_prod_restored RENAME TO pratikoai_prod;
   EOF

   # Update .env.production back to original database name
   # Restart app
   # Delete corrupted backup after 30 days (keep for investigation)
   ```

**Total Recovery Time:** ~15 minutes
**Data Loss:** 1 hour (2:00 PM - 3:00 PM messages)

---

### Workflow 4: Upgrade pgvector Index (IVFFlat → HNSW)

**Scenario:** Upgrade from IVFFlat to HNSW for better recall (DEV-BE-79).

**Steps:**

1. **Verify pgvector version supports HNSW:**
   ```sql
   -- On development
   SELECT * FROM pg_available_extensions WHERE name = 'vector';
   -- Version must be ≥0.5.0 for HNSW
   ```

2. **Test HNSW on development:**
   ```sql
   -- Create HNSW index alongside IVFFlat
   CREATE INDEX CONCURRENTLY idx_kc_embedding_hnsw_test
   ON knowledge_chunks
   USING hnsw (embedding vector_cosine_ops)
   WITH (m = 16, ef_construction = 64);

   -- Compare query performance
   EXPLAIN ANALYZE
   SELECT * FROM knowledge_chunks
   ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector
   LIMIT 10;

   -- If HNSW faster + better recall, proceed
   ```

3. **Create Alembic migration:**
   ```python
   # alembic/versions/XXXX_upgrade_to_hnsw_index.py

   def upgrade():
       # Create HNSW index
       op.execute("""
           CREATE INDEX CONCURRENTLY idx_kc_embedding_hnsw_1536
           ON knowledge_chunks
           USING hnsw (embedding vector_cosine_ops)
           WITH (m = 16, ef_construction = 64);
       """)

       # Drop old IVFFlat index
       op.execute("DROP INDEX CONCURRENTLY idx_kc_embedding_ivfflat_1536;")

   def downgrade():
       # Recreate IVFFlat index
       op.execute("""
           CREATE INDEX CONCURRENTLY idx_kc_embedding_ivfflat_1536
           ON knowledge_chunks
           USING ivfflat (embedding vector_cosine_ops)
           WITH (lists = 100);
       """)

       # Drop HNSW index
       op.execute("DROP INDEX CONCURRENTLY idx_kc_embedding_hnsw_1536;")
   ```

4. **Test migration on QA:**
   ```bash
   # On QA server (500K vectors, 30-60 min build time)
   alembic upgrade head

   # Monitor index build progress
   psql -h qa-db-host -U pratikoai_qa -d pratikoai_qa <<EOF
   SELECT
     schemaname, tablename, indexname,
     pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
   FROM pg_stat_user_indexes
   WHERE indexname LIKE '%embedding%';
   EOF
   ```

5. **Benchmark QA performance:**
   ```bash
   # Run load tests with HNSW
   python scripts/load_test_vector_search.py --env qa

   # Compare to IVFFlat baseline
   # Expected: HNSW 20-30% faster, 5-10% better recall
   ```

6. **Deploy to Preprod:**
   ```bash
   # On Preprod server (production dress rehearsal)
   alembic upgrade head

   # Monitor for 24 hours
   # Check application logs for errors
   # Verify search quality with production-like queries
   ```

7. **Deploy to Production (during low-traffic window):**
   ```bash
   # On Production server (Sunday 2 AM)
   # 1. Create backup
   pg_dump -h prod-db-host -U pratikoai_prod -d pratikoai_prod | gzip > prod_backup_pre_hnsw.sql.gz

   # 2. Run migration (30-60 min)
   alembic upgrade head

   # 3. Monitor index build
   watch -n 10 "psql -h prod-db-host -U pratikoai_prod -d pratikoai_prod -c \"SELECT pg_size_pretty(pg_relation_size('idx_kc_embedding_hnsw_1536'));\""

   # 4. Verify HNSW index used
   psql -h prod-db-host -U pratikoai_prod -d pratikoai_prod <<EOF
   EXPLAIN ANALYZE
   SELECT * FROM knowledge_chunks
   ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector
   LIMIT 10;
   EOF
   # Should show: Index Scan using idx_kc_embedding_hnsw_1536
   ```

8. **Rollback plan (if issues):**
   ```bash
   # If HNSW causes problems, rollback to IVFFlat
   alembic downgrade -1

   # Or manually:
   psql -h prod-db-host -U pratikoai_prod -d pratikoai_prod <<EOF
   DROP INDEX CONCURRENTLY idx_kc_embedding_hnsw_1536;
   CREATE INDEX CONCURRENTLY idx_kc_embedding_ivfflat_1536
   ON knowledge_chunks
   USING ivfflat (embedding vector_cosine_ops)
   WITH (lists = 100);
   EOF
   ```

---

## Troubleshooting

### Issue: Migration Fails on QA but Works on Development

**Symptoms:**
```
alembic upgrade head
# ERROR: column "new_field" of relation "knowledge_items" already exists
```

**Cause:** QA database schema out of sync with migrations.

**Solution:**

1. **Check current migration version:**
   ```bash
   alembic current
   # Shows: abc123def456 (current migration)

   alembic history
   # Shows: all migrations
   ```

2. **Check actual database schema:**
   ```sql
   psql -h qa-db-host -U pratikoai_qa -d pratikoai_qa -c "\d knowledge_items"
   # Shows: actual columns in database
   ```

3. **Options:**

   **Option A: Mark migration as applied (if column already exists):**
   ```bash
   alembic stamp head  # Mark all migrations as applied (skips actual SQL)
   ```

   **Option B: Reset QA database and re-run migrations:**
   ```bash
   # Drop QA database (DANGEROUS - deletes all data)
   dropdb -h qa-db-host -U postgres pratikoai_qa
   createdb -h qa-db-host -U postgres pratikoai_qa

   # Re-run all migrations from scratch
   alembic upgrade head
   ```

   **Option C: Fix migration manually:**
   ```sql
   -- If migration adds column that already exists, modify migration:
   # Edit alembic/versions/XXXX_add_new_field.py

   def upgrade():
       # Add IF NOT EXISTS check
       op.execute("""
           ALTER TABLE knowledge_items
           ADD COLUMN IF NOT EXISTS new_field TEXT;
       """)
   ```

---

### Issue: pgvector Index Not Being Used

**Symptoms:**
```sql
EXPLAIN ANALYZE SELECT * FROM knowledge_chunks ORDER BY embedding <=> '[0.1, ...]'::vector LIMIT 10;
# Shows: Seq Scan (sequential scan, NOT index scan)
```

**Cause:** Query planner thinks sequential scan is faster than index scan.

**Solution:**

1. **Check index exists:**
   ```sql
   \d knowledge_chunks
   # Should show: idx_kc_embedding_ivfflat_1536 (ivfflat)
   ```

2. **Update table statistics:**
   ```sql
   ANALYZE knowledge_chunks;
   -- Re-run EXPLAIN ANALYZE
   ```

3. **Force index usage (testing only):**
   ```sql
   SET enable_seqscan = off;
   EXPLAIN ANALYZE SELECT * FROM knowledge_chunks ORDER BY embedding <=> '[0.1, ...]'::vector LIMIT 10;
   # Should now show: Index Scan

   SET enable_seqscan = on;  -- Re-enable after testing
   ```

4. **Check index is valid:**
   ```sql
   SELECT
     schemaname, tablename, indexname,
     idx_scan AS index_scans,
     pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
   FROM pg_stat_user_indexes
   WHERE indexname LIKE '%embedding%';

   -- If idx_scan = 0, index never used (problem)
   -- If index_size = 0, index not built (run REINDEX)
   ```

5. **Rebuild index:**
   ```sql
   REINDEX INDEX CONCURRENTLY idx_kc_embedding_ivfflat_1536;
   ```

---

### Issue: Backup Restore Fails with Foreign Key Errors

**Symptoms:**
```bash
psql -h qa-db-host -U pratikoai_qa -d pratikoai_qa < backup.sql
# ERROR: insert or update on table "knowledge_chunks" violates foreign key constraint "knowledge_chunks_knowledge_item_id_fkey"
```

**Cause:** Backup restores tables in wrong order (child tables before parent tables).

**Solution:**

1. **Disable foreign key checks during restore:**
   ```bash
   psql -h qa-db-host -U pratikoai_qa -d pratikoai_qa <<EOF
   SET session_replication_role = replica;  -- Disables triggers and FK checks
   \i backup.sql
   SET session_replication_role = default;  -- Re-enables checks
   EOF
   ```

2. **Or: Use pg_dump with correct options:**
   ```bash
   # Create backup with correct table order
   pg_dump -h prod-db-host -U pratikoai_prod -d pratikoai_prod \
     --section=pre-data \
     --section=data \
     --section=post-data \
     > backup_ordered.sql

   # Restore
   psql -h qa-db-host -U pratikoai_qa -d pratikoai_qa < backup_ordered.sql
   ```

---

### Issue: Production Database Running Out of Disk Space

**Symptoms:**
```
ERROR: could not extend file "base/16384/123456": No space left on device
```

**Immediate Solution:**

1. **Check disk usage:**
   ```bash
   df -h  # Check filesystem usage
   # /var/lib/postgresql/data: 95% full (CRITICAL)
   ```

2. **Find largest tables:**
   ```sql
   SELECT
     schemaname || '.' || tablename AS table_name,
     pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size
   FROM pg_tables
   WHERE schemaname = 'public'
   ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
   LIMIT 10;
   ```

3. **Quick fixes:**

   **Option A: Delete old backups:**
   ```bash
   # Delete backups older than 30 days
   find /backups/production/hourly -name "prod_backup_*.sql.gz" -mtime +30 -delete
   ```

   **Option B: Vacuum database:**
   ```sql
   VACUUM FULL ANALYZE;  -- Reclaims disk space (WARNING: locks tables)
   ```

   **Option C: Drop unused indexes:**
   ```sql
   -- Find unused indexes
   SELECT
     schemaname, tablename, indexname,
     idx_scan AS index_scans,
     pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
   FROM pg_stat_user_indexes
   WHERE idx_scan = 0  -- Never used
     AND pg_relation_size(indexrelid) > 100000000  -- >100MB
   ORDER BY pg_relation_size(indexrelid) DESC;

   -- Drop unused indexes (CAREFULLY!)
   DROP INDEX CONCURRENTLY idx_unused_index;
   ```

**Long-term Solution:**

1. **Increase disk size:**
   ```bash
   # AWS: Modify RDS instance storage
   # Hetzner: Resize volume
   ```

2. **Implement automated cleanup:**
   ```bash
   # scripts/cleanup_old_data.sh
   # Delete conversations older than 90 days
   psql -h prod-db-host -U pratikoai_prod -d pratikoai_prod <<EOF
   DELETE FROM messages WHERE created_at < NOW() - INTERVAL '90 days';
   DELETE FROM conversations WHERE created_at < NOW() - INTERVAL '90 days';
   VACUUM ANALYZE messages, conversations;
   EOF
   ```

3. **Monitor disk usage:**
   ```bash
   # Add to monitoring (Prometheus/Grafana)
   node_filesystem_avail_bytes{mountpoint="/var/lib/postgresql/data"}
   # Alert if <10% free space
   ```

---

## Quick Reference

### Environment URLs (Example)

| Environment | Database URL | Access |
|-------------|-------------|--------|
| **Development** | `localhost:5433` | Local only |
| **QA** | `qa-db.pratikoai.internal:5432` | VPN required |
| **Preprod** | `preprod-db.pratikoai.internal:5432` | VPN + 2FA |
| **Production** | `prod-db.pratikoai.com:5432` | SSL + 2FA |

### Common Commands

**Start local database:**
```bash
docker-compose up -d postgres redis
```

**Run migrations:**
```bash
alembic upgrade head
```

**Check migration status:**
```bash
alembic current  # Current version
alembic history  # All migrations
```

**Create backup:**
```bash
pg_dump -h HOST -U USER -d DATABASE | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

**Restore backup:**
```bash
gunzip -c backup_20251120_140000.sql.gz | psql -h HOST -U USER -d DATABASE
```

**Check database size:**
```sql
SELECT
  pg_size_pretty(pg_database_size('pratikoai_prod')) AS database_size,
  pg_size_pretty(pg_total_relation_size('knowledge_chunks')) AS chunks_table_size;
```

**Check index health:**
```sql
SELECT
  schemaname, tablename, indexname,
  idx_scan AS scans,
  pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC;
```

### Decision Matrix

**Need to reset database?**
- Dev: Yes, anytime (no backups needed)
- QA: Yes, with team notification (restore from backup if needed)
- Preprod: Rarely (only if testing disaster recovery)
- Production: **NEVER** (restore from backup only)

**Need to backup database?**
- Dev: No
- QA: Yes (daily, 7-day retention)
- Preprod: Yes (daily, 30-day retention)
- Production: **YES** (hourly, multi-tier retention)

**Need to sanitize data?**
- Dev: N/A (no PII ever)
- QA: Yes (before import from production)
- Preprod: Yes (before import from production)
- Production: No (real user data)

**Need SSL?**
- Dev: No
- QA: Optional
- Preprod: Yes (mirrors production)
- Production: **YES** (mandatory)

### Contact & Support

**Database issues:**
- Architect (@Egidio) - Schema design, architecture decisions
- Database Designer (@Primo) - Index optimization, query performance
- DevOps (@Dario) - Backup/restore, infrastructure

**Emergency (production database down):**
1. Check #architect-alerts Slack channel
2. Contact Ops team immediately
3. Follow disaster recovery workflow (see above)

---

## Document History

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2025-11-20 | 1.0 | Initial version | PratikoAI Database Designer (@Primo) |

---

**Last Updated:** 2025-11-20
**Maintained By:** PratikoAI Database Designer (@Primo)
**Review Frequency:** Quarterly (or after major schema changes)