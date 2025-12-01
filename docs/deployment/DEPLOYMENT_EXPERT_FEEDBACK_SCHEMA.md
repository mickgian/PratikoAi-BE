# Expert Feedback System Database Schema - Deployment Summary

**Task:** DEV-BE-72 - Implement Expert Feedback System
**Branch:** `DEV-BE-72-expert-feedback-database-schema`
**Date:** 2025-11-21
**Status:** ✅ READY FOR QA TESTING

---

## Quick Summary

This deployment creates the database foundation for the Expert Feedback System, enabling:
- ✅ Expert user profiles with trust scoring
- ✅ Expert feedback collection on AI-generated answers
- ✅ FAQ candidate auto-approval workflow
- ✅ Performance analytics and quality metrics

**Impact:** Enables S113-S130 architecture flow for expert validation

---

## What's Being Deployed

### New Database Objects

**Tables (3):**
1. `expert_profiles` - Expert credentials and trust scores
2. `expert_feedback` - Feedback on AI answers
3. `expert_faq_candidates` - FAQ candidates from experts

**Indexes (12):**
- Performance-optimized for trust-based queries, analytics, and approval workflows

**PostgreSQL Enum Types (3):**
- `feedback_type` - correct, incomplete, incorrect
- `italian_feedback_category` - normativa_obsoleta, interpretazione_errata, etc.
- `expert_credential_type` - dottore_commercialista, revisore_legale, etc.

**Triggers (3):**
- Auto-update `updated_at` timestamps on all 3 tables

---

## Files Changed

### Migration File (NEW)
```
/alembic/versions/20251121_add_expert_feedback_system.py
```
- 300+ lines of SQL
- Complete upgrade/downgrade logic
- Handles enum types, triggers, constraints

### Documentation (NEW)
```
/docs/database/expert_feedback_schema_validation.md       (12,000+ words)
/docs/database/expert_feedback_migration_test_plan.md     (8,000+ words)
/DEPLOYMENT_EXPERT_FEEDBACK_SCHEMA.md                     (This file)
```

---

## Deployment Command

### QA Environment (Hetzner)
```bash
# 1. SSH to QA server
ssh pratiko-qa

# 2. Navigate to project
cd /opt/pratiko-backend

# 3. Checkout branch
git checkout develop
git pull origin develop
git checkout DEV-BE-72-expert-feedback-database-schema
git pull origin DEV-BE-72-expert-feedback-database-schema

# 4. Backup database (CRITICAL!)
pg_dump -Fc $DATABASE_URL > /backups/pre_expert_feedback_$(date +%Y%m%d_%H%M%S).dump

# 5. Activate virtualenv
source .venv/bin/activate

# 6. Run migration
alembic upgrade head

# 7. Verify
psql $DATABASE_URL -c "\dt expert_*"
psql $DATABASE_URL -c "SELECT COUNT(*) FROM expert_profiles;"
```

**Estimated Time:** 2-5 minutes

---

## Rollback Plan

If issues occur, rollback immediately:

```bash
# Rollback migration
alembic downgrade -1

# Restore from backup (if needed)
pg_restore -d $DATABASE_URL /backups/pre_expert_feedback_YYYYMMDD_HHMMSS.dump

# Verify
psql $DATABASE_URL -c "\dt expert_*"  # Should show nothing
```

**Estimated Time:** 5-10 minutes

---

## Critical Issues Resolved

### Issue 1: User Table Type Mismatch
**Problem:** User.id is INTEGER but models expected UUID
**Resolution:** Changed expert_profiles.user_id to INTEGER for compatibility
**Future Action:** Migrate user table to UUID in future sprint

### Issue 2: FAQCandidate Table Naming Conflict
**Problem:** faq_automation.py already has faq_candidates table
**Resolution:** Renamed to expert_faq_candidates (different purpose)

### Issue 3: SQLAlchemy/SQLModel Relationship Incompatibility
**Problem:** Cannot create relationships between SQLAlchemy and SQLModel
**Resolution:** Removed relationships, access via foreign keys only

---

## Testing Checklist

After deployment, verify:

- [ ] All 3 tables created: `\dt expert_*`
- [ ] All 12 indexes created: `\di expert_*`
- [ ] All 3 enum types created: `\dT feedback_type`
- [ ] Insert test expert profile (see test plan)
- [ ] Insert test feedback (see test plan)
- [ ] Verify triggers work (updated_at auto-updates)
- [ ] Verify foreign keys cascade correctly
- [ ] Run performance benchmarks (see test plan)

**Full Test Plan:** `/docs/database/expert_feedback_migration_test_plan.md`

---

## Performance Expectations

### Storage (Year 1)
- expert_profiles: ~2 MB (100 experts)
- expert_feedback: ~80 MB (10K feedback)
- expert_faq_candidates: ~4 MB (1K candidates)
- **Total:** ~86 MB + 43 MB indexes = **129 MB**

### Query Performance
- Find expert by trust score: <10ms
- Get expert feedback (30 days): <20ms
- Approval dashboard: <5ms
- Analytics queries: <100ms

