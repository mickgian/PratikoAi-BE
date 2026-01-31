#!/bin/bash
# Session Start Hook - Injects project context at session start
# Runs on: startup, resume, compact

cat << 'EOF'
## PratikoAI Session Context

### Agent Workflow (CLAUDE.md)
- @mario -> requirements (3+ files, DB/API changes)
- @egidio -> architecture review (HAS VETO POWER)
- @primo -> database design (SQLModel only)
- @ezio -> backend implementation (TDD required)
- @clelia -> test validation (target: 69.5%)

### Critical Rules
1. TDD: Write tests FIRST (RED-GREEN-REFACTOR) - ADR-013
2. SQLModel ONLY, no SQLAlchemy Base - ADR-014
3. Test coverage target: 69.5%
4. Italian for user-facing text
5. Pre-commit hooks must pass (ruff, mypy, pytest)

### Quick Commands
- Tests: uv run pytest
- Format: ruff format . && ruff check --fix .
- Migration: alembic revision --autogenerate -m "description"
EOF

# Show recent commits for context
echo ""
echo "### Recent Commits"
git log --oneline -5 2>/dev/null || echo "(not a git repo)"

# Show current branch
echo ""
echo "### Current Branch"
git branch --show-current 2>/dev/null || echo "(not a git repo)"
