# PratikoAI Subagent Tool Permissions

**Last Updated:** 2025-11-17
**Enforcement:** STRICT - Violations will halt execution
**Purpose:** Define which tools subagents can use autonomously

---

## Permission Levels

### 🟢 ALWAYS ALLOWED (No approval needed)

Tools that subagents can use autonomously without asking permission:

**File Operations:**
- ✅ `Read` - Read any file in project
- ✅ `Grep` - Search for patterns in code
- ✅ `Glob` - Find files by pattern
- ✅ `Edit` - Modify existing files
- ✅ `Write` - Create new files (with notification)

**Code Analysis:**
- ✅ `ruff check` - Lint code (read-only check)
- ✅ `ruff format` - Format code
- ✅ `mypy` - Type checking

**Git Read Operations:**
- ✅ `git status` - Check repository status
- ✅ `git diff` - View changes
- ✅ `git log` - View commit history
- ✅ `git branch` - List branches

**Testing:**
- ✅ `pytest` - Run tests (if permitted by task)

**Communication:**
- ✅ `Slack notifications` - ALWAYS send automatically (NO approval needed)
- ✅ `SlackNotificationService` - Send notifications for milestones, code review, PR creation
- ✅ Automatic notifications for: code ready, commits, pushes, PR creation, task completion

---

### 🟡 NOTIFICATION REQUIRED (Do it, but notify)

Tools that require Slack notification but can proceed:

**Git Write Operations:**
- 🟡 `git add` - Stage files → Notify before commit
- 🟡 `git checkout -b` - Create branch → Notify branch creation

**Code Quality Fixes:**
- 🟡 `ruff check --fix` - Auto-fix lint issues → Notify changes made
- 🟡 Pre-commit hooks - Auto-formatting → Notify if files modified

---

### 🔴 APPROVAL REQUIRED (Ask first!)

Tools that require explicit human approval before execution:

**Git Write Operations:** (temporary reuiqre human approval, might be moved to Notification required later)
- 🔴 `git commit` - Create commit → **Slack notification MANDATORY**
- 🔴 `git push` - Push to remote → Notify after push

**Destructive Git Operations:**
- 🔴 `git reset --hard` - **NEVER** use without approval
- 🔴 `git push --force` - **NEVER** use without approval
- 🔴 `git rebase` - Ask first
- 🔴 `git merge` - Ask first (except fast-forward)

**Deployment & Infrastructure:**
- 🔴 `docker-compose up` - Ask first
- 🔴 Database migrations - **ALWAYS** ask first
- 🔴 Environment variable changes - Ask first

**External Services:**
- 🔴 API calls to external services (EXCEPT Slack - see below)
- 🔴 npm/pip install (dependency changes) - Ask first

**IMPORTANT - Slack Exception:**
- ✅ Slack notifications are ALWAYS ALLOWED without approval
- ✅ Send automatically at key milestones (code ready, commits, PRs)
- ✅ DO NOT wait for human approval to send Slack notifications
- ✅ Notifications are for visibility, not approval requests

---

## Tool-Specific Rules

### Ruff (Linting & Formatting)

**Permitted Uses:**
```bash
# ✅ ALLOWED - Check for issues (read-only)
uv run ruff check .

# ✅ ALLOWED - Auto-fix safe issues + NOTIFY
uv run ruff check . --fix

# ✅ ALLOWED - Format code + NOTIFY
uv run ruff format .
```

**Workflow:**
1. Run `ruff check .` to identify issues
2. Run `ruff check . --fix` to auto-fix
3. Run `ruff format .` to format
4. If files changed, include in commit with note: "Applied Ruff auto-fixes"

**Notification Requirement:**
- If ruff modifies files → Send Slack notification listing changed files
- Include in commit message: "Applied Ruff formatting/fixes"

### MyPy (Type Checking)

**Permitted Uses:**
```bash
# ✅ ALLOWED - Check types (read-only)
uv run mypy app/
```

**NOT Allowed:**
- Generating type stubs autonomously (ask first)

### Pytest (Testing)

**Permitted Uses:**
```bash
# ✅ ALLOWED - Run tests
uv run pytest

# ✅ ALLOWED - Run tests with coverage
uv run pytest --cov=app --cov-report=html
```

