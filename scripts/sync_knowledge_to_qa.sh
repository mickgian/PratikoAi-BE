#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# sync_knowledge_to_qa.sh — One-command dev DB → QA DB knowledge sync
#
# Dumps feed_status, knowledge_items, knowledge_chunks, and
# regulatory_documents from the local dev database and restores them
# to the QA database via SSH + docker exec.  Fully automated —
# no manual SSH into QA required.
#
# Usage:
#   export QA_HOST=<qa-server-ip>      # required (Hetzner QA IP)
#   ./scripts/sync_knowledge_to_qa.sh
#
# Prerequisites:
#   - Local dev DB running (docker compose up db)
#   - SSH access to QA server as 'deploy' user
#   - QA containers running (db service)
#
# Options (env vars):
#   QA_HOST          QA server IP/hostname (REQUIRED)
#   QA_SSH_USER      SSH user on QA (default: deploy)
#   QA_SSH_KEY       Path to SSH key (optional)
# ──────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Config ───────────────────────────────────────────────────────────
QA_HOST="${QA_HOST:?ERROR: Set QA_HOST env var (e.g. export QA_HOST=1.2.3.4)}"
QA_SSH_USER="${QA_SSH_USER:-deploy}"
QA_SSH_KEY="${QA_SSH_KEY:-}"

DB_USER="aifinance"
DB_NAME="aifinance"

# Tables in dependency order (parents first)
TABLES=(feed_status knowledge_items knowledge_chunks regulatory_documents)

# SSH options
SSH_OPTS="-o StrictHostKeyChecking=accept-new -o ConnectTimeout=10"
if [ -n "$QA_SSH_KEY" ]; then
  SSH_OPTS="$SSH_OPTS -i $QA_SSH_KEY"
fi
SSH_CMD="ssh $SSH_OPTS ${QA_SSH_USER}@${QA_HOST}"

# Docker compose commands (local dev + remote QA)
DEV_DC="docker compose"
QA_DC="cd /opt/pratikoai && docker compose --env-file .env.qa -f docker-compose.yml -f docker-compose.qa.yml"

# ── Helpers ──────────────────────────────────────────────────────────
info()  { echo "  $*"; }
step()  { echo ""; echo "==> $*"; }
abort() { echo ""; echo "ERROR: $*" >&2; exit 1; }

dev_psql() {
  $DEV_DC exec -T db psql -U "$DB_USER" -d "$DB_NAME" "$@"
}

dev_pgdump() {
  $DEV_DC exec -T db pg_dump -U "$DB_USER" -d "$DB_NAME" "$@"
}

qa_exec() {
  $SSH_CMD "$QA_DC exec -T db $*"
}

# ── Pre-flight checks ───────────────────────────────────────────────
echo ""
echo "================================================================"
echo "  PratikoAI Knowledge Base Sync:  Dev DB  -->  QA DB"
echo "================================================================"
echo "  Dev:  local docker compose (db service)"
echo "  QA:   ${QA_SSH_USER}@${QA_HOST} (docker db container)"
echo ""

step "Pre-flight checks..."

# Check local dev DB container is running
if ! $DEV_DC exec -T db pg_isready -U "$DB_USER" > /dev/null 2>&1; then
  abort "Dev DB container is not running. Start it with: docker compose up -d db"
fi
info "Dev DB: OK"

# Check SSH + QA DB connectivity
if ! $SSH_CMD "$QA_DC exec -T db pg_isready -U $DB_USER" > /dev/null 2>&1; then
  abort "Cannot reach QA DB via SSH. Check QA_HOST, SSH key, and that QA containers are running."
fi
info "QA DB:  OK"

