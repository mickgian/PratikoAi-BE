# Database Backup System

**Purpose**: Prevent data loss by maintaining automated daily backups of the PostgreSQL database.

**Created**: 2025-11-29 (in response to data loss incident)

---

## Overview

The PratikoAI backend includes an automated backup system that:
- ✅ Creates daily compressed PostgreSQL dumps
- ✅ Retains last 7 days of backups (configurable)
- ✅ Verifies backup integrity automatically
- ✅ Supports manual backup and restore operations
- ✅ Optional Slack notifications for backup status

---

## Quick Start

### 1. Manual Backup (Test)

```bash
# Run backup manually
./scripts/backup_database.sh

# Check backup was created
ls -lh backups/
```

### 2. Automated Daily Backups (Cron)

Add to crontab to run automatically at 2 AM daily:

```bash
# Edit crontab
crontab -e

# Add this line (adjust paths to match your installation):
0 2 * * * /path/to/PratikoAi-BE/scripts/backup_database.sh >> /path/to/PratikoAi-BE/logs/backup.log 2>&1
```

**Example** (if project is in `/home/user/PratikoAi-BE`):
```
0 2 * * * /home/user/PratikoAi-BE/scripts/backup_database.sh >> /home/user/PratikoAi-BE/logs/backup.log 2>&1
```

### 3. Restore from Backup

```bash
# Restore from latest backup
./scripts/restore_database.sh

# Restore from specific backup
./scripts/restore_database.sh backups/pratiko_backup_20251129_140000.sql.gz
```

⚠️ **WARNING**: Restore will DROP the existing database!

---

## Backup Configuration

### Default Settings

Located in `scripts/backup_database.sh`:

| Setting | Default | Description |
|---------|---------|-------------|
| `BACKUP_DIR` | `./backups/` | Directory where backups are stored |
| `RETENTION_DAYS` | `7` | Number of days to keep backups |
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5433` | PostgreSQL port (Docker container) |
| `DB_NAME` | `aifinance` | Database name |
| `DB_USER` | `aifinance` | Database user |
| `DB_PASSWORD` | `devpass` | Database password |

### Environment Variables

You can override defaults using environment variables:

```bash
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5433
export POSTGRES_DB=aifinance
export POSTGRES_USER=aifinance
export POSTGRES_PASSWORD=devpass

./scripts/backup_database.sh
```

### Slack Notifications (Optional)

To receive backup notifications in Slack:

```bash
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
./scripts/backup_database.sh
```

---

## Backup File Format

Backups are stored as compressed SQL dumps:

```
backups/
├── pratiko_backup_20251129_020000.sql.gz  # Timestamped backup
├── pratiko_backup_20251130_020000.sql.gz
├── pratiko_backup_20251201_020000.sql.gz
└── pratiko_backup_latest.sql.gz           # Symlink to latest backup
```

**Naming Convention**: `pratiko_backup_YYYYMMDD_HHMMSS.sql.gz`

**Compression**: gzip (typically 80-90% size reduction)

---

## Backup Verification

The backup script automatically verifies integrity:

1. Checks if backup file was created
2. Verifies file is not empty
3. Tests gzip decompression
4. Creates symlink to latest backup

If verification fails, the backup is deleted and an error is logged.

---

## Monitoring Backups

### Check Backup Status

```bash
# List all backups
ls -lh backups/

# View latest backup
ls -lh backups/pratiko_backup_latest.sql.gz