---

## Next Steps

### After QA Deployment:
1. **Testing Phase (1 week)**
   - Run full test plan
   - Verify all constraints
   - Benchmark performance
   - Test with sample data

2. **Code Integration (1 week)**
   - Implement expert feedback API endpoints
   - Build approval workflow UI
   - Integrate with S113-S130 flow

3. **Preprod Deployment (After approval)**
   - Repeat deployment process
   - Test with production-like data
   - Stakeholder review

4. **Production Deployment (After approval)**
   - Final backup and migration
   - Monitor performance
   - Enable expert feedback collection

---

## Risk Assessment

### Low Risk:
- ✅ Migration is isolated (no changes to existing tables)
- ✅ Full rollback plan available
- ✅ Comprehensive test plan
- ✅ No breaking changes to existing features

### Medium Risk:
- ⚠️ User table type mismatch (temporary, documented)
- ⚠️ First use of PostgreSQL enum types in this project

### Mitigation:
- Complete testing on QA before Preprod
- Database backup before deployment
- Rollback plan ready
- Scrum Master approval required

---

## Dependencies

### Required Before Deployment:
- ✅ PostgreSQL ≥12 (for gen_random_uuid())
- ✅ Alembic migrations up to 20251111_add_pub_date
- ✅ user table exists with integer ID
- ✅ Database backup completed

### Blocked By This:
- Expert Feedback API endpoints (DEV-BE-72 backend)
- Expert Feedback UI (DEV-004 frontend)
- Auto-approval workflow

---

## Support & Troubleshooting

### Common Issues:

**1. Migration fails with "relation already exists"**
- **Cause:** Tables already exist from previous run
- **Solution:** Drop tables manually or use rollback

**2. Foreign key violation on user_id**
- **Cause:** No users in user table
- **Solution:** Create at least one user first

**3. Enum type already exists**
- **Cause:** Previous migration attempt
- **Solution:** Migration handles this automatically (DO $$ BEGIN ... EXCEPTION)

**Full Troubleshooting Guide:** See test plan document

---

## Contact & Approval

### Technical Questions:
- **Database Designer (Primo):** Available via Claude Code agent
- **Backend Expert:** Review SQLAlchemy models
- **Architect:** Consult on schema changes

### Deployment Approval:
- **Scrum Master:** Required for QA → Preprod → Production
- **Stakeholder:** Required for Production deployment

---

## Checklist Before Deployment

- [ ] Branch merged to develop (or deployment branch)
- [ ] All tests passing (CI/CD)
- [ ] Database backup completed
- [ ] QA environment accessible
- [ ] Rollback plan reviewed
- [ ] Test plan reviewed
- [ ] Scrum Master notified
- [ ] Deployment window scheduled (low-traffic time)

---

## Post-Deployment Verification

### Immediate (5 minutes after deployment):
```bash
# 1. Check tables exist
psql $DATABASE_URL -c "\dt expert_*"

# 2. Check indexes
psql $DATABASE_URL -c "\di expert_*"

# 3. Insert test data (see test plan)

# 4. Verify triggers work
# UPDATE test record, check updated_at changed
```

### Short-term (1 hour after deployment):
- Monitor database CPU/memory usage
- Check for slow queries (pg_stat_statements)
- Verify no errors in application logs

### Long-term (1 day after deployment):
- Run full test suite
- Benchmark query performance
- Verify index usage (pg_stat_user_indexes)

---

## Success Criteria

Deployment is successful if:
- ✅ All 3 tables created without errors
- ✅ All 12 indexes created and used by queries
- ✅ All 3 enum types created with correct values
- ✅ Test data inserts successfully
- ✅ Triggers fire correctly (updated_at auto-updates)
- ✅ Foreign key cascades work correctly
- ✅ Query performance meets benchmarks (<20ms)
- ✅ No errors in application logs after 1 hour

---

## Deployment History

| Environment | Date | Deployed By | Status | Notes |
|-------------|------|-------------|--------|-------|
| QA (Hetzner) | TBD | TBD | ⏳ Pending | Initial deployment |
| Preprod | TBD | TBD | ⏳ Pending | After QA testing |
| Production | TBD | TBD | ⏳ Pending | After Preprod + approval |

---

**Prepared By:** PratikoAI Database Designer (Primo)
**Document Version:** 1.0
**Last Updated:** 2025-11-21

---

## Quick Reference Links

- **Migration File:** `/alembic/versions/20251121_add_expert_feedback_system.py`
- **Validation Report:** `/docs/database/expert_feedback_schema_validation.md`
- **Test Plan:** `/docs/database/expert_feedback_migration_test_plan.md`
- **SQLAlchemy Models:** `/app/models/quality_analysis.py`
- **Architecture Roadmap:** `/ARCHITECTURE_ROADMAP.md` (DEV-BE-72)

---

**Ready for QA Deployment:** ✅ YES
**Scrum Master Approval Required:** ✅ YES
**Estimated Testing Time:** 2-4 hours
**Estimated Production Deployment:** 2-4 weeks (after QA + Preprod)
