# ADR-013: Test-Driven Development (TDD) Methodology

**Status:** ACCEPTED
**Date:** 2025-11-25
**Decision Makers:** PratikoAI Architect (Egidio), Michele Giannone (Stakeholder)
**Context Review:** DEV-BE-72 post-mortem (9 bugs in manual testing)

---

## Context

**Current Development Workflow:**
- Feature implementation first, tests added later (if at all)
- Tests considered validation tool, not design tool
- Test coverage enforced at commit time (30% global threshold)
- No formal TDD process documented

**Problem: DEV-BE-72 Shipped with 9 Critical Bugs**

All 9 bugs were **preventable through automated tests**:
1. Missing frontend component
2. Frontend validation schema mismatch (Pydantic ≠ TypeScript)
3. Foreign key to non-existent table
4. PostgreSQL enum type name mismatch
5. Session management issues (user_id not in session)
6. String to enum conversion errors
7. Enum serialization bugs (not JSON serializable)
8. Enum deserialization bugs
9. API enum conversion passing objects instead of strings

**Root Cause:** Tests written AFTER implementation (too late to catch design flaws)

---

## Decision

**Adopt Test-Driven Development (TDD) as the mandatory development methodology for all feature work.**

### Core Principle: RED-GREEN-REFACTOR Cycle

**🔴 RED: Write Failing Test FIRST**
```python
def test_cache_key_excludes_doc_hashes():
    """Cache key should NOT include doc_hashes (too volatile)."""
    service = CacheService()

    key1 = service.generate_cache_key(..., doc_hashes=["doc1", "doc2"])
    key2 = service.generate_cache_key(..., doc_hashes=["doc3", "doc4"])

    assert key1 == key2  # FAILS - function doesn't exist yet
```

**🟢 GREEN: Write Minimal Code to Pass**
```python
def generate_cache_key(..., doc_hashes=None):
    """Generate cache key WITHOUT doc_hashes."""
    key_parts = f"{query_hash}{model}{temperature}{kb_epoch}"
    return hashlib.sha256(key_parts.encode()).hexdigest()
    # Test PASSES - minimal implementation
```

**🔵 REFACTOR: Improve Code Quality**
```python
def generate_cache_key(..., doc_hashes=None):
    """Generate deterministic cache key.

    Excludes doc_hashes to avoid cache misses from retrieval variations.
    """
    key_parts = self._generate_cache_key_parts(...)  # Extracted
    return hashlib.sha256(key_parts.encode()).hexdigest()
    # Tests STILL PASS - code improved
```

---

## Test Coverage Requirements

**Global Threshold:** 30% (for legacy code compatibility)
**New Code Threshold:** 70% (enforced by CI diff-cover)
**Pre-commit Hook:** Blocks commits below 30% global coverage

### Test Types Pyramid
```
        /\
       /E2E\ (10% of tests - critical user flows)
      /----\
     /Integ-\ (30% of tests - API + DB)
    /--------\
   /  Unit    \ (60% of tests - business logic)
  /____________\
```

---

## Agent Role Definitions

### Ezio (Backend Expert)
- **Writes tests FIRST** before implementing backend features
- Follows RED-GREEN-REFACTOR for all APIs, services, models
- Invokes Clelia AFTER feature complete for validation

### Livia (Frontend Expert)
- **Writes tests FIRST** before implementing frontend features
- Follows RED-GREEN-REFACTOR for components, hooks, pages
- Tests: Component (Jest + RTL), E2E (Playwright)

### Clelia (Test Validator)
- **NEW PARADIGM:** Validator, NOT generator
- Invoked AFTER Ezio/Livia complete TDD cycle
- Reviews test quality, coverage, edge cases
- **NOT invoked during RED-GREEN-REFACTOR** (avoids agent switching)

### Tiziano (Debug Specialist)
- Writes regression tests for every bug
- RED: Write failing test that reproduces bug
- GREEN: Fix bug (test passes)
- Ensures bug cannot reoccur

---

## Workflow Example

**Bad (Old Pattern - DEPRECATED):**
```
1. Implement feature → 2. Write tests → 3. Fix failing tests
```

**Good (TDD - CURRENT):**
```
1. 🔴 Write test (FAILS)
2. 🟢 Implement (test PASSES)
3. 🔵 Refactor (tests still PASS)
4. ✅ Invoke Clelia to validate coverage/edge cases
```

---

## Consequences

**Positive:**
- ✅ Fewer bugs (9 bugs in DEV-BE-72 would have been caught)
- ✅ Better API design (tests force clean interfaces)
- ✅ Faster debugging (test failures pinpoint exact issue)
- ✅ Living documentation (tests show how to use code)
- ✅ Fearless refactoring (tests protect against regressions)

**Negative:**
- ❌ Initial slowdown (~20% time increase when learning)
- ❌ Learning curve (team must learn TDD discipline)
- ❌ Test maintenance (tests require updates with requirements)

**Mitigations:**
- Agent files updated with TDD mandates
- Pre-commit hooks enforce test-first (ADR-012)
- Measure bug count reduction over 3 months

---

## Success Metrics

**Tracked Monthly:**

1. **Test Coverage:**
   - Global: ≥30% (legacy compatible)
   - New code: ≥70% (CI enforced)
   - Target: 80% by Q2 2025

2. **Bug Escape Rate:**
   - Baseline: 9 bugs in DEV-BE-72
   - Target: <2 bugs per feature
   - Measurement: Bugs found in manual testing

3. **Test-First Compliance:**
   - Baseline: 4.2% of tasks have Test Requirements
   - Target: 100% by Week 3
   - Measurement: ARCHITECTURE_ROADMAP.md audit

4. **Developer Velocity:**
   - Maintain current velocity (1-2 weeks/feature)
   - Reduce debugging time (less manual testing)

---

## Test Type Guidelines

**Unit Tests (60%):**
- Test single functions in isolation
- Mock external dependencies
- Fast (<10ms per test)
- Example: `test_generate_cache_key_without_doc_hashes()`

**Integration Tests (30%):**
- Test multiple components together
- Use real database (fixtures, cleanup)
- Test API endpoints end-to-end
- Example: `test_expert_feedback_creates_database_record()`

**E2E Tests (10%):**
- Test complete user workflows
- Use Playwright for browser automation
- Slow (>1 second per test)
- Example: `test_expert_submits_feedback_sees_confirmation()`

---

## References

- **DEV-BE-72 Post-Mortem:** 9 bugs discovered (2025-11-24)
- **ADR-012:** Enhanced Pre-commit Test Enforcement
- **Agent Updates:**
  - Backend Expert (ezio): Lines 34-95 mandatory TDD section
  - Frontend Expert (livia): Lines 35-163 TDD section
  - Test Validator (clelia): Lines 34-103 new validation role
  - Debug Specialist (tiziano): Lines 20-180 test-driven debugging
- **Industry Standards:**
  - Kent Beck, "Test-Driven Development: By Example" (2002)
  - Martin Fowler, "Refactoring" (2018)

---

**Approved By:** PratikoAI Architect (Egidio)
**Date:** 2025-11-25
