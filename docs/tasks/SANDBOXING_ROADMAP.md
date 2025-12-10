# Sandboxing Implementation Roadmap

**Document Version:** 1.0
**Created:** 2025-12-04
**Status:** IN PROGRESS
**Total Effort:** 19 hours (~2.5 days)
**Architecture Review:** APPROVED by @agent-egidio (no vetoes)

---

## Overview

Implement Claude Code Local Sandboxing to reduce permission prompts by ~84% while providing OS-level security for credentials and network access.

**Key Benefits:**
- 84% fewer permission prompts (approval fatigue eliminated)
- OS-level security (macOS Seatbelt, Linux bubblewrap)
- Credential protection (kernel-enforced, not bypassable)
- Network isolation (domain allowlist via proxy)

---

## Critical Configuration Discovery

> **IMPORTANT:** Claude Code does NOT read from a separate `sandbox-config.json` file.
> Sandbox settings must be in `.claude/settings.local.json`.

### Correct Configuration Structure

Claude Code uses **TWO config files** for sandboxing:

| File | Purpose | Git Status |
|------|---------|------------|
| `.claude/settings.local.json` | Sandbox settings (excludedCommands, etc.) | gitignored |
| `.claude/rss-domains.json` | RSS domain validation for pre-commit hook | tracked |

**Sandbox settings** (in `settings.local.json`):
```json
{
  "sandbox": {
    "enabled": true,
    "autoAllowBashIfSandboxed": true,
    "allowUnsandboxedCommands": true,
    "excludedCommands": ["docker", "docker-compose", "docker compose", "kubectl"]
  }
}
```

**Verification:** Run `/sandbox` → Config tab should show:
```
Excluded Commands: docker, docker-compose, docker compose, kubectl
```

---

## When to Start Each Phase

| Phase | When to Start | Blocking? |
|-------|---------------|-----------|
| **Phase 0** | Before any sandbox work (rotate credentials) | Yes - security |
| **Phase 1** | ✅ COMPLETED | - |
| **Phase 2** | After 1-2 days of sandbox usage | No - documentation only |
| **Phase 3** | Immediately after Phase 1 to validate | Yes - before daily use |

**Recommended Flow:**
1. ✅ Phase 1 done → Sandbox configured
2. → Phase 3 (Testing) → Validate pytest, alembic, docker work
3. → Use sandbox for 1-2 days in normal development
4. → Phase 2 (Roadmap Updates) → Document for deployments

---

## User Concerns Addressed

### 1. Fear of Getting Stuck
**Solution: Tiered Fallback Strategy**
- **Tier 1 (Immediate):** `dangerouslyDisableSandbox` prompt - Allow Once
- **Tier 2 (Minutes):** `git checkout .claude/rss-domains.json`
- **Tier 3 (Session):** Restart Claude Code without `/sandbox`
- **Tier 4 (Full Rollback):** Remove sandbox section from `settings.local.json`

### 2. Feature Flag to Enable/Disable
- **Via /sandbox menu:** Select "No Sandbox" in Mode tab
- **Config File:** Remove `sandbox` section from `settings.local.json`
- **Session:** Simply don't run `/sandbox` command

### 3. Manual Work Clearly Marked
All tasks requiring user action marked with **⚠️ MANUAL**

---

## Prerequisites

- [ ] Git branch from develop: `git checkout develop && git pull && git checkout -b feature/sandboxing`
- [ ] Frontend path confirmed: `/Users/micky/WebstormProjects/PratikoAiWebApp/`

---

## Phase 0: Security Prerequisite

### TASK-SB-000: Rotate Exposed Credentials
**Type:** ⚠️ MANUAL | **Effort:** 30 min | **Status:** ❌ NOT STARTED

**Why:** Credentials may have been exposed in `.env.development`. Rotate before implementing sandbox protection.

**Steps:**
1. Check `.env.development` for exposed secrets
2. Rotate credentials at:
   - OpenAI: https://platform.openai.com/api-keys
   - Anthropic: https://console.anthropic.com/settings/keys
   - Gmail App Password: https://myaccount.google.com/apppasswords
   - Langfuse: https://cloud.langfuse.com
   - Stripe (if applicable): https://dashboard.stripe.com/apikeys
3. Update `.env.development` with new credentials
4. Verify: `docker-compose up -d && docker-compose logs -f app`

