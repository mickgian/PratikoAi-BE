# End-to-End (E2E) Integration Tests

This directory contains **End-to-End Integration Tests** that verify complete workflows across multiple layers of the application (API → Service → Database → File System).

## Purpose

**Why E2E Tests?**
- Catch integration bugs that unit tests miss (API contract mismatches, database constraints, type incompatibilities)
- Verify actual database transactions and foreign key relationships
- Test real file system operations (task generation)
- Validate background task execution
- Ensure complete workflows work correctly

**Unit Tests vs E2E Tests:**
- **Unit tests**: Test individual components in isolation (mocked dependencies)
- **E2E tests**: Test complete workflows with real dependencies (database, file system)
- **Both are essential**: Unit tests catch logic bugs, E2E tests catch integration bugs

## Test Strategy

Full documentation: `docs/testing/E2E_EXPERT_FEEDBACK_TESTING_STRATEGY.md`

### Current Test Scenarios

| ID | Scenario | Status |
|----|----------|--------|
| E2E-01 | Correct feedback workflow | ✅ Implemented |
| E2E-02 | Incomplete feedback with task generation | ✅ Implemented |
| E2E-03 | Incorrect feedback with task generation | 🔴 TODO |
| E2E-04 | Authentication & authorization RBAC | ✅ Implemented |
| E2E-05 | Validation errors | ✅ Implemented |
| E2E-06 | Database constraints | 🔴 TODO |
| E2E-07 | Field mappings & type compatibility | ✅ Implemented |
| E2E-08 | Golden Set workflow integration | 🔴 TODO |
| E2E-09 | Error recovery & transaction rollback | 🔴 TODO |
| E2E-10 | Background task execution | 🔴 TODO |

## Running E2E Tests

### Prerequisites

1. **Test Database**: Create PostgreSQL test database
   ```bash
   psql -U postgres
   CREATE DATABASE pratiko_ai_test;
   \q
   ```

2. **Environment Variables**: Set test database URL
   ```bash
   export DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/pratiko_ai_test"
   ```

3. **Run Migrations**: Initialize test database schema
   ```bash
   uv run alembic upgrade head
   ```

### Run All E2E Tests

```bash
# Run all E2E tests
uv run pytest tests/e2e/ -v

# Run with coverage
uv run pytest tests/e2e/ --cov=app --cov-report=html

# Run specific test file
uv run pytest tests/e2e/test_expert_feedback_e2e.py -v

# Run specific test
uv run pytest tests/e2e/test_expert_feedback_e2e.py::test_e2e_01_correct_feedback_golden_set_workflow -v
```

### Run in Parallel (Faster)

```bash
# Install pytest-xdist
uv add --dev pytest-xdist

# Run tests in parallel
uv run pytest tests/e2e/ -n auto
```

## Test Structure

### Directory Layout

```
tests/e2e/
├── README.md                           # This file
├── conftest.py                         # Test fixtures and database setup
├── test_expert_feedback_e2e.py         # Expert Feedback E2E tests
└── test_<feature>_e2e.py              # Additional E2E test files
```

### Key Fixtures

**Database Fixtures:**
- `test_engine`: PostgreSQL test engine (session-scoped)
- `db_session`: Async session with automatic rollback (function-scoped)

**User Fixtures:**
- `test_super_user`: User with SUPER_USER role
- `test_regular_user`: User with regular USER role
- `test_expert_profile`: Expert profile with high trust score

**Data Fixtures:**
- `sample_feedback_payload`: Valid feedback submission JSON
- `temp_project_root`: Temporary directory for file operations

## Writing E2E Tests

### Basic Template

```python
@pytest.mark.asyncio
async def test_e2e_my_feature(
    db_session: AsyncSession,
    test_super_user: User,
    test_expert_profile: ExpertProfile,
):
    """E2E test for my feature.

    Test Steps:
    1. Setup test data
    2. Make API request
    3. Verify database changes
    4. Verify file system changes
    5. Clean up (automatic rollback)
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Override authentication
        app.dependency_overrides[get_current_user] = lambda: test_super_user

        try:
            # Make API request
            response = await client.post("/api/endpoint", json={...})

            # Verify response
            assert response.status_code == 200

            # Verify database
            result = await db_session.execute(select(Model).where(...))
            record = result.scalar_one()
            assert record.field == "expected_value"

        finally:
            app.dependency_overrides.clear()
```

### Best Practices

1. **Use Real Database**: Don't mock database - catch constraint violations
2. **Explicit Waits**: Use `asyncio.sleep()` for background tasks, not implicit timing
3. **Verify Everything**: Check API response, database state, file system, and side effects
4. **Clean Dependencies**: Always clear `app.dependency_overrides` in `finally` block
5. **Descriptive Names**: Use `test_e2e_XX_descriptive_name` format
6. **Docstrings**: Document test steps and expected outcomes