# Check backup log (if using cron)
tail -f logs/backup.log
```

### Verify Backup Count

```bash
# Should have 7 backups (if running daily for 7+ days)
ls backups/pratiko_backup_*.sql.gz | wc -l
```

---

## Disaster Recovery Procedure

### Scenario: Complete Data Loss

1. **Stop the application**:
   ```bash
   docker-compose down
   ```

2. **Restore from latest backup**:
   ```bash
   docker-compose up -d db redis  # Start database only
   ./scripts/restore_database.sh   # Restore from latest backup
   ```

3. **Run migrations** (if backup is old):
   ```bash
   alembic upgrade head
   ```

4. **Restart application**:
   ```bash
   docker-compose up -d
   ```

5. **Verify restoration**:
   ```bash
   # Check table counts
   psql "postgresql://aifinance:devpass@localhost:5433/aifinance" -c "\dt"

   # Check knowledge base
   psql "postgresql://aifinance:devpass@localhost:5433/aifinance" -c "SELECT COUNT(*) FROM knowledge_items;"
   ```

---

## Troubleshooting

### Backup Fails: "pg_dump not found"

**Solution**: Install PostgreSQL client tools:

```bash
# Ubuntu/Debian
sudo apt-get install postgresql-client

# macOS
brew install postgresql
```

### Backup Fails: Connection refused

**Solution**: Verify database is running and accessible:

```bash
docker-compose ps
psql "postgresql://aifinance:devpass@localhost:5433/aifinance" -c "\dt"
```

### Restore Fails: Database in use

**Solution**: The restore script automatically terminates connections. If it still fails:

```bash
# Stop application
docker-compose stop app

# Run restore again
./scripts/restore_database.sh
```

### Old Backups Not Being Deleted

**Solution**: Check retention setting in `scripts/backup_database.sh`:

```bash
RETENTION_DAYS=7  # Increase to keep more backups
```

---

## Best Practices

### 1. Test Backups Regularly

**Monthly Test Restore** (recommended):

```bash
# Restore to test database to verify backups work
DB_NAME=aifinance_test ./scripts/restore_database.sh
```

### 2. Monitor Backup Size

Large database growth might indicate issues:

```bash
# Check backup sizes
du -h backups/pratiko_backup_*.sql.gz
```

### 3. Offsite Backups

For production, copy backups to remote storage:

```bash
# Example: Sync to S3 (add to cron after backup)
aws s3 sync backups/ s3://my-bucket/pratikoai-backups/ \
  --exclude "*" --include "pratiko_backup_*.sql.gz"
```

### 4. Backup Before Migrations

```bash
# Before running alembic upgrade
./scripts/backup_database.sh

# If migration fails, restore
./scripts/restore_database.sh
```

---

## Security Considerations

### Backup File Permissions

Backups contain sensitive data. Ensure proper permissions:

```bash
# Restrict access to backups directory
chmod 700 backups/
chmod 600 backups/*.sql.gz
```

### Encryption (Optional)

For sensitive production data:

```bash
# Encrypt backup after creation
gpg --encrypt --recipient you@example.com backups/pratiko_backup_latest.sql.gz

# Decrypt when restoring
gpg --decrypt backups/pratiko_backup_latest.sql.gz.gpg | gunzip | psql ...
```

---

## Maintenance

### Changing Retention Period

Edit `scripts/backup_database.sh`:

```bash
# Keep backups for 30 days instead of 7
RETENTION_DAYS=30
```

### Backup Storage Locations

By default, backups are stored in `./backups/`. To change:

```bash
# Edit scripts/backup_database.sh
BACKUP_DIR="/mnt/backups/pratikoai"
```

### Manual Cleanup

```bash
# Delete backups older than 30 days
find backups/ -name "pratiko_backup_*.sql.gz" -type f -mtime +30 -delete
```

---

## Migration History

This backup system was created on **2025-11-29** in response to a data loss incident where:
- Docker volume was accidentally deleted
- All knowledge base data (31 documents, 128 chunks) was lost
- RSS feeds had to be re-ingested to restore data

**Lesson Learned**: Always maintain automated backups before any database work.

---

## Related Documentation

- [GDPR Data Deletion](GDPR_DATA_DELETION.md) - User data deletion procedures
- [Chat Storage Architecture](CHAT_STORAGE_ARCHITECTURE.md) - Chat history storage
- [Database Schema](../alembic/) - Migration history

---

**Last Updated**: 2025-11-29