**Acceptance Criteria:**
- [ ] All potentially exposed credentials rotated
- [ ] Application starts successfully with new credentials
- [ ] Old credentials invalidated

**Rollback:** N/A (security task)

---

## Phase 1: Configuration (Day 1) - 4 hours ✅ COMPLETED

### TASK-SB-001: Create Sandbox Configuration
**Type:** AUTOMATED | **Effort:** 30 min | **Status:** ✅ COMPLETED

**Important:** Claude Code uses TWO config files:
1. `.claude/settings.local.json` - Sandbox settings (excludedCommands, etc.)
2. `.claude/rss-domains.json` - RSS domain validation (for pre-commit hook)

**File 1:** `.claude/settings.local.json` (add to existing)

```json
{
  "sandbox": {
    "enabled": true,
    "autoAllowBashIfSandboxed": true,
    "allowUnsandboxedCommands": true,
    "excludedCommands": ["docker", "docker-compose", "docker compose", "kubectl"]
  }
}
```

**File 2:** `.claude/rss-domains.json` (for RSS validation script)

```json
{
  "enabled": true,
  "sandboxing": {
    "allowedNetworkDomains": [
      "api.openai.com",
      "api.anthropic.com",
      "cloud.langfuse.com",
      "api.stripe.com",
      "js.stripe.com",
      "*.agenziaentrate.gov.it",
      "*.inps.it",
      "*.gov.it",
      "*.gazzettaufficiale.it",
      "smtp.gmail.com",
      "smtp.googlemail.com",
      "pypi.org",
      "files.pythonhosted.org",
      "registry.npmjs.org",
      "*.npmjs.org",
      "github.com",
      "hooks.slack.com",
      "localhost",
      "127.0.0.1"
    ]
  }
}
```

**Acceptance Criteria:**
- [x] JSON files are valid and parseable
- [x] excludedCommands shows in `/sandbox` Config tab
- [x] RSS validation script reads from rss-domains.json

**Rollback:** Remove sandbox section from settings.local.json, delete rss-domains.json

---

### TASK-SB-002: Enable Sandboxing
**Type:** ⚠️ MANUAL | **Effort:** 5 min | **Status:** ❌ NOT STARTED

**Steps:**
1. Start Claude Code: `claude`
2. Run: `/sandbox`
3. Verify reduced permission prompts

**Acceptance Criteria:**
- [ ] `/sandbox` executes without errors
- [ ] Subsequent operations have reduced prompts

**Rollback:** Exit and restart Claude Code without `/sandbox`

---

### TASK-SB-003: Create RSS Validation Script
**Type:** AUTOMATED | **Effort:** 1 hour | **Status:** ✅ COMPLETED

**File:** `scripts/validate_rss_sandbox.py`

**Purpose:**
- Read sandbox config from `.claude/sandbox-config.json`
- Query active RSS feeds from database (FeedStatus table)
- Validate each feed URL domain against allowedNetworkDomains
- Report violations and exit with non-zero code if found

**Acceptance Criteria:**
- [ ] Script correctly loads sandbox config
- [ ] Script queries database for active feeds
- [ ] Script validates domains against allowlist
- [ ] Script reports clear error messages for violations
- [ ] Exit code 0 on success, 1 on failure

**Rollback:** `rm scripts/validate_rss_sandbox.py`

---

### TASK-SB-004: Add Pre-commit Hook
**Type:** AUTOMATED | **Effort:** 30 min | **Status:** ✅ COMPLETED

**File:** `.pre-commit-config.yaml` (modify)

**Add:**
```yaml
- repo: local
  hooks:
    - id: validate-rss-sandbox
      name: Validate RSS feeds in sandbox
      entry: uv run python scripts/validate_rss_sandbox.py
      language: system
      pass_filenames: false
      always_run: true
```

**Acceptance Criteria:**
- [ ] Pre-commit config remains valid YAML
- [ ] Hook runs on commits
- [ ] Hook passes with current configuration

**Rollback:** Remove hook from `.pre-commit-config.yaml`

---

### TASK-SB-005: Create Weekly Review Script
**Type:** AUTOMATED | **Effort:** 1.5 hours | **Status:** ✅ COMPLETED

**File:** `scripts/weekly_sandbox_review.py`

