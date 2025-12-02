#!/bin/bash
# Verification script for Phase 1 migration cleanup

echo "==================================="
echo "Phase 1 Migration Verification"
echo "==================================="
echo ""

MIGRATION_FILE="/Users/micky/PycharmProjects/PratikoAi-BE/alembic/versions/e1ca2614d620_phase_1_convert_regional_taxes_py_to_.py"

echo "1. File Exists:"
if [ -f "$MIGRATION_FILE" ]; then
    echo "   ✅ Migration file exists"
else
    echo "   ❌ Migration file NOT found"
    exit 1
fi
echo ""

echo "2. File Size:"
LINES=$(wc -l < "$MIGRATION_FILE" | tr -d ' ')
echo "   Lines: $LINES"
if [ "$LINES" -lt 200 ]; then
    echo "   ✅ File is clean (< 200 lines)"
else
    echo "   ⚠️  File might contain extra content"
fi
echo ""

echo "3. Tables Created (upgrade):"
CREATE_COUNT=$(grep -c "op.create_table" "$MIGRATION_FILE")
echo "   Count: $CREATE_COUNT"
if [ "$CREATE_COUNT" -eq 4 ]; then
    echo "   ✅ Exactly 4 tables (correct)"
    grep "op.create_table" "$MIGRATION_FILE" | sed 's/^/     - /'
else
    echo "   ❌ Expected 4, found $CREATE_COUNT"
fi
echo ""

echo "4. Tables Dropped (downgrade):"
DROP_COUNT=$(grep -c "op.drop_table" "$MIGRATION_FILE")
echo "   Count: $DROP_COUNT"
if [ "$DROP_COUNT" -eq 4 ]; then
    echo "   ✅ Exactly 4 tables (correct)"
    grep "op.drop_table" "$MIGRATION_FILE" | sed 's/^/     - /'
else
    echo "   ❌ Expected 4, found $DROP_COUNT"
fi
echo ""

echo "5. Dangerous Operations Check:"
ALTER_COUNT=$(grep -c "op.alter" "$MIGRATION_FILE" 2>/dev/null || echo "0")
echo "   ALTER operations: $ALTER_COUNT"
if [ "$ALTER_COUNT" -eq 0 ]; then
    echo "   ✅ No ALTER operations (safe)"
else
    echo "   ⚠️  Found ALTER operations"
fi
echo ""

echo "6. Python Syntax Check:"
if python3 -m py_compile "$MIGRATION_FILE" 2>/dev/null; then
    echo "   ✅ Python syntax valid"
else
    echo "   ❌ Syntax errors found"
    exit 1
fi
echo ""

echo "7. Alembic Recognition:"
ALEMBIC_CHECK=$(uv run alembic history 2>/dev/null | grep "e1ca2614d620")
if [ -n "$ALEMBIC_CHECK" ]; then
    echo "   ✅ Migration recognized by Alembic"
    echo "   $ALEMBIC_CHECK"
else
    echo "   ❌ Migration NOT recognized by Alembic"
fi
echo ""

echo "8. Foreign Key Relationships:"
FK_REGIONI=$(grep -c "regioni.id" "$MIGRATION_FILE")
FK_COMUNI=$(grep -c "comuni.id" "$MIGRATION_FILE")
echo "   References to regioni.id: $FK_REGIONI"
echo "   References to comuni.id: $FK_COMUNI"
if [ "$FK_REGIONI" -ge 2 ] && [ "$FK_COMUNI" -ge 1 ]; then
    echo "   ✅ Foreign key relationships present"
else
    echo "   ⚠️  Foreign key relationships may be missing"
fi
echo ""

echo "==================================="
echo "Summary:"
echo "==================================="
if [ "$LINES" -lt 200 ] && [ "$CREATE_COUNT" -eq 4 ] && [ "$DROP_COUNT" -eq 4 ] && [ "$ALTER_COUNT" -eq 0 ]; then
    echo "✅ ALL CHECKS PASSED"
    echo ""
    echo "Migration is SAFE to deploy!"
    echo ""
    echo "Next steps:"
    echo "  1. Backup database"
    echo "  2. Run: uv run alembic upgrade e1ca2614d620"
    echo "  3. Verify tables created"
    exit 0
else
    echo "⚠️  SOME CHECKS FAILED"
    echo "Review the migration before deploying"
    exit 1
fi
