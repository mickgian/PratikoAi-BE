# 🔒 Installing Security Checks

## Quick Setup

```bash
# Install pre-commit
pip install pre-commit

# Install the hooks
pre-commit install

# Test the installation
pre-commit run --all-files
```

## Manual Check

You can manually check for sensitive data anytime:

```bash
python scripts/check_sensitive_data.py
```

## What Gets Checked

The security system automatically prevents commits containing:

- ✅ **Personal emails** (gmail, yahoo, hotmail, etc.)
- ✅ **API keys** (OpenAI, Stripe, AWS)
- ✅ **Passwords** and secrets
- ✅ **Private keys**
- ✅ **Database URLs with credentials**

## Safe Values

These patterns are considered safe and won't trigger alerts:

- `your-email@example.com`
- `test-password`
- `mock-api-key`
- `fake-secret`
- Values in test files with obvious test patterns

## If You Need to Bypass

**Only in exceptional cases:**

```bash
git commit --no-verify -m "Your message"
```

⚠️ **Warning**: Only bypass if you're absolutely certain no sensitive data is included.

## Setup Complete

Your repository is now protected against accidental sensitive data commits! 🛡️