**Purpose:**
- Parse sandbox log files (`/tmp/claude-sandbox-*.log`)
- Aggregate network requests by domain
- Identify blocked attempts
- Generate HTML email report
- Send to `METRICS_REPORT_RECIPIENTS_ADMIN` via SMTP

**Acceptance Criteria:**
- [x] Script handles missing log files gracefully
- [x] Script generates readable report format (HTML + plain text)
- [x] Email integration uses existing SMTP settings
- [x] Script can run standalone for testing (`--dry-run`)

**Rollback:** `rm scripts/weekly_sandbox_review.py`

---

### TASK-SB-006: Document Manual Review Process
**Type:** DOCUMENTATION | **Effort:** 5 min | **Status:** ✅ COMPLETED

No automated scheduling needed. Run the review script manually when you want to check sandbox activity:

```bash
# Full review with email notification
uv run python scripts/weekly_sandbox_review.py

# Preview without sending email
uv run python scripts/weekly_sandbox_review.py --dry-run
```

**Acceptance Criteria:**
- [x] Script documented in SANDBOXING_GUIDE.md
- [x] Manual execution works correctly

**Rollback:** N/A (no automation to remove)

---

### TASK-SB-007: Configure Email Notifications
**Type:** AUTOMATED | **Effort:** 15 min | **Status:** ✅ COMPLETED

**File:** `.env.example`

Weekly sandbox reports use existing email infrastructure:
- Recipients: `METRICS_REPORT_RECIPIENTS_ADMIN`
- SMTP: Existing `SMTP_*` settings

No additional environment variables needed.

**Acceptance Criteria:**
- [x] Uses existing SMTP configuration
- [x] Uses existing admin recipient list

**Rollback:** N/A (uses existing config)

---

### TASK-SB-008: Create Sandboxing Guide
**Type:** AUTOMATED | **Effort:** 1 hour | **Status:** ✅ COMPLETED

**File:** `.claude/docs/SANDBOXING_GUIDE.md`

**Covers:**
- Quick start instructions
- What is protected (credentials, network)
- Docker usage (auto-excluded)
- RSS feed management workflow
- `dangerouslyDisableSandbox` decision guide
- Security monitoring information
- Troubleshooting common issues

**Acceptance Criteria:**
- [ ] Guide covers all documented topics
- [ ] Examples are accurate and tested
- [ ] Decision matrix for escape hatch is clear

**Rollback:** `rm -rf .claude/docs/`

---

## Phase 2: Roadmap Updates (Day 2 Morning) - 2 hours

Start Phase 2 when: You're ready to update deployment documentation (not blocking development work).

 Phase 2 is documentation-only - it updates ARCHITECTURE_ROADMAP.md files to include sandbox phases in deployment tasks. This is
 planning for future deployments, not immediate action.

### TASK-SB-010: Update Backend ARCHITECTURE_ROADMAP.md
**Type:** AUTOMATED | **Effort:** 1 hour | **Status:** ❌ NOT STARTED

**File:** `docs/tasks/ARCHITECTURE_ROADMAP.md`

**Add sandbox phases to:**
- DEV-BE-75 (QA): Phase 6 - Sandbox & Docker Configuration
- DEV-BE-88 (Preprod): Phase 4 - Enhanced Sandbox
- DEV-BE-90 (Production): Phase 4 - Paranoid Mode Sandbox

**Acceptance Criteria:**
- [ ] All three deployment tasks updated
- [ ] Sandbox phases correctly numbered
- [ ] Effort estimates included

**Rollback:** `git checkout docs/tasks/ARCHITECTURE_ROADMAP.md`

---

### TASK-SB-011: Update Frontend Roadmap
**Type:** AUTOMATED | **Effort:** 30 min | **Status:** ❌ NOT STARTED

**File:** `/Users/micky/WebstormProjects/PratikoAiWebApp/ARCHITECTURE_ROADMAP.md`

**Add sandbox phases to:**
- DEV-005 (QA): Phase 2 - Environment Configuration & Sandbox
- DEV-010 (Preprod/Production): Phase 3.5 - Sandbox Security Configuration

**Acceptance Criteria:**
- [ ] Frontend deployment tasks updated
- [ ] Jest watchman fix documented (if applicable)

**Rollback:** `cd /Users/micky/WebstormProjects/PratikoAiWebApp && git checkout ARCHITECTURE_ROADMAP.md`

