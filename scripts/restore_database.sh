#!/bin/bash
################################################################################
# PostgreSQL Database Restore Script
#
# Purpose: Restore PostgreSQL database from backup file
# Usage: ./scripts/restore_database.sh [backup_file]
#        If no backup_file specified, uses latest backup
#
# Examples:
#   # Restore from latest backup
#   ./scripts/restore_database.sh
#
#   # Restore from specific backup
#   ./scripts/restore_database.sh backups/pratiko_backup_20251129_140000.sql.gz
#
# ⚠️  WARNING: This will DROP the existing database and restore from backup!
################################################################################

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_ROOT}/backups"

# Database connection (from docker-compose.yml)
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5433}"
DB_NAME="${POSTGRES_DB:-aifinance}"
DB_USER="${POSTGRES_USER:-aifinance}"
DB_PASSWORD="${POSTGRES_PASSWORD:-devpass}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

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

confirm_restore() {
    local backup_file=$1

    echo ""
    log_warn "⚠️  WARNING: This will DROP the existing database!"
    log_warn "Database: ${DB_NAME} on ${DB_HOST}:${DB_PORT}"
    log_warn "Restore from: $backup_file"
    echo ""
    read -p "Are you sure you want to continue? (type 'yes' to confirm): " -r
    echo

    if [[ ! $REPLY =~ ^yes$ ]]; then
        log_info "Restore cancelled by user"
        exit 0
    fi
}

check_backup_file() {
    local backup_file=$1

    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        exit 1
    fi

    # Verify backup integrity
    if ! gzip -t "$backup_file" 2>/dev/null; then
        log_error "Backup file is corrupted: $backup_file"
        exit 1
    fi

    log_info "Backup file verified ✓"
}

perform_restore() {
    local backup_file=$1

    log_info "Starting database restore..."

    export PGPASSWORD="$DB_PASSWORD"

    # Drop existing database connections
    log_info "Terminating existing database connections..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c \
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();" \
        > /dev/null 2>&1 || true

    # Drop and recreate database
    log_info "Dropping existing database..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c \
        "DROP DATABASE IF EXISTS $DB_NAME;" || {
        log_error "Failed to drop database"
        unset PGPASSWORD
        exit 1
    }

    log_info "Creating new database..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c \
        "CREATE DATABASE $DB_NAME OWNER $DB_USER;" || {
        log_error "Failed to create database"
        unset PGPASSWORD
        exit 1
    }

    # Enable pgvector extension
    log_info "Enabling pgvector extension..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c \
        "CREATE EXTENSION IF NOT EXISTS vector;" || {
        log_warn "Failed to enable pgvector extension (might not be available)"
    }

    # Restore from backup
    log_info "Restoring database from backup..."
    if gunzip -c "$backup_file" | psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" > /dev/null 2>&1; then
        unset PGPASSWORD
        log_info "Database restored successfully ✓"
        return 0
    else
        unset PGPASSWORD
        log_error "Database restore failed"
        return 1
    fi
}

verify_restore() {
    log_info "Verifying restore..."

    export PGPASSWORD="$DB_PASSWORD"

    # Check if database is accessible
    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "\dt" > /dev/null 2>&1; then
        TABLE_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")

        unset PGPASSWORD

        log_info "Restore verified ✓"
        log_info "Tables found: $TABLE_COUNT"
        return 0
    else
        unset PGPASSWORD
        log_error "Restore verification failed"
        return 1
    fi
}

################################################################################
# Main Execution
################################################################################

main() {
    log_info "=========================================="
    log_info "PostgreSQL Restore Script"
    log_info "=========================================="

    # Determine backup file
    if [ $# -eq 0 ]; then
        # Use latest backup
        BACKUP_FILE="${BACKUP_DIR}/pratiko_backup_latest.sql.gz"

        if [ ! -L "$BACKUP_FILE" ]; then
            log_error "No latest backup found. Please specify a backup file."
            log_info "Usage: $0 [backup_file]"
            exit 1
        fi

        # Resolve symlink
        BACKUP_FILE=$(readlink -f "$BACKUP_FILE" 2>/dev/null || realpath "$BACKUP_FILE" 2>/dev/null)
        log_info "Using latest backup: $BACKUP_FILE"
    else
        BACKUP_FILE="$1"
    fi

    # Confirm restore
    confirm_restore "$BACKUP_FILE"

    # Check backup file
    check_backup_file "$BACKUP_FILE"

    # Perform restore
    if perform_restore "$BACKUP_FILE"; then
        if verify_restore; then
            log_info "=========================================="
            log_info "Restore completed successfully!"
            log_info "=========================================="
            exit 0
        else
            log_error "Restore verification failed"
            exit 1
        fi
    else
        log_error "Restore failed"
        exit 1
    fi
}

# Run main function
main "$@"
