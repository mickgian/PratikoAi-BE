# Human-in-the-Loop Git Workflow

**Last Updated:** 2025-11-19
**Authority:** Mick (Michele Giannone) authorizes all commits and pushes

---

## Git Operations Authority

**Agents CAN:**
- ✅ `git checkout -b TICKET-NUMBER-name` - Create feature branches
- ✅ `git checkout develop` - Switch to develop
- ✅ `git pull origin develop` - Update from remote
- ✅ `git add .` or `git add <files>` - Stage changes
- ✅ `git status` - Check status
- ✅ `git diff` - View changes
- ✅ Read/Write/Edit files
- ✅ Run tests

**Agents CANNOT:**
- ❌ `git commit` - Only Mick commits
- ❌ `git push` - Only Mick pushes

**Mick (human) MUST:**
- ✅ Review staged changes
- ✅ Authorize and execute `git commit`
- ✅ Execute `git push`
- ✅ Signal completion

---

## Complete Workflow

### Phase 1: Agent Prepares Changes

**Agent (Livia, Ezio, etc.):**

```bash
# 1. Create feature branch from develop
git checkout develop
git pull origin develop
git checkout -b TICKET-NUMBER-descriptive-name

# 2. Make file changes using Write/Edit tools
# (Agent modifies files)

# 3. Stage all changes
git add .

# 4. Verify what's staged
git status
git diff --staged

# 5. Run tests
npm test  # or pytest
```

**Agent signals:**
```
Changes staged, ready for commit:

Branch: TICKET-NUMBER-descriptive-name
Staged files:
- app/services/foo.py (added new feature)
- tests/test_foo.py (added tests)

Tests: ✅ All passing
Coverage: ✅ 69.5%+
Linting: ✅ Passing

Waiting for Mick to review, commit, and push.
```

### Phase 2: Mick Commits and Pushes

**Mick (human):**

```bash
# 1. Review staged changes
git status
git diff --staged

# 2. Commit (staged changes already added by agent)
git commit -m "TICKET-NUMBER: Brief description

- Change 1
- Change 2

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# 3. Push to remote
git push -u origin TICKET-NUMBER-descriptive-name
```

**Mick signals:**
```
TICKET-NUMBER-descriptive-name pushed
```

Example: `DEV-008-change-colors pushed`

### Phase 3: DevOps Creates PR

**Silvano (@Silvano):**

Waits for Mick's signal, then:

```bash
# 1. Fetch latest
git fetch --all

# 2. Verify branch exists
git ls-remote origin TICKET-NUMBER-descriptive-name

# 3. Create PR
gh pr create --base develop --head TICKET-NUMBER-descriptive-name \
  --title "TICKET-NUMBER: Description" \
  --body "..."
```

---

## Multi-Repository Tasks

### Agent Workflow

**Agent prepares BOTH repositories:**

```bash
# Backend
cd /Users/micky/PycharmProjects/PratikoAi-BE
git checkout develop && git pull origin develop
git checkout -b TICKET-NUMBER-descriptive-name
# Make changes
git add .

# Frontend
cd /Users/micky/PycharmProjects/PratikoAi-BE/web
git checkout develop && git pull origin develop
git checkout -b TICKET-NUMBER-descriptive-name
# Make changes
git add .
```

**Agent signals:**
```
Changes staged, ready for commit (multi-repo):

Backend: TICKET-NUMBER-descriptive-name
Staged:
- app/core/prompts/system.md
- app/services/context_builder_merge.py

Frontend: TICKET-NUMBER-descriptive-name
Staged:
- src/components/ui/source-citation.tsx
- src/components/ui/__tests__/source-citation.test.tsx

Tests: ✅ All passing (both repos)

Waiting for Mick to commit and push both repositories.
```

### Mick Commits and Pushes BOTH

```bash
# Backend
cd /Users/micky/PycharmProjects/PratikoAi-BE
git commit -m "TICKET-NUMBER: Backend changes..."
git push -u origin TICKET-NUMBER-descriptive-name

# Frontend
cd /Users/micky/PycharmProjects/PratikoAi-BE/web
git commit -m "TICKET-NUMBER: Frontend changes..."
git push -u origin TICKET-NUMBER-descriptive-name
```

**Mick signals:**
```
TICKET-NUMBER-descriptive-name pushed (both repos)
```

---

## Branch Naming Convention

**Format:** `TICKET-NUMBER-descriptive-name`

**Examples:**
- ✅ `DEV-FE-002-ui-source-citations`
- ✅ `DEV-BE-67-faq-embeddings-migration`
- ✅ `DEV-008-change-colors`
- ❌ `feature/citations` (missing ticket number)
- ❌ `DEV-FE-002` (missing description)

---

## PR Target Branch

**ALWAYS:** `develop`
**NEVER:** `master`

```bash
gh pr create --base develop --head TICKET-NUMBER-descriptive-name
```

---

## Agent Completion Signal Template

```
Changes staged, ready for commit:

Task: TICKET-NUMBER - Brief description
Branch: TICKET-NUMBER-descriptive-name
Repository: backend | frontend | both

Staged files:
- path/to/file1.py (description)
- path/to/file2.tsx (description)

Tests: ✅ All passing
Linting: ✅ Ruff/ESLint passing
Type checks: ✅ MyPy/TypeScript passing
Coverage: ✅ 69.5%+

Summary:
- [Key change 1]
- [Key change 2]

Waiting for Mick to commit and push.
```

## Mick Completion Signal Template

**Simple format:**
```
TICKET-NUMBER-descriptive-name pushed
```

**Examples:**
- `DEV-008-change-colors pushed`
- `DEV-FE-002-ui-source-citations pushed`
- `DEV-BE-67-faq-embeddings-migration pushed (both repos)` (multi-repo)

---

## Why This Workflow?

1. **Agent Efficiency:** Agents prepare everything (branch, changes, staging)
2. **Human Gate:** Mick controls what enters git history (commit/push)
3. **Clean History:** All commits require human authorization
4. **Quality Control:** Mick reviews before commit
5. **Accountability:** Mick's approval on every commit
6. **Fast Iteration:** Agents don't wait for approval to stage changes

---

**Document Status:** 🟢 ACTIVE
**Enforced By:** All subagents (Livia, Ezio, Silvano, Tiziano, etc.)
**Maintained By:** PratikoAI Architect (@Egidio)
**Last Updated:** 2025-11-19
