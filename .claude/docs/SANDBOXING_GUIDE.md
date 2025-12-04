# Sandboxing Guide for PratikoAI

This guide explains how to use Claude Code sandboxing in the PratikoAI development environment.

---

## Quick Start

```bash
# Start Claude Code
claude

# Enable sandboxing (in Claude Code)
/sandbox
```

That's it! You now have OS-level security protecting your credentials.

---

## What's Protected

### Filesystem Protection

**Denied directories (BLOCKED):**
- All `.env*` files (credentials)
- `~/.ssh/` (SSH keys)
- `~/.aws/` (AWS credentials)
- `~/.docker/config.json` (Docker auth)
- `~/.gitconfig`, `~/.git-credentials`

**Allowed directories:**
- `/Users/micky/PycharmProjects/PratikoAi-BE/` (backend repo)
- `/Users/micky/WebstormProjects/PratikoAiWebApp/` (frontend repo)
- `/tmp/` (temporary files)
- `~/.cache/uv/`, `~/.cache/npm/` (package caches)
- `/usr/local/bin/`, `/opt/homebrew/bin/` (system binaries)

### Network Protection

**Allowed domains:**
- `api.openai.com`, `api.anthropic.com` (LLM APIs)
- `cloud.langfuse.com` (observability)
- `api.stripe.com`, `js.stripe.com` (payments)
- `*.agenziaentrate.gov.it`, `*.inps.it`, `*.gov.it` (Italian government)
- `smtp.gmail.com` (email)
- `pypi.org`, `registry.npmjs.org` (package registries)
- `github.com`, `hooks.slack.com`
- `localhost`, `127.0.0.1`

**Everything else is BLOCKED by default.**

---

## Docker Usage

Docker commands work normally because they're excluded from the sandbox:

```bash
docker-compose up -d      # Works
docker-compose logs       # Works
docker ps                 # Works
docker build             # Works
```

The sandbox excludes: `docker`, `docker-compose`, `docker compose`, `kubectl`

---

## RSS Feed Management

### Adding a New RSS Feed

1. Add feed to database as usual
2. Check if domain is in sandbox allowlist:
   ```bash
   uv run python scripts/validate_rss_sandbox.py
   ```
3. If domain is NOT allowed, add to `.claude/rss-domains.json`:
   ```json
   "allowedNetworkDomains": [
     "*.newdomain.gov.it",
     ... existing domains ...
   ]
   ```
4. Commit the updated config

### Pre-commit Validation

The `validate-rss-sandbox` pre-commit hook automatically checks that all enabled RSS feeds have their domains in the sandbox allowlist.

---

## The Escape Hatch: dangerouslyDisableSandbox

When Claude needs to access something blocked by the sandbox, you'll see:

```
dangerouslyDisableSandbox

Claude needs to access: <blocked-resource>
This is blocked by your sandbox configuration.

Options:
  [Deny] - Claude will find another way
  [Allow Once] - Temporarily disable sandbox for this operation
  [Update Config] - Add this path/domain to allowlist permanently
```

### Decision Guide

| Resource | Action | Reason |
|----------|--------|--------|
| `.env` files | **DENY** | Credentials must stay protected |
| `~/.ssh/`, `~/.aws/` | **DENY** | System credentials are off-limits |
| Pastebin, file sharing | **DENY** | Data exfiltration risk |
| New Italian gov domain | **Update Config** | Trusted government source |
| Unknown config file | **Allow Once** | Investigate, then decide |

**Default to DENY** and ask Claude to work within sandbox boundaries.

---

## Security Monitoring

### Sandbox Review (Manual)

Run the review script when you want to check sandbox activity:

```bash
# Full review with email notification
uv run python scripts/weekly_sandbox_review.py

# Preview without sending email
uv run python scripts/weekly_sandbox_review.py --dry-run

# Analyze specific time period
uv run python scripts/weekly_sandbox_review.py --days 30
```

If `METRICS_REPORT_RECIPIENTS_ADMIN` is configured, it sends an HTML email report to the admin recipients.

### Manual Log Inspection

```bash
# Watch network activity in real-time
tail -f /tmp/claude-sandbox-network.log

# Watch filesystem violations
tail -f /tmp/claude-sandbox-filesystem.log

# Parse with jq for better formatting
tail -f /tmp/claude-sandbox-network.log | jq .
```

---

## Troubleshooting

### "Read-only file system" Error

**Cause:** Trying to write outside allowed directories.

**Fix:** The sandbox only allows writes to the current working directory. Ensure you're in the project root.

### Jest Tests Hanging

**Cause:** Watchman incompatible with sandbox.

**Fix:** Add `--no-watchman` flag:
```json
{
  "scripts": {
    "test": "jest --no-watchman"
  }
}
```

### Network Request Blocked

**Cause:** Domain not in allowlist.

**Fix:**
1. Check if domain should be allowed
2. If yes, add to `.claude/rss-domains.json`:
   ```json
   "allowedNetworkDomains": [
     "new-domain.com",
     ...
   ]
   ```
3. Re-run `/sandbox`

### Pre-commit Hook Failing

**Cause:** RSS feed domain not in sandbox allowlist.

**Fix:**
1. Run: `uv run python scripts/validate_rss_sandbox.py`
2. Add missing domains to sandbox config
3. Commit both files together

---

## Fallback Plan (If Stuck)

### Level 1: Escape Hatch (Seconds)
Use `[Allow Once]` when dangerouslyDisableSandbox prompt appears.

### Level 2: Config Rollback (Minutes)
```bash
git checkout .claude/rss-domains.json
```

### Level 3: Session Disable (Immediate)
Exit Claude Code, restart WITHOUT running `/sandbox`.

### Level 4: Full Rollback (15 minutes)
```bash
rm .claude/rss-domains.json
# Edit .pre-commit-config.yaml to remove validate-rss-sandbox hook
```

---

## Configuration Reference

### Sandbox Config (settings.local.json)

Sandbox settings are in `.claude/settings.local.json`:

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

### RSS Domain Config (rss-domains.json)

RSS feed domain validation uses `.claude/rss-domains.json`:

```json
{
  "enabled": true,
  "sandboxing": {
    "allowedNetworkDomains": [
      "api.openai.com",
      "*.gov.it",
      ...
    ]
  }
}
```

### Feature Flag

Disable sandbox in `/sandbox` menu or remove `sandbox` section from `settings.local.json`.

---

## Further Reading

- [Claude Code Sandboxing Docs](https://code.claude.com/docs/en/sandboxing)
- [Anthropic Engineering Blog](https://www.anthropic.com/engineering/claude-code-sandboxing)
- [PratikoAI Sandboxing Roadmap](../../../docs/tasks/SANDBOXING_ROADMAP.md)

---

**Last Updated:** 2025-12-04
**Maintainer:** Backend Team