# ── Gather counts before sync ───────────────────────────────────────
step "Current row counts..."
printf "  %-30s %10s %10s\n" "TABLE" "DEV" "QA"
printf "  %-30s %10s %10s\n" "-----" "---" "--"
for table in "${TABLES[@]}"; do
  dev_count=$(dev_psql -tAc "SELECT COUNT(*) FROM $table" 2>/dev/null | tr -d ' ' || echo "?")
  qa_count=$(qa_exec "psql -U $DB_USER -d $DB_NAME -tAc 'SELECT COUNT(*) FROM $table'" 2>/dev/null | tr -d ' ' || echo "?")
  printf "  %-30s %10s %10s\n" "$table" "$dev_count" "$qa_count"
done

# ── Confirm ──────────────────────────────────────────────────────────
echo ""
echo "This will TRUNCATE the QA tables and replace with dev data."
read -r -p "Continue? [y/N] " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
  echo "Aborted."
  exit 0
fi

# ── Step 1: Dump dev tables ──────────────────────────────────────────
step "Step 1/2: Dumping dev tables..."

DUMP_FILE=$(mktemp /tmp/pratiko_sync_XXXXXX.sql)
trap 'rm -f "$DUMP_FILE"' EXIT

# Header: wrap in transaction, disable triggers, truncate first
cat > "$DUMP_FILE" <<'SQL'
BEGIN;

-- Disable FK/trigger checks for self-referential tables
SET session_replication_role = 'replica';

-- Truncate inside the same transaction to prevent race conditions
-- with background workers that might insert rows between truncate and copy
TRUNCATE TABLE regulatory_documents, knowledge_chunks, knowledge_items, feed_status CASCADE;

SQL

for table in "${TABLES[@]}"; do
  info "Dumping $table..."
  if [ "$table" = "knowledge_items" ]; then
    # knowledge_items has a circular self-referential FK (parent_document_id).
    # pg_dump --data-only can emit duplicate rows for such tables.
    # Use --inserts --on-conflict-do-nothing so duplicates are silently skipped.
    dev_pgdump --data-only --table="$table" --inserts --on-conflict-do-nothing --no-owner --no-privileges >> "$DUMP_FILE"
  else
    dev_pgdump --data-only --table="$table" --no-owner --no-privileges >> "$DUMP_FILE"
  fi
done

# Footer: re-enable triggers and commit
cat >> "$DUMP_FILE" <<'SQL'

-- Re-enable FK checks and triggers
SET session_replication_role = 'origin';

COMMIT;
SQL

DUMP_SIZE=$(du -h "$DUMP_FILE" | cut -f1)
info "Dump complete: $DUMP_SIZE"

# ── Step 2: Restore to QA ───────────────────────────────────────────
step "Step 2/2: Restoring to QA (truncate + load in single transaction)..."
cat "$DUMP_FILE" | $SSH_CMD "$QA_DC exec -T db psql -U $DB_USER -d $DB_NAME --set ON_ERROR_STOP=on -q"
info "Restore complete"

# ── Verify ───────────────────────────────────────────────────────────
step "Verification..."
ALL_MATCH=true
printf "  %-30s %10s %10s %s\n" "TABLE" "DEV" "QA" "STATUS"
printf "  %-30s %10s %10s %s\n" "-----" "---" "--" "------"
for table in "${TABLES[@]}"; do
  dev_count=$(dev_psql -tAc "SELECT COUNT(*) FROM $table" | tr -d ' ')
  qa_count=$(qa_exec "psql -U $DB_USER -d $DB_NAME -tAc 'SELECT COUNT(*) FROM $table'" | tr -d ' ')
  if [ "$dev_count" = "$qa_count" ]; then
    status="OK"
  else
    status="MISMATCH"
    ALL_MATCH=false
  fi
  printf "  %-30s %10s %10s %s\n" "$table" "$dev_count" "$qa_count" "$status"
done

echo ""
if $ALL_MATCH; then
  echo "================================================================"
  echo "  Sync complete! QA knowledge base matches dev."
  echo "================================================================"
else
  echo "WARNING: Some counts don't match. Check for errors above."
  exit 1
fi
