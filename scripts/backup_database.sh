#!/bin/bash
################################################################################
# PostgreSQL Automated Backup Script
#
# Purpose: Create daily backups of PostgreSQL database to prevent data loss
# Retention: Keeps last 7 days of backups
# Schedule: Run daily via cron (see setup instructions below)
#
# Setup Instructions:
#   1. Make script executable: chmod +x scripts/backup_database.sh
#   2. Add to crontab: crontab -e
#   3. Add line: 0 2 * * * /path/to/PratikoAi-BE/scripts/backup_database.sh >> /path/to/PratikoAi-BE/logs/backup.log 2>&1
#      (This runs at 2 AM daily)
#
# Manual Usage:
#   ./scripts/backup_database.sh
################################################################################

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_ROOT}/backups"
RETENTION_DAYS=7

# Database connection (from docker-compose.yml)
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5433}"
DB_NAME="${POSTGRES_DB:-aifinance}"
DB_USER="${POSTGRES_USER:-aifinance}"
DB_PASSWORD="${POSTGRES_PASSWORD:-devpass}"

# Timestamp for backup file
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/pratiko_backup_${TIMESTAMP}.sql.gz"
BACKUP_LATEST="${BACKUP_DIR}/pratiko_backup_latest.sql.gz"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

################################################################################
# Functions
################################################################################

log_info() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} INFO: $1"
}

log_warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} WARN: $1"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} ERROR: $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check if pg_dump is available
    if ! command -v pg_dump &> /dev/null; then
        log_error "pg_dump not found. Please install PostgreSQL client tools."
        exit 1
    fi

    # Check if gzip is available
    if ! command -v gzip &> /dev/null; then
        log_error "gzip not found. Please install gzip."
        exit 1
    fi

    log_info "Prerequisites check passed ✓"
}

create_backup_directory() {
    log_info "Creating backup directory if needed..."

    if [ ! -d "$BACKUP_DIR" ]; then
        mkdir -p "$BACKUP_DIR"
        log_info "Created backup directory: $BACKUP_DIR"
    else
        log_info "Backup directory exists: $BACKUP_DIR"
    fi
}

perform_backup() {
    log_info "Starting database backup..."
    log_info "Database: ${DB_NAME} on ${DB_HOST}:${DB_PORT}"
    log_info "Backup file: $BACKUP_FILE"

    # Export password for pg_dump
    export PGPASSWORD="$DB_PASSWORD"

    # Perform backup with compression
    if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        --format=plain --no-owner --no-acl --verbose 2>&1 | gzip > "$BACKUP_FILE"; then

        # Unset password
        unset PGPASSWORD

        # Check if backup file was created and has content
        if [ -s "$BACKUP_FILE" ]; then
            BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
            log_info "Backup completed successfully ✓"
            log_info "Backup size: $BACKUP_SIZE"

            # Create symlink to latest backup
            ln -sf "$(basename "$BACKUP_FILE")" "$BACKUP_LATEST"
            log_info "Updated latest backup symlink ✓"

            return 0
        else
            log_error "Backup file created but is empty"
            rm -f "$BACKUP_FILE"
            return 1
        fi
    else
        unset PGPASSWORD
        log_error "Backup failed"
        rm -f "$BACKUP_FILE"
        return 1
    fi
}

cleanup_old_backups() {
    log_info "Cleaning up backups older than ${RETENTION_DAYS} days..."

    # Find and delete backups older than retention period
    DELETED_COUNT=$(find "$BACKUP_DIR" -name "pratiko_backup_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete -print | wc -l)

    if [ "$DELETED_COUNT" -gt 0 ]; then
        log_info "Deleted $DELETED_COUNT old backup(s) ✓"
    else
        log_info "No old backups to delete"
    fi

    # Show current backups
    CURRENT_BACKUPS=$(find "$BACKUP_DIR" -name "pratiko_backup_*.sql.gz" -type f | wc -l)
    log_info "Current backup count: $CURRENT_BACKUPS"
}

verify_backup() {
    log_info "Verifying backup integrity..."

    # Test if backup can be decompressed
    if gzip -t "$BACKUP_FILE" 2>/dev/null; then
        log_info "Backup integrity verified ✓"
        return 0
    else
        log_error "Backup verification failed - file is corrupted"
        return 1
    fi
}

send_notification() {
    local status=$1
    local message=$2

    # Optional: Send notification via Slack if webhook is configured
    if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
        curl -X POST "$SLACK_WEBHOOK_URL" \
            -H 'Content-Type: application/json' \
            -d "{\"text\": \"🗄️ Database Backup $status: $message\"}" \
            > /dev/null 2>&1 || true
    fi
}

################################################################################
# Main Execution
################################################################################

main() {
    log_info "=========================================="
    log_info "PostgreSQL Backup Script"
    log_info "=========================================="

    # Run backup steps
    check_prerequisites
    create_backup_directory

    if perform_backup; then
        if verify_backup; then
            cleanup_old_backups

            log_info "=========================================="
            log_info "Backup completed successfully!"
            log_info "=========================================="

            send_notification "Success" "Database backed up successfully"
            exit 0
        else
            log_error "Backup verification failed"
            send_notification "Failed" "Backup verification failed"
            exit 1
        fi
    else
        log_error "Backup process failed"
        send_notification "Failed" "Backup process failed"
        exit 1
    fi
}

# Run main function
main "$@"