### Testing Background Tasks

```python
# Submit request that triggers background task
response = await client.post("/api/endpoint", json=payload)
assert response.status_code == 201

# Wait for background task to complete
await asyncio.sleep(3)  # Adjust timeout as needed

# Verify background task results
result = await db_session.execute(select(Model).where(...))
record = result.scalar_one()
assert record.task_completed is True
```

### Testing File System Changes

```python
# Use temporary directory
def test_with_files(temp_project_root: Path):
    # Files are created in temp_project_root
    task_file = temp_project_root / "QUERY_ISSUES_ROADMAP.md"

    # Verify file exists and contains expected content
    assert task_file.exists()
    content = task_file.read_text()
    assert "QUERY-08" in content
```

## Troubleshooting

### Test Database Connection Issues

**Problem:** `asyncpg.exceptions.InvalidCatalogNameError: database "pratiko_ai_test" does not exist`

**Solution:**
```bash
psql -U postgres -c "CREATE DATABASE pratiko_ai_test;"
```

### Tests Fail Due to Missing Tables

**Problem:** `relation "users" does not exist`

**Solution:**
```bash
# Run migrations on test database
DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/pratiko_ai_test" \
  uv run alembic upgrade head
```

### Tests Are Slow

**Problem:** E2E tests take >2 minutes to run

**Solutions:**
1. Use transaction rollback instead of recreating tables
2. Run tests in parallel: `pytest -n auto`
3. Reduce `asyncio.sleep()` timeouts for background tasks
4. Mock external services (Redis, email, LLM APIs)

### Flaky Tests

**Problem:** Tests pass sometimes, fail other times

**Solutions:**
1. Use explicit waits with timeouts instead of fixed `sleep()`
2. Check background task completion status in database
3. Mock non-deterministic dependencies (timestamps, random values)
4. Ensure test isolation (database rollback, temp directories)

## CI/CD Integration

E2E tests run in GitHub Actions on every PR:

**Workflow:** `.github/workflows/e2e-tests.yml`

**Pipeline Steps:**
1. Start PostgreSQL service container
2. Install dependencies
3. Run database migrations
4. Execute E2E tests
5. Upload coverage report

**Local CI Simulation:**
```bash
# Run tests exactly as CI does
docker run -d --name postgres-test \
  -e POSTGRES_DB=pratiko_ai_test \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 postgres:16

uv run pytest tests/e2e/ --cov=app

docker stop postgres-test && docker rm postgres-test
```

## Coverage Goals

**Target Coverage:**
- Unit tests: 45-50% (API + Service layers)
- E2E tests: +10-15% (Integration paths)
- **Total: 55-65%**

**Coverage by Module:**
- `app/api/v1/expert_feedback.py`: 95%
- `app/services/expert_feedback_collector.py`: 90%
- `app/services/task_generator_service.py`: 95%
- `app/schemas/expert_feedback.py`: 100%

## Next Steps

**Phase 1: Complete Core E2E Tests** (Current)
- [x] E2E-01: Correct feedback workflow
- [x] E2E-02: Incomplete feedback with task generation
- [ ] E2E-03: Incorrect feedback with task generation
- [x] E2E-04: Authentication & authorization
- [x] E2E-05: Validation errors

**Phase 2: Advanced E2E Tests**
- [ ] E2E-06: Database constraints
- [x] E2E-07: Field mappings & type compatibility
- [ ] E2E-08: Golden Set workflow integration
- [ ] E2E-09: Error recovery & transaction rollback
- [ ] E2E-10: Background task execution

**Phase 3: Expand Coverage**
- [ ] Add E2E tests for other features (auth, queries, etc.)
- [ ] Performance testing (load tests, stress tests)
- [ ] Security testing (SQL injection, XSS, CSRF)

## References

**Documentation:**
- [E2E Testing Strategy](../../docs/testing/E2E_EXPERT_FEEDBACK_TESTING_STRATEGY.md)
- [Expert Feedback Implementation Summary](../../EXPERT_FEEDBACK_IMPLEMENTATION_SUMMARY.md)
- [Database Schema Documentation](../../DEPLOYMENT_EXPERT_FEEDBACK_SCHEMA.md)

**Related Code:**
- API: `app/api/v1/expert_feedback.py`
- Service: `app/services/expert_feedback_collector.py`
- Task Generator: `app/services/task_generator_service.py`
- Models: `app/models/quality_analysis.py`

**Existing Tests:**
- Unit tests (API): `tests/api/test_expert_feedback.py`
- Unit tests (Service): `tests/services/test_task_generator_service.py`