**Requirement:**
- Must run tests BEFORE committing if task involves code changes
- Report test failures in Slack notification

### Git Operations

**Commit Workflow:**
```bash
# 1. Stage files (NOTIFICATION REQUIRED)
git add <files>

# 2. Send Slack notification: "Code ready for commit"

# 3. Wait for approval OR auto-proceed after 2 minutes

# 4. Commit (HUMAN PERMISSION REQUIRED)
git commit -m "message"

# 5. Send Slack notification: "Code committed, ready to push"

# 6. Push (HUMAN PERMISSION REQUIRED)
git push origin <branch>

# 7. Send Slack notification: "Code pushed, creating PR"
```

**PR Creation:**
```bash
# ✅ ALLOWED - Create PR to develop
gh pr create --base develop --head <branch>

# ❌ FORBIDDEN - Create PR to master
gh pr create --base master --head <branch>  # VIOLATION!
```

---

## Notification Protocol

### Slack Notification Requirements

**Before Commit:**
```
📝 CODE READY FOR REVIEW

Task: DEV-BE-XXX
Branch: <branch-name>
Changes:
- file1.py (modified)
- file2.py (created)

Ruff fixes applied: Yes/No
Tests passed: Yes/No/Skipped

Awaiting approval to commit (auto-proceed in 2 min)
```

**After Push:**
```
✅ CODE PUSHED

Task: DEV-BE-XXX
Branch: <branch-name>
Commits: X commit(s)

Next: Creating PR to develop
```

---

## Violation Handling

### If Subagent Uses Forbidden Tool

**Immediate Action:**
1. Halt execution
2. Send Slack alert: "VIOLATION: Used forbidden tool"
3. Wait for human intervention
4. Do NOT proceed with task

**Example Violations:**
- Running `git push --force`
- Running `git reset --hard`
- Modifying `.env` files
- Installing dependencies without approval

### If Subagent Skips Notification

**Immediate Action:**
1. Retrospectively send notification: "Late notification - code already committed"
2. Log violation for Scrum Master review
3. Do NOT repeat - add to workflow checklist

---

## Permission Exceptions

### DevOps Subagent (@Dario)

**Additional Permissions:**
- ✅ Create PRs autonomously
- ✅ Monitor CI/CD pipelines
- ✅ Read GitHub Actions logs

**Still Forbidden:**
- ❌ Merge PRs
- ❌ Deploy to production
- ❌ Modify GitHub Secrets

### Test Generation Subagent (@Clelia)

**Additional Permissions:**
- ✅ Run test coverage analysis
- ✅ Generate test files
- ✅ Modify pytest configuration (with notification)

---

## Decision Matrix

| Tool | Read-Only | Modifies Files | Git Write | External API |
|------|-----------|----------------|-----------|--------------|
| Read | ✅ Allowed | - | - | - |
| Edit | - | ✅ Allowed | - | - |
| Slack notifications | - | - | - | ✅ ALWAYS ALLOWED |
| ruff check | ✅ Allowed | - | - | - |
| ruff check --fix | - | 🟡 Notify | - | - |
| git add | - | - | 🟡 Notify | - |
| git commit | - | - | 🔴 Ask + Slack | - |
| git push --force | ❌ FORBIDDEN | - | ❌ FORBIDDEN | - |
| npm install | ❌ Ask first | 🔴 Ask | - | 🔴 External |
| Other External APIs | ❌ Ask first | - | - | 🔴 Ask first |

---

## Auto-Approval Timeout

**Default Timeout:** 10 minutes

**Workflow:**
1. Subagent sends Slack notification: "Code ready for commit"
2. Wait for human response
3. If no response after 10 minutes → Auto-proceed
4. Log decision: "Auto-proceeded after timeout"

**Human Can:**
- Respond "approve" → Immediate proceed
- Respond "hold" → Wait indefinitely
- Respond "reject" → Abort operation

---

## Version History

| Date | Change | Reason |
|------|--------|--------|
| 2025-11-17 | Initial permissions file created | Sprint 1: Define tool usage policies |

---

**Status:** 🔴 CRITICAL - MANDATORY COMPLIANCE
**Maintained By:** PratikoAI Scrum Master (@Ottavio) + Architect (@Egidio)
**Violations:** Report to Slack immediately
