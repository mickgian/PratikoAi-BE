# Workflow Improvement Proposal: Task-Based Development with Regression Testing

**Date:** 2025-11-29 (Updated)
**Status:** DRAFT - Under Review (Integrated Reddit Article Enhancements)
**Version:** 1.3 - Integrated Reddit article tactical patterns
**Inspiration:** Reddit r/ClaudeAI post on plan-mode + task workflow
**Customized For:** PratikoAI multi-agent system with TDD enforcement

**Latest Updates:**

**v1.3 (2025-11-29):**
- ✅ Integrated **3 tactical enhancements** from Reddit article analysis
- ✅ Added **Context Handoff System** (context.json) for 30% token reduction
- ✅ Promoted **SubagentStop Hooks** from optional to recommended (Phase 1)
- ✅ Added **Test Parallelization** (pytest-xdist) for 50% faster execution
- ✅ Documented what we adopted vs. rejected from Reddit article

**v1.2 (2025-11-26):**
- ✅ Added **Phase 0: Feature Planning** with @Mario (Business Analyst agent)
- ✅ Interactive requirements gathering before task creation
- ✅ Codebase impact analysis (breaking changes, affected features)
- ✅ Complexity routing (complex features → BA session, bugs → skip BA)

**v1.1 (2025-11-26):**
- ✅ Replaced "regression after EVERY subtask" with intelligent **tiered testing strategy**
- ✅ RED phase: Run only new test (fastest feedback)
- ✅ GREEN/BLUE phases: Run affected modules + full regression
- ✅ Risk-based test selection (database changes → models+api, service changes → services/*, etc.)
- ✅ Maintains safety while improving velocity

---

## Executive Summary

Enhance PratikoAI development workflow by implementing **task-based execution with mandatory regression testing**. This approach combines Reddit's proven "one task at a time" pattern with our existing ARCHITECTURE_ROADMAP.md system, preventing context drift and ensuring existing features never break.

**Key Principles:**
1. **Business Analyst phase FIRST** - Interactive requirements gathering before implementation (@Mario)
2. **ONE task at a time** - Implement, test, stop
3. **Tiered testing MANDATORY** - Smart testing at each phase (task tests → module tests → full regression at GREEN/BLUE)
4. **Manual testing required** - No auto-commit/push
5. **Use existing conventions** - DEV-BE-XXX, DEV-FE-XXX
6. **Roadmap as source of truth** - ARCHITECTURE_ROADMAP.md for all planned tasks

---

## Problem Statement

### Current Issues
- ❌ **Breaking existing features** - Changes break unrelated functionality
- ❌ **Context drift** - Claude loses focus during long implementations
- ❌ **No systematic regression testing** - Tests run only at commit time
- ❌ **Manual workflow steps** - No automation for repetitive tasks

### Reddit User Results (https://www.reddit.com/r/ClaudeAI/comments/1m7zlot/how_planmode_and_four_slash_commands_turned/)
- ✅ **70% token reduction** - Smaller, focused prompts
- ✅ **Near-zero context drift** - Each task isolated
- ✅ **Predictable behavior** - "Junior dev following checklist"

---

## Architecture: PratikoAI-Adapted Workflow

### File Structure
```
Project Root:
├── claude.md                           # EXISTING - Enhanced with task rules
├── tasks.md                            # NEW - Current sprint checklist
├── ARCHITECTURE_ROADMAP.md             # EXISTING - Strategic development tasks (source of truth)
└── QUERY_ISSUES_ROADMAP.md             # EXISTING - Expert feedback tasks

.claude/
├── commands/                           # NEW - Task automation commands
│   ├── start-feature-planning.md       # NEW - Invoke @Mario for BA session
│   ├── generate-task-file.md           # Convert roadmap → tasks.md
│   ├── run-next-task.md                # Execute ONE task + regression tests
│   ├── prepare-commit.md               # Prepare commit (NO auto-push)
│   ├── tdd-red.md                      # Start RED phase
│   ├── tdd-green.md                    # Start GREEN phase
│   ├── tdd-blue.md                     # Start BLUE phase
│   ├── regression-test.md              # Run full test suite
│   └── code-review.md                  # KISS/overengineering check
├── workflows/
│   ├── task-based-development.md       # NEW - Complete workflow doc
│   ├── regression-testing.md           # NEW - Regression test strategy
│   └── tdd-workflow.md                 # EXISTING - TDD enforcement
└── agents/                             # EXISTING - 10 specialized agents
    ├── business-analyst.md             # NEW - @Mario (requirements gathering)
    ├── architect.md                    # EXISTING - @Egidio (architecture oversight)
    ├── backend-expert.md               # EXISTING - @Ezio
    ├── frontend-expert.md              # EXISTING - @Livia
    ├── database-designer.md            # EXISTING - @Primo
    └── [...7 more agents]
```

---

## Context Management System (NEW in v1.3)

### Purpose
Structured inter-task communication to reduce token usage and maintain architectural coherence across task boundaries.

### Context Handoff File: `.claude/context.json`

**Schema:**
```json
{
  "current_task": "DEV-BE-XXX",
  "current_phase": "RED|GREEN|BLUE",
  "current_agent": "ezio|livia|primo|...",
  "previous_outputs": {
    "migration_file": "20251126_add_feature.py",
    "test_count": 15,
    "endpoints_added": ["POST /api/feature"]
  },
  "shared_context": {
    "user_id_type": "string",
    "feature_flags": ["sso_enabled"],
    "api_version": "v1"
  },
  "task_metadata": {
    "started_at": "2025-11-29T10:00:00Z",
    "tests_passed": 287,
    "coverage": "51.2%"
  }
}
```

**Benefits:**
- **30% token reduction** (based on Reddit article analysis)
- Prevents repeating context in every prompt
- Maintains consistency across task boundaries
- Enables agents to pick up exactly where previous agent left off

**Usage:**
- `/run-next-task` writes to context.json after completing task
- `/generate-task-file` reads context.json to pre-populate task metadata
- Agents can reference context.json for decisions

**Lifecycle:**
- Created when first task starts
- Updated after each task completion
- Archived after feature completion (`.claude/context-archive/`)
- Max size: 50KB (old context rotated to archive)

---

## Core Commands (7 Essential)

### 0. `/start-feature-planning` - Interactive BA Session with @Mario

**Purpose:** Gather comprehensive requirements BEFORE creating task specification

**When to Use:**
- ✅ Complex features (database changes, API endpoints, multi-service refactoring)
- ✅ Unclear requirements (vague user request needs clarification)
- ✅ High-risk changes (authentication, payments, GDPR-related)
- ⏭️  Skip for: Simple bug fixes, typos, documentation updates, config changes

**Logic:**
```markdown
1. User describes feature request
2. Mario (BA agent) conducts interactive Q&A:
   - Functional requirements (what should it do?)
   - Data model (what data needs storage?)
   - API contracts (new endpoints? formats?)
   - Integration points (which features affected?)
   - Edge cases (error handling? validation?)
   - Non-functional (performance? security?)
3. Mario searches codebase for impact analysis:
   - Grep: Search for related models/services/APIs
   - Read: Review existing implementations
   - Identify breaking changes (API contracts, DB schema)
   - List affected features and mitigation plans
4. Mario generates comprehensive task specification:
   - Problem statement
   - Implementation plan with TDD phases
   - Affected features & breaking changes
   - Test requirements (minimum test counts)
   - Acceptance criteria
   - Rollback plan
5. Mario returns specification to main thread
6. (Optional) SubagentStop hook suggests: "→ NEXT: Invoke @Egidio for architecture review"
7. User/Claude invokes @Egidio for architecture review
8. Task written to ARCHITECTURE_ROADMAP.md after review
9. Temporary plan files deleted
10. Report: "✅ Task created: DEV-BE-XXX at line [N] in ARCHITECTURE_ROADMAP.md"
```

**Example:**
See `.claude/agents/business-analyst.md` for full BA session transcript of "Add SSO Authentication" feature.

---

### 1. `/generate-task-file` - Create tasks.md from Roadmaps

**Purpose:** Convert ARCHITECTURE_ROADMAP.md task into executable checklist

**Logic:**
```markdown
1. Ask user: "Which task? (e.g., DEV-BE-72, DEV-FE-004, QUERY-20251125-001)"
2. Read appropriate roadmap:
   - DEV-BE-* → ARCHITECTURE_ROADMAP.md (backend section)
   - DEV-FE-* → ARCHITECTURE_ROADMAP.md (frontend section)
   - QUERY-* → QUERY_ISSUES_ROADMAP.md
3. Extract task phases and subtasks
4. Convert to checkbox format with TDD phases:
   ```
   [ ] DEV-BE-72: Expert Feedback System
     [ ] Phase 1: Database Schema (primo)
       [ ] 🔴 Write migration test
       [ ] 🟢 Create Alembic migration
       [ ] 🔵 Add indexes
     [ ] Phase 2: API Endpoints (ezio)
       [ ] 🔴 Write endpoint test
       [ ] 🟢 Implement POST /feedback/submit
       [ ] 🔵 Add validation
   ```
5. Save as tasks.md
6. Report: "tasks.md created for [TASK-ID] with [N] subtasks"
```

**Tiered Testing:** Applied per subtask (task tests → module tests → full regression at GREEN/BLUE)

---

### 2. `/run-next-task` - Execute ONE Task + Tiered Testing

**Purpose:** Implement next unchecked task with intelligent, risk-based testing

**Logic:**
```markdown
1. Read tasks.md
2. Find first "[ ]" line
3. Identify agent from parentheses: (ezio), (livia), (primo)
4. If architecture change → Consult egidio FIRST
5. Implement task following TDD:
   - If 🔴: Write failing test
   - If 🟢: Implement minimal code
   - If 🔵: Refactor code

6. TIERED TESTING STRATEGY:

   A. Run Task-Specific Tests First:
      - `uv run pytest <test_file> -v`
      - If fails → STOP and report

   B. Run Affected Module Tests (Risk-Based):
      - Database changes → `uv run pytest tests/models/ tests/api/ -v`
      - Service changes → `uv run pytest tests/services/<service_name>* -v`
      - API changes → `uv run pytest tests/api/ -v`
      - Frontend changes → `npm test <component>.test.tsx`
      - Docs/config → Skip (will run before commit)

   C. Full Regression (Only at Key Phases):
      - If 🟢 GREEN phase → Run full suite: `uv run pytest -n auto --tb=short`
      - If 🔵 BLUE phase → Run full suite: `uv run pytest -n auto --tb=short`
      - If 🔴 RED phase → Skip full regression (only new test)
      - If ANY test fails → STOP and report failure
      - Note: `-n auto` enables parallel execution (v1.3+)

7. On success:
   - Replace "[ ]" with "[X]" for that line
   - Save tasks.md
8. STOP (do not continue to next task)
9. Report:
   - Task complete: [description]
   - Task-specific tests: [X passed]
   - Affected module tests: [Y passed]
   - Full regression: [Z passed / SKIPPED (will run at GREEN/BLUE)]

CRITICAL:
- Implement ONE task only, then STOP
- NEVER proceed if ANY tests fail
- Report broken tests to user for review
- Full regression runs at GREEN/BLUE phases and before commit
```

**Safety Net:** Targeted tests per subtask + full regression at key checkpoints prevents breaking existing features while maintaining velocity

---

### 3. `/regression-test` - Run Full Test Suite (Parallelized in v1.3)

**Purpose:** Verify no existing features broken

**Logic:**
```markdown
1. Run full test suite with parallelization: `uv run pytest -n auto --tb=short -v`
   - `-n auto` uses pytest-xdist to run tests in parallel
   - Expected: 50% faster execution (2 min → 1 min typical)
   - Automatically detects CPU cores and scales workers
2. Parse results:
   - Total tests run
   - Passed count
   - Failed count (with test names)
   - Skipped count
3. Generate report:
   ```
   Regression Test Results:
   ========================
   ✅ Passed: 287/290 tests
   ❌ Failed: 3 tests
      - test_chat_session_persistence (tests/api/test_sessions.py:45)
      - test_knowledge_base_search (tests/services/test_search.py:12)
      - test_file_upload_validation (tests/api/test_files.py:78)
   ⏭️  Skipped: 0 tests

   Status: FAILED - Fix broken tests before proceeding
   ```
4. If failures:
   - STOP immediately
   - Show traceback summary for each failure
   - Suggest: "Review failures, fix, then re-run /regression-test"
5. If all pass:
   - Report: "✅ All regression tests passed - safe to continue"
```

**Usage:**
- Automatically triggered during GREEN/BLUE phases in `/run-next-task`
- Run manually anytime with `/regression-test`
- Always runs before `/prepare-commit`

---

### 4. `/prepare-commit` - Prepare Commit (NO Auto-Push)

**Purpose:** Prepare commit message for manual testing and commit

**Logic:**
```markdown
1. Open tasks.md
2. Count completed tasks: "[X]" count
3. Run `git status --porcelain`
4. For each changed file NOT represented in tasks.md:
   - Report to user: "Untracked change: <file>"
   - Ask: "Add to tasks.md as completed task? [Y/n]"
   - If yes: Append "[X] Update <file>" to tasks.md
5. Final Regression Test:
   - Run: `uv run pytest --cov=app --cov-report=term`
   - Verify coverage ≥49%
   - If below → WARN user, do NOT block
6. Generate commit message:
   ```
   feat(DEV-BE-XXX): [Feature summary]

   Changes:
   - app/api/endpoints.py: Added POST /feature endpoint
   - app/services/feature.py: Implemented business logic
   - tests/api/test_feature.py: Added 5 unit + 3 integration tests

   Test Results:
   - Task-specific tests: X passed
   - Regression tests: Y/Z passed
   - Coverage: XX.X% (threshold: ≥49%)

   Tasks: [N] completed (tasks.md)

   🤖 Generated with [Claude Code](https://claude.com/claude-code)

   Co-Authored-By: Claude <noreply@anthropic.com>
   ```
7. Stage files: `git add .`
8. Show commit message to user
9. STOP - Wait for manual testing
10. Report:
    ```
    Commit prepared (NOT committed):
    - [N] files staged
    - [M] tests passed
    - Coverage: XX.X%

    Next steps (MANUAL):
    1. Review changes: git diff --cached
    2. Run manual tests
    3. Commit: git commit -m "$(cat .git/COMMIT_EDITMSG)"
    4. Push: git push (when ready)
    ```
```

**Safety:** Never auto-commits or auto-pushes. Always requires manual review.

---

### 5. `/tdd-red`, `/tdd-green`, `/tdd-blue` - TDD Phase Commands

**Purpose:** Explicitly execute TDD phases (can be used standalone or within task)

**`/tdd-red` - Start RED Phase:**
```markdown
1. Ask user: "Feature name and test file path?"
2. Create test file with:
   - Import statements
   - Test class/function structure
   - Minimum 3 test cases (happy path, error, edge case)
3. Run test: `uv run pytest <test_file> -v`
4. Verify test FAILS
5. Report: "🔴 RED phase complete - test failing as expected"
```

**`/tdd-green` - Start GREEN Phase:**
```markdown
1. Ask user: "Test file from RED phase?"
2. Read test to understand requirements
3. Implement MINIMAL code to pass tests
4. Run test: `uv run pytest <test_file> -v`
5. Verify test PASSES
6. Run regression tests: `uv run pytest --tb=short`
7. Report: "🟢 GREEN phase complete - tests passing, no regressions"
```

**`/tdd-blue` - Start BLUE Phase:**
```markdown
1. Ask user: "Feature file to refactor?"
2. Improve code quality:
   - Add error handling
   - Extract reusable functions
   - Add type hints and docstrings
3. After EACH change: Run tests
4. Run regression tests: `uv run pytest --tb=short`
5. Report: "🔵 BLUE phase complete - code refactored, tests green"
```

---

### 6. `/code-review` - KISS & Best Practices Check

**Purpose:** Check for overengineering, best practices, code smell

**Logic:**
```markdown
1. Ask user: "File or directory to review?"
2. Read code
3. Check for:
   - KISS principle: Is it simpler than it needs to be?
   - Overengineering: Unused abstractions, premature optimization
   - Task adherence: Did we drift from original task?
   - Best practices: Following Python/FastAPI conventions?
   - Cleanup: Temp files, commented code, debug prints
   - Italian language: UI strings in Italian?
4. Generate report:
   ```
   Code Review Results:
   ===================

   ✅ KISS Principle: Code is appropriately simple
   ⚠️  Overengineering: Found 1 issue
      - CacheService uses 3 abstraction layers for simple dict lookup
      - Suggestion: Simplify to single Redis call

   ✅ Task Adherence: Matches DEV-BE-72 requirements
   ✅ Best Practices: Follows FastAPI conventions
   ❌ Cleanup: Found 2 issues
      - test_debug.py should be removed
      - print() statement in line 45 should use logger

   ✅ Italian Language: All UI strings in Italian

   Overall: 4/6 checks passed - Address warnings before commit
   ```
5. Report findings to user
```

**Usage:** Run before `/prepare-commit` to catch issues early

---

## Enhanced claude.md Directives

**Add to existing claude.md:**

```markdown
# Task Execution Rules

## Core Workflow
1. Use /start-feature-planning to gather requirements (complex features only)
2. Use /generate-task-file to create tasks.md from roadmap
3. Use /run-next-task to execute ONE task at a time
4. STOP after each task - wait for human review
5. Use /prepare-commit when all tasks complete (NO auto-push)

## Tiered Testing Strategy (MANDATORY)
After EVERY subtask implementation:

**Tier 1 - Task-Specific Tests (Always):**
- Run tests for the code you just wrote
- If fails → STOP immediately

**Tier 2 - Affected Module Tests (Risk-Based):**
- Database changes → tests/models/ + tests/api/
- Service changes → tests/services/<service_name>*
- API changes → tests/api/
- Frontend changes → Component test suite
- Docs/config → Skip until commit

**Tier 3 - Full Regression (Key Phases Only):**
- 🟢 GREEN phase → Full suite: `uv run pytest --tb=short`
- 🔵 BLUE phase → Full suite: `uv run pytest --tb=short`
- 🔴 RED phase → Skip (only run new test)
- Before commit → Always run full suite

**Critical Rules:**
- NEVER proceed if ANY test fails at ANY tier
- Report failures to user for review
- Full regression MUST pass before moving to next task phase

## TDD Enforcement (ADR-013)
Every task MUST follow:
1. 🔴 RED: Write failing test FIRST + run task-specific test only
2. 🟢 GREEN: Implement minimal code to pass + run affected module tests + **FULL REGRESSION**
3. 🔵 BLUE: Refactor while keeping tests green + **FULL REGRESSION**
4. ✅ Before commit: Final full regression + coverage check

## Task Sources
- **Strategic development:** ARCHITECTURE_ROADMAP.md (DEV-BE-XXX, DEV-FE-XXX)
- **Expert feedback:** QUERY_ISSUES_ROADMAP.md (QUERY-YYYYMMDD-XXX)
- Use /generate-task-file to convert either into tasks.md

## Manual Testing Requirement
- Commits are PREPARED but NOT executed automatically
- Human MUST perform manual testing before commit/push
- Use /prepare-commit to stage and generate message
- Human executes: git commit && git push

## Quality Gates (All Required)
- [ ] All task-specific tests pass (Tier 1)
- [ ] All affected module tests pass (Tier 2)
- [ ] Full regression tests pass at GREEN/BLUE phases (Tier 3)
- [ ] Final regression tests pass before commit (MANDATORY)
- [ ] Coverage ≥49%
- [ ] Code quality checks pass (`./scripts/check_code.sh`)
- [ ] Manual testing complete
- [ ] Code review passed (/code-review)
```

---

## Hook-Based Agent Orchestration (Recommended - Phase 1 Priority)

### Why Hooks?

**Problem:** Agents cannot invoke other agents directly due to Claude Code's flat architecture.
- ❌ @Mario cannot programmatically invoke @Egidio
- ❌ @Egidio cannot spawn @Ezio for implementation
- ✅ Only the main Claude thread can orchestrate agent invocations

**Solution:** SubagentStop hooks provide **suggestions** (not automatic invocation).

### How It Works

**1. SubagentStop Hook Fires**
When an agent completes (e.g., @Mario finishes requirements gathering), a hook script executes.

**2. Hook Prints Suggestion to STDOUT**
The hook output appears in the Claude Code transcript:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ @business-analyst completed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 SUGGESTED NEXT STEP:
   @architect review the requirements and assess architecture impact

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**3. User/Claude Acts on Suggestion**
The main Claude thread (or user) sees the suggestion and invokes the next agent:
```
Human: @Egidio please review the requirements and assess architecture impact
```

### Benefits

- ✅ **Reduces cognitive load** - No need to remember workflow steps
- ✅ **Prevents forgotten steps** - Hook reminds you what comes next
- ✅ **Keeps human in control** - Suggestions, not automation
- ✅ **Extensible** - Can evolve to queue-based system later

### Implementation Script

**Create `.claude/hooks/suggest-next-agent.sh`:**
```bash
#!/bin/bash
# SubagentStop hook - Suggests next agent in workflow
agent="$1"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ @${agent} completed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

case "$agent" in
  business-analyst)
    echo "🎯 SUGGESTED NEXT STEP:"
    echo "   @architect review the requirements and assess architecture impact"
    ;;
  architect)
    echo "🎯 SUGGESTED NEXT STEP:"
    echo "   @backend-expert (for backend) OR @frontend-expert (for frontend) to implement"
    ;;
  backend-expert|frontend-expert|database-designer)
    echo "🎯 SUGGESTED NEXT STEP:"
    echo "   @test-generation to validate coverage and test quality"
    ;;
  test-generation)
    echo "🎯 SUGGESTED NEXT STEP:"
    echo "   Run /code-review before preparing commit"
    ;;
  *)
    echo "🎯 Workflow step complete. Check tasks.md for next task."
    ;;
esac

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

**Configure in `.claude/settings.local.json`:**
```json
{
  "hooks": {
    "SubagentStop": ".claude/hooks/suggest-next-agent.sh"
  }
}
```

### Implementation Phases

**Phase 1: Simple Suggestions** (Week 1 - HIGH PRIORITY)
- Create `.claude/hooks/suggest-next-agent.sh` bash script (above)
- Configure SubagentStop hook in `.claude/settings.local.json`
- Map agent completions → next agent suggestions
- **Effort:** 2-3 hours
- **Value:** High - Prevents forgotten workflow steps

**Phase 2: Queue-Based Workflow** (Future - Optional)
- Add `.claude/workflow-queue.json` for complex dependencies
- Track parallel vs. sequential tasks
- Support multi-agent coordination
- **Effort:** 8-10 hours
- **Value:** High for complex features
- **Status:** Defer until Phase 1 proven

**Current Status:** Phase 1 recommended for Week 1 implementation (v1.3 update)

---

## Workflow Example: DEV-BE-72 Expert Feedback System

### Step 1: Generate Tasks from Roadmap
```
Human: /generate-task-file
Claude: Which task? (e.g., DEV-BE-72)
Human: DEV-BE-72
Claude: ✅ tasks.md created for DEV-BE-72 with 15 subtasks
```

### Step 2: Execute First Task (RED Phase)
```
Human: /run-next-task
Claude:
  Implementing: Phase 1 - Database Schema (primo)
  🔴 Writing migration test...
  ✅ Test written: test_expert_feedback_migration()

  Running Tier 1 (Task-Specific Tests):
  ✅ Test FAILS as expected (table doesn't exist) - RED phase validated

  Running Tier 2 (Affected Module Tests):
  ⏭️  SKIPPED - RED phase only validates new test fails

  Running Tier 3 (Full Regression):
  ⏭️  SKIPPED - RED phase doesn't require full regression

  Task complete: [X] 🔴 Write migration test
  [STOPS - waits for next command]
```

### Step 3: Continue Through Tasks (GREEN Phase with Regression)
```
Human: /run-next-task
Claude:
  Implementing: Phase 1 - Database Schema (primo)
  🟢 Creating Alembic migration...
  ✅ Migration created: 20251126_add_expert_feedback.py

  Running Tier 1 (Task-Specific Tests):
  ✅ Migration test PASSES

  Running Tier 2 (Affected Module Tests):
  Database change detected → Running tests/models/ + tests/api/
  ✅ All 45 affected module tests passed

  Running Tier 3 (Full Regression):
  🟢 GREEN phase → Full suite required
  ❌ REGRESSION FAILURE!

  Failed Tests (3):
  - test_user_authentication() - IntegrityError: column users.role
  - test_create_session() - AttributeError: User has no attribute 'role'
  - test_get_user_profile() - KeyError: 'role'

  STOPPED - Fix regressions before continuing
```

### Step 4: Human Reviews and Fixes
```
Human: [Reviews failures, realizes migration added user.role but broke existing code]
Human: [Fixes User model to include role field]
Human: /regression-test
Claude:
  Running full test suite...
  ✅ All 290 tests passed

  Safe to continue!
```

### Step 5: Continue After Fix (BLUE Phase with Regression)
```
Human: /run-next-task
Claude:
  Implementing: Phase 1 - Database Schema (primo)
  🔵 Adding indexes and constraints...
  ✅ Added GIN index on feedback_text
  ✅ Added foreign key constraints

  Running Tier 1 (Task-Specific Tests):
  ✅ All migration tests pass

  Running Tier 2 (Affected Module Tests):
  Database change detected → Running tests/models/ + tests/api/
  ✅ All 45 affected module tests passed

  Running Tier 3 (Full Regression):
  🔵 BLUE phase → Full suite required
  ✅ All 290 tests passed

  Task complete: [X] 🔵 Add indexes
  [STOPS]
```

### Step 6: Prepare Commit (After All Tasks)
```
Human: /prepare-commit
Claude:
  Checking tasks.md... 15/15 tasks completed ✅
  Checking git status... 8 files changed

  Untracked change: app/models/user.py
  Add to tasks.md? [Y/n]
Human: y
Claude:
  Added: [X] Update User model with role field

  Running final regression tests...
  ✅ All 290 tests passed

  Running coverage check...
  Coverage: 51.2% (threshold: ≥49%) ✅

  Commit prepared (NOT committed):
  - 9 files staged
  - 290 tests passed
  - Coverage: 51.2%

  Next steps (MANUAL):
  1. Review changes: git diff --cached
  2. Run manual tests:
     - Test expert feedback submission
     - Test role-based access control
     - Test database constraints
  3. Commit: git commit -F .git/COMMIT_EDITMSG
  4. Push: git push
```

### Step 7: Human Manual Testing and Commit
```
Human: [Runs manual tests - all pass]
Human: git commit -F .git/COMMIT_EDITMSG
Human: git push origin DEV-BE-72-expert-feedback-system
```

---

## Key Differences from Reddit Approach

| Reddit Approach | PratikoAI Adaptation |
|-----------------|---------------------|
| plan-v001.md, plan-v002.md | ARCHITECTURE_ROADMAP.md (existing) |
| Automatic commits | MANUAL commits after testing |
| No regression testing | **Tiered testing strategy** |
| Generic task naming | DEV-BE-XXX, QUERY-XXX conventions |
| Single roadmap | Two sources (dev + expert feedback) |
| Auto-push to git | Human controls push timing |

## Testing Strategy Evolution

| Original Proposal (v1.0) | Updated Proposal (v1.1) |
|--------------------------|-------------------------|
| ❌ Full regression after EVERY subtask | ✅ Tiered testing based on TDD phase |
| ⏱️  ~2 minutes per subtask | ⏱️  ~5 sec (RED), ~30-120 sec (GREEN/BLUE) |
| 😤 High friction, developer frustration | ✅ Fast feedback, safety at checkpoints |
| ❌ Same testing for docs vs. DB migrations | ✅ Risk-based: docs skip, DB gets full suite |
| ✅ Maximum safety | ✅ Balanced safety + velocity |

---

## Implementation Timeline

### Week 1: Core Commands + v1.3 Enhancements (Foundation)

**Phase 1A: v1.3 Quick Wins** (6 hours - HIGH PRIORITY)
- [ ] Context Handoff System (2-3 hours)
  - [ ] Create `.claude/context.json` schema
  - [ ] Update `/run-next-task` to write context after completion
  - [ ] Update `/generate-task-file` to read context
  - [ ] Test: Verify 30% token reduction on sample task
- [ ] SubagentStop Hooks (2-3 hours)
  - [ ] Create `.claude/hooks/suggest-next-agent.sh` bash script
  - [ ] Configure SubagentStop hook in `.claude/settings.local.json`
  - [ ] Test: Verify suggestions appear after agent completion
- [ ] Test Parallelization (1 hour)
  - [ ] Add `pytest-xdist` to dependencies (`uv pip install pytest-xdist`)
  - [ ] Update `/regression-test` command with `-n auto` flag
  - [ ] Update `/run-next-task` Tier 3 tests with `-n auto`
  - [ ] Test: Measure before/after test execution time

**Phase 1B: Core Commands** (Remaining Week 1)
- [ ] Create 6 essential commands
  - [ ] /generate-task-file
  - [ ] /run-next-task (with tiered regression tests)
  - [ ] /prepare-commit (no auto-push)
  - [ ] /regression-test (with parallelization)
  - [ ] /code-review
  - [ ] /tdd-red, /tdd-green, /tdd-blue
- [ ] Enhance claude.md with task rules
- [ ] Test workflow on small task (e.g., bug fix)

### Week 2: Integration with Roadmaps
- [ ] Test /generate-task-file with ARCHITECTURE_ROADMAP.md
- [ ] Test /generate-task-file with QUERY_ISSUES_ROADMAP.md
- [ ] Verify DEV-BE-XXX and QUERY-XXX task parsing
- [ ] Test full workflow on DEV-BE-72

### Week 3: Documentation & Training
- [ ] Create .claude/workflows/task-based-development.md
- [ ] Create .claude/workflows/regression-testing.md
- [ ] Train agents (ezio, livia, primo) on new workflow
- [ ] Document lessons learned

---

## Success Metrics (Measure After 1 Month)

1. **Regression Prevention:**
   - Target: Zero "breaking existing features" incidents
   - Baseline: Currently happening frequently

2. **Context Drift Reduction:**
   - Target: 80% of tasks completed without drift
   - Measure: Tasks completed vs. tasks attempted

3. **Token Efficiency:**
   - Target: 30% reduction in token usage per task
   - Reddit users report 70% reduction

4. **Bug Escape Rate:**
   - Target: <2 bugs per feature in manual testing
   - Baseline: 9 bugs in DEV-BE-72

5. **Developer Velocity:**
   - Target: Maintain current velocity
   - No slowdown from additional regression testing

---

## Risk Mitigation

### Risk 1: Regression Tests Too Slow ✅ MITIGATED
**Impact:** /run-next-task takes too long
**Mitigation (IMPLEMENTED via Tiered Testing):**
- ✅ RED phase: Only run new test (fastest)
- ✅ GREEN/BLUE phases: Run affected modules first, then full suite
- ✅ Docs/config changes: Skip regression until commit
- Additional options if still slow:
  - Run fast unit tests first (--lf for last failed)
  - Parallelize tests with pytest-xdist
  - Use pytest-split for distributed execution

### Risk 2: False Positive Failures
**Impact:** Regression tests fail due to test flakiness
**Mitigation:**
- Fix flaky tests immediately (high priority)
- Add retry logic for network-dependent tests
- Document known flaky tests in .flaky-tests.txt

### Risk 3: Workflow Too Rigid
**Impact:** Developers bypass workflow for quick fixes
**Mitigation:**
- Allow /run-next-task --skip-regression for trivial changes
- Provide /quick-fix command for small tweaks
- Keep manual override option available

---

## Rollback Plan

If workflow doesn't work after 2 weeks:

1. Keep regression testing requirement (proven value)
2. Remove task-based execution (revert to free-form)
3. Keep /prepare-commit (manual testing is valuable)
4. Archive commands in .claude/commands/archive/

---

## Reddit Article Integration Summary (v1.3)

### What We Adopted from the Reddit Article

After comprehensive analysis of the Reddit article "97% of Developers Kill Their Claude Code Agents" and comparison with PratikoAI's existing workflow, we adopted **3 tactical enhancements**:

#### 1. Context Handoff System (`.claude/context.json`)
**Why:** Reduces token usage by 30% through structured inter-task communication
**How:** Maintains task state, previous outputs, and shared context across task boundaries
**Status:** Phase 1A - Week 1 implementation (2-3 hours)

#### 2. SubagentStop Hooks (Agent Completion Suggestions)
**Why:** Prevents forgotten workflow steps, reduces cognitive load
**How:** Bash script suggests next agent after completion (Mario → Egidio → Ezio/Livia)
**Status:** Phase 1A - Week 1 implementation (2-3 hours)

#### 3. Test Parallelization (pytest-xdist)
**Why:** 50% faster test execution without changing test strategy
**How:** Use `pytest -n auto` to distribute tests across CPU cores
**Status:** Phase 1A - Week 1 implementation (1 hour)

### What We Rejected (And Why)

| Reddit Pattern | PratikoAI Decision | Rationale |
|----------------|-------------------|-----------|
| **Auto-commit/push** | ❌ REJECTED | Production safety requires manual testing gate |
| **plan-vXXX naming** | ❌ REJECTED | Existing conventions (DEV-BE-XXX, QUERY-XXX) established |
| **4 commands** | ✅ ADAPTED | Expanded to 7 commands for TDD phases and code review |
| **Single roadmap** | ✅ ADAPTED | Two sources: ARCHITECTURE_ROADMAP.md + QUERY_ISSUES_ROADMAP.md |

### What Makes PratikoAI Different (Our Advantages)

1. **10 Specialized Agents** (vs. Reddit's single agent with role switching)
   - Domain expertise: @Mario (BA), @Egidio (Architect), @Ezio (Backend), @Livia (Frontend), etc.
   - Specialized knowledge per domain

2. **Sophisticated Testing Strategy** (vs. Reddit's basic regression)
   - Tiered testing: Task-specific → Module → Full regression
   - Risk-based test selection
   - TDD phase enforcement (RED/GREEN/BLUE)

3. **Business Analyst Phase** (not in Reddit article)
   - Interactive requirements gathering with @Mario
   - Codebase impact analysis
   - Breaking change detection

4. **Production-Grade Safety** (vs. Reddit's rapid prototyping focus)
   - Manual commit/push gates
   - Multiple quality checkpoints
   - GDPR compliance considerations

### Integration Results

| Metric | Before v1.3 | After v1.3 (Expected) |
|--------|-------------|----------------------|
| **Token Usage** | Baseline | -30% (via context.json) |
| **Test Execution** | ~2 min full suite | ~1 min (via pytest-xdist) |
| **Forgotten Steps** | Occasional | 0 incidents (via hooks) |
| **Workflow Complexity** | Moderate | Same (enhancements are additive) |

### Success Criteria (Measure After 2 Weeks)

- [ ] Context.json reduces prompt size by 30%
- [ ] Test parallelization achieves 50% speedup
- [ ] Hooks prevent all forgotten agent invocations
- [ ] No increase in workflow friction
- [ ] Developer feedback: "Enhancements feel natural"

### Full Analysis Reference

Detailed comparison available in: **REDDIT_ARTICLE_COMPARISON_ANALYSIS.md** (comprehensive 9-part analysis)

---

## Next Actions

1. **Review this proposal** - Stakeholder approval of v1.3 enhancements
2. **Implement Phase 1A (Week 1)** - Context handoff, hooks, test parallelization (6 hours)
3. **Test enhancements** - Measure token reduction, test speedup, hook effectiveness
4. **Create Week 1B commands** - Core slash commands (/run-next-task, /regression-test, etc.)
5. **Iterate based on metrics** - Adjust after real-world usage
6. **Document lessons learned** - Update proposal with actual results

---

## Questions for Stakeholder Review

1. ✅ Confirmed: No auto-commit/push - manual testing required
2. ✅ Confirmed: Tiered testing with full regression at GREEN/BLUE phases
3. ✅ Confirmed: Use DEV-BE-XXX naming (not plan-vXXX)
4. ✅ Confirmed: Integrate QUERY_ISSUES_ROADMAP.md
5. ✅ RESOLVED: Tiered approach - task tests always, affected module tests per risk, full regression at GREEN/BLUE + commit
6. ❓ Question: Should we allow /run-next-task --skip-regression flag for emergencies?
7. ✅ RESOLVED: Risk-based affected test detection (database→models+api, service→services/*, etc.)

---

**Document Status:** DRAFT v1.3 - Integrated Reddit Article Enhancements
**Next Step:** Implement Phase 1A (context.json, hooks, pytest-xdist) - 6 hours
**Estimated Implementation:** Week 1 Phase 1A (6 hours) + 3 weeks for full workflow (6-8 hours/week)
**Changelog:**
- v1.0 (2025-11-26): Initial draft with full regression after every subtask
- v1.1 (2025-11-26): Refined to tiered testing strategy based on stakeholder feedback
- v1.2 (2025-11-26): Added Business Analyst phase (@Mario) + Corrected agent invocation architecture (agents cannot invoke other agents; hooks provide suggestions instead)
- v1.3 (2025-11-29): Integrated 3 tactical enhancements from Reddit article analysis:
  - Context Handoff System (context.json) for 30% token reduction
  - SubagentStop Hooks (agent completion suggestions)
  - Test Parallelization (pytest-xdist) for 50% faster tests
  - Updated Implementation Timeline with Phase 1A quick wins
  - Added comprehensive Reddit Article Integration Summary
