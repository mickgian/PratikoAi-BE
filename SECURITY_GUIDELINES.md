# 🔒 Security Guidelines for PratikoAI Development

## Never Commit Sensitive Data

### ❌ What NOT to commit:
- Personal email addresses (e.g., john.smith@gmail.com)
- Real API keys (OpenAI, Stripe, etc.)
- Actual passwords or tokens
- Production database URLs with credentials
- Private SSH keys or certificates
- Any personally identifiable information (PII)

### ✅ What to commit instead:
- Example configurations with placeholders
- Documentation with generic examples
- Code that reads from environment variables
- `.example` files showing configuration structure

## Pre-commit Checks

We use automated checks to prevent accidental commits of sensitive data:

```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run checks manually
python scripts/check_sensitive_data.py
```

## Environment Files Best Practices

### 1. Use `.example` files for templates:
```bash
.env.example           # ✅ Commit this
.env.development       # ❌ Never commit
.env.staging          # ❌ Never commit  
.env.production       # ❌ Never commit
```

### 2. Use placeholders in examples:
```bash
# Good examples:
EMAIL=your-email@example.com
API_KEY=your-api-key-here
DATABASE_URL=postgresql://username:password@localhost:5432/dbname

# Bad examples (too specific):
EMAIL=john.smith@gmail.com
API_KEY=sk-proj-ABC123...
DATABASE_URL=postgresql://admin:secretpass@prod.db.com:5432/pratikoai
```

### 3. Document without exposing:
```markdown
# Good documentation:
"Configure your email in METRICS_REPORT_RECIPIENTS environment variable"

# Bad documentation:
"Send reports to john.smith@gmail.com"
```

## Git Configuration

### Ensure .gitignore includes:
```
# Environment files
.env
.env.*
!.env.example
!.env.*.example

# Secrets
*.key
*.pem
*.p12
secrets/
```

### Before Every Commit:
1. Review staged files: `git status`
2. Check for sensitive data: `git diff --cached`
3. Let pre-commit hooks run
4. Never use `--no-verify` unless absolutely necessary

## If You Accidentally Commit Sensitive Data

1. **Don't push!** If you haven't pushed yet:
   ```bash
   git reset HEAD~1
   ```

2. **If already pushed:**
   - Immediately rotate/change the exposed credentials
   - Use `git filter-branch` or BFG Repo-Cleaner to remove from history
   - Force push the cleaned history
   - Notify the team

## Environment Variable Management

### Development:
- Keep personal settings in `.env.development`
- Never share your personal `.env` files

### CI/CD:
- Use secret management services
- Never put secrets in GitHub Actions YAML files
- Use repository secrets for sensitive values

### Production:
- Use proper secret management (AWS Secrets Manager, etc.)
- Rotate credentials regularly
- Monitor for exposed credentials

## Questions or Concerns?

If you're unsure whether something is sensitive:
- Err on the side of caution
- Ask the team
- Use placeholders
- Check with `scripts/check_sensitive_data.py`

Remember: **Security is everyone's responsibility!**