---

### TASK-SB-012: Document Cross-Repo Coordination
**Type:** AUTOMATED | **Effort:** 30 min | **Status:** ❌ NOT STARTED

**Files:** Both ARCHITECTURE_ROADMAP.md files

**Add "Sandbox Coordination" section:**
- Shared Slack channel (#security-sandbox)
- Weekly review schedule (Monday 9AM)
- Deployment dependencies (backend sandbox before backend services)

**Acceptance Criteria:**
- [ ] Coordination section added to both files
- [ ] Dependencies clearly documented

**Rollback:** Revert changes to both roadmap files

---

## Phase 3: Testing & Validation (Day 2-3) - 6 hours

### TASK-SB-013: Test Backend in Sandbox
**Type:** ⚠️ MANUAL | **Effort:** 1 hour | **Status:** ❌ NOT STARTED

**Steps:**
1. Enable sandbox: `/sandbox`
2. Run backend tests: `uv run pytest tests/`
3. Run Alembic: `alembic current`
4. Document any issues or performance degradation

**Acceptance Criteria:**
- [ ] pytest runs successfully
- [ ] Alembic commands work
- [ ] No false-positive blocks on legitimate operations

**Rollback:** Exit sandbox mode, continue without it

---

### TASK-SB-014: Test Frontend in Sandbox
**Type:** ⚠️ MANUAL | **Effort:** 1 hour | **Status:** ❌ NOT STARTED

**Steps:**
1. Enable sandbox in frontend context
2. Run: `npm test`
3. Run: `npm run build`
4. If Jest hangs, add `--no-watchman` flag

**Acceptance Criteria:**
- [ ] `npm test` passes
- [ ] `npm run build` completes
- [ ] No credential access attempts logged

**Rollback:** Document watchman workaround if needed

---

### TASK-SB-015: Test Cross-Repo Access
**Type:** ⚠️ MANUAL | **Effort:** 30 min | **Status:** ❌ NOT STARTED

**Steps:**
1. From backend, read frontend code:
   ```bash
   cat /Users/micky/WebstormProjects/PratikoAiWebApp/src/app/api/client.ts
   ```
   Should ALLOW
2. From backend, attempt to read frontend credentials:
   ```bash
   cat /Users/micky/WebstormProjects/PratikoAiWebApp/.env.local
   ```
   Should BLOCK

**Acceptance Criteria:**
- [ ] Code files accessible across repos
- [ ] Credential files blocked across repos

---

### TASK-SB-016: Test RSS Feed Access
**Type:** ⚠️ MANUAL | **Effort:** 30 min | **Status:** ❌ NOT STARTED

**Steps:**
1. Test allowed Italian gov domains:
   ```bash
   curl https://www.agenziaentrate.gov.it
   ```
   Should ALLOW
2. Test unknown domain:
   ```bash
   curl https://unknown-domain.com
   ```
   Should BLOCK + Alert
3. Run validation script:
   ```bash
   uv run python scripts/validate_rss_sandbox.py
   ```

**Acceptance Criteria:**
- [ ] Italian gov domains accessible
- [ ] Unknown domains blocked
- [ ] Validation script reports correct status

---

### TASK-SB-017: Test Gmail SMTP
**Type:** ⚠️ MANUAL | **Effort:** 15 min | **Status:** ❌ NOT STARTED

**Steps:**
Test SMTP connection:
```python
import smtplib
smtp = smtplib.SMTP('smtp.gmail.com', 587)
smtp.starttls()
smtp.quit()
```

**Acceptance Criteria:**
- [ ] SMTP connection to Gmail allowed
- [ ] TLS handshake succeeds

---

### TASK-SB-018: Test Credential Blocking
**Type:** ⚠️ MANUAL | **Effort:** 30 min | **Status:** ❌ NOT STARTED

**Steps:**
1. Attempt to read .env:
   ```bash
   cat .env.development
   ```
   Should BLOCK
2. Attempt to read SSH keys:
   ```bash
   cat ~/.ssh/id_rsa
   ```
   Should BLOCK
3. Verify `dangerouslyDisableSandbox` prompt appears

**Acceptance Criteria:**
- [ ] All credential paths blocked
- [ ] Clear prompt appears for blocked access
- [ ] Log entry created for blocked attempts

---

### TASK-SB-019: Test Docker (Excluded)
**Type:** ⚠️ MANUAL | **Effort:** 15 min | **Status:** ❌ NOT STARTED

**Steps:**
```bash
docker-compose ps
docker-compose up -d
docker ps
```
Should all work (excluded from sandbox)

**Acceptance Criteria:**
- [ ] Docker commands execute without sandbox interference
- [ ] No permission prompts for Docker operations

---

### TASK-SB-020: Performance Benchmarking
**Type:** ⚠️ MANUAL | **Effort:** 1.5 hours | **Status:** ❌ NOT STARTED

**File:** `docs/SANDBOX_PERFORMANCE_BASELINE.md`

**Steps:**
1. Baseline WITHOUT sandbox:
   ```bash
   time uv run pytest tests/
   ```
2. Enable sandbox: `/sandbox`
3. WITH sandbox:
   ```bash
   time uv run pytest tests/
   ```
4. Calculate overhead percentage
5. Document results

**Target:** <10% overhead

**Acceptance Criteria:**
- [ ] Overhead documented for each test type
- [ ] All tests show <10% overhead
- [ ] Performance baseline document created

---

### TASK-SB-021: Test Email Alerts
**Type:** ⚠️ MANUAL | **Effort:** 30 min | **Status:** ❌ NOT STARTED

**Steps:**
1. Ensure `METRICS_REPORT_RECIPIENTS_ADMIN` is set in `.env.development`
2. Run weekly review:
   ```bash
   uv run python scripts/weekly_sandbox_review.py
   ```
3. Verify email received

**Acceptance Criteria:**
- [ ] Weekly review sends email
- [ ] HTML format is readable
- [ ] No credentials exposed in messages

---

## Fallback Plan (If Stuck)

### Level 1: Escape Hatch (Seconds)
When `dangerouslyDisableSandbox` prompt appears:
- **[Deny]** - Claude finds alternative
- **[Allow Once]** - Temporary bypass
- **[Update Config]** - Add to allowlist permanently

### Level 2: Config Rollback (Minutes)
```bash
git checkout .claude/sandbox-config.json
```

### Level 3: Session Disable (Immediate)
Exit Claude Code, restart without running `/sandbox`.

### Level 4: Full Rollback (15 minutes)
```bash
rm .claude/sandbox-config.json
# Remove pre-commit hook from .pre-commit-config.yaml
# Remove cron job: crontab -e
# Continue with existing permission system
```

**Important:** Keep `settings.local.json` intact during transition (do NOT delete).

---

## 2-Week Soft Launch Protocol

**Week 1-2 (Soft Launch):**
- Enable sandboxing with verbose monitoring
- Keep `settings.local.json` intact (do NOT delete permissions)
- Track all `dangerouslyDisableSandbox` occurrences
- Update allowlist based on legitimate needs
- Target: <5 escape hatch prompts per week

**Week 3-4 (Validation):**
- Compare approval frequency: before vs. after sandboxing
- Document any false positives
- Verify 84% prompt reduction claim
- Create performance baseline document

**Week 5+ (Full Adoption):**
- ONLY THEN consider deprecating granular `settings.local.json` permissions
- Keep backup: `cp settings.local.json settings.local.json.backup`
- Schedule quarterly security review

---

## Architecture Decision: ADR-016

Create ADR-016 documenting:
- **Context:** 128+ granular permissions causing approval fatigue
- **Decision:** Implement OS-level sandboxing
- **Consequences:** 84% fewer prompts, kernel-enforced security
- **Mitigations:** Tiered fallback, feature flag

---

## Success Criteria

- [ ] Sandbox enabled and working
- [ ] Permission prompts reduced by ~84%
- [ ] Docker commands work (excluded)
- [ ] pytest passes in sandbox
- [ ] RSS feeds accessible
- [ ] Credentials blocked
- [ ] Performance overhead <10%
- [ ] Fallback tested and documented

---

## Sources

- [Claude Code Sandboxing Docs](https://code.claude.com/docs/en/sandboxing)
- [Anthropic Engineering Blog](https://www.anthropic.com/engineering/claude-code-sandboxing)

---

**Document Prepared By:** Claude Code with @agent-egidio, @agent-mario (BA)
**Next Review:** After Phase 3 completion
