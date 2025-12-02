# ADR-012: Enhanced Pre-commit Test Enforcement

**Status:** ACCEPTED
**Date:** 2025-11-25
**Decision Makers:** PratikoAI Architect (Egidio), Michele Giannone (Stakeholder)
**Context Review:** DEV-BE-72 revealed 9 bugs that should have been caught by tests

---

## Context

**Current State:**
- Pre-commit hook enforces 30% global test coverage threshold
- Hook runs all tests on every commit (`.pre-commit-config.yaml` lines 98-104)
- No enforcement of test-first development (TDD)
- No validation that new features have corresponding test files

**Problem:**
- Developers can commit feature code without writing tests
- Tests can be added "later" (but often forgotten)
- Coverage threshold is global (easy to pass by having high coverage in unrelated modules)
- No mechanism to verify tests were written BEFORE implementation

**Evidence from DEV-BE-72:**
- 9 bugs discovered during manual testing
- Bugs included: enum mismatches, foreign key errors, validation schema mismatches
- All bugs should have been caught by automated tests
- Root cause: Tests written after implementation (or not at all)

---

## Decision

**Enhance pre-commit hooks with three additional TDD enforcement checks:**

### 1. Test File Existence Check
**Hook ID:** `check-test-files-exist`
**Purpose:** Block commits of feature code without corresponding test files

**Logic:**
```python
# For each new/modified file in app/
# Example: app/services/cache_service.py
# Require: tests/services/test_cache_service.py
```

**Implementation:** `/scripts/check_test_files_exist.py`

---

### 2. Test-Code Co-Modification Check
**Hook ID:** `check-test-code-co-modification`
**Purpose:** Warn when feature code modified without test updates

**Logic:**
```python
# If app/services/cache_service.py modified
# Expect: tests/services/test_cache_service.py also in staged files
```

**Mode:** WARNING (not blocking) - encourages good practice without being too strict

**Implementation:** `/scripts/check_test_code_co_modification.py`

---

### 3. Minimum Test Count Check
**Hook ID:** `check-minimum-test-count`
**Purpose:** Ensure new test files have adequate test functions

**Logic:**
```python
# For each new test file
# Require: Minimum 3 test functions
# - 1 happy path test
# - 1 error case test
# - 1 edge case test
```

**Implementation:** `/scripts/check_minimum_test_count.py`

---

## Usage

**Normal commit (all hooks enforced):**
```bash
git commit -m "feat: Add cache service"
```

**Emergency bypass (requires justification):**
```bash
git commit --no-verify -m "HOTFIX: Critical production bug (tests in DEV-BE-XXX)"
```

---

## Consequences

**Positive:**
- ✅ Impossible to commit feature code without corresponding tests
- ✅ Test-first development becomes the default workflow
- ✅ Reduces bug count by catching issues early
- ✅ Aligns with ADR-013 (TDD Methodology)

**Negative:**
- ❌ Slight increase in commit time (~1-2 seconds for hook execution)
- ❌ May frustrate developers initially (adjustment period)
- ❌ May produce false positives for generated code

**Mitigations:**
- Clear error messages with documentation links
- Allow `--no-verify` bypass for emergencies
- Exclude generated files (`__init__.py`, migrations)
- Co-modification check is WARNING (not blocking)

---

## Implementation

**Files Modified:**
- `.pre-commit-config.yaml` (lines 106-137): Added 3 new hooks
- `scripts/check_test_files_exist.py`: Created
- `scripts/check_test_code_co_modification.py`: Created
- `scripts/check_minimum_test_count.py`: Created

**Activation:** Immediate (hooks active on next commit)

---

## Success Metrics

**Track weekly:**
1. % of commits blocked by hooks
2. % of commits with test files for feature files
3. % of commits using `--no-verify` (target: <5%)

**Target:**
- 100% of new feature commits include test files (measured over 2 weeks)
- Zero bugs in manual testing phase (vs. 9 bugs in DEV-BE-72)

---

## References

- DEV-BE-72 Post-Mortem: 9 bugs discovered in manual testing (2025-11-24)
- ADR-013: Test-Driven Development (TDD) Methodology
- Agent Updates:
  - `.claude/agents/backend-expert.md` (lines 34-95: TDD section)
  - `.claude/agents/frontend-expert.md` (lines 35-163: TDD section)
  - `.claude/agents/test-generation.md` (lines 34-103: Validator role)
  - `.claude/agents/debug-specialist.md` (lines 20-180: Test-driven debugging)

---

**Approved By:** PratikoAI Architect (Egidio)
**Date:** 2025-11-25
