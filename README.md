# PratikoAI Backend

FastAPI-based backend for PratikoAI - AI-powered assistant for Italian legal and tax information.

## Features

- **RAG (Retrieval-Augmented Generation):** 134-step LangGraph orchestration pipeline
- **Hybrid Search:** 50% FTS + 35% Vector + 15% Recency scoring
- **pgvector:** PostgreSQL-based vector search (1536d embeddings)
- **Semantic Caching:** Redis-based caching for cost optimization
- **GDPR Compliant:** Data export, deletion, and consent management
- **Multi-Agent System:** Architect, Scrum Master, and specialized subagents with @mention support

## Tech Stack

- **Python:** 3.13
- **Framework:** FastAPI (async)
- **Database:** PostgreSQL 15+ with pgvector
- **Cache:** Redis
- **LLM:** OpenAI (gpt-4-turbo, text-embedding-3-small)
- **Orchestration:** LangGraph
- **Validation:** Pydantic V2
- **Testing:** pytest (target: 69.5% coverage)

## Prerequisites

- Python 3.13+
- PostgreSQL 15+ with pgvector extension
- Redis
- Docker & Docker Compose (recommended)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/mickgian/PratikoAi-BE.git
cd PratikoAi-BE
```

### 2. Environment Setup

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and configure:
# - LLM_API_KEY (OpenAI API key)
# - POSTGRES_URL (PostgreSQL connection string)
# - REDIS_URL (Redis connection string)
# - SLACK_WEBHOOK_URL (for subagent notifications - see below)
nano .env
```

### 3. Install Dependencies

#### Using UV (Recommended)

```bash
# Install UV if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
```

#### Using pip

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .
```

### 4. Database Setup

```bash
# Using Docker Compose (recommended)
docker-compose up -d postgres redis

# Run migrations
alembic upgrade head
```

### 5. Run the Application

```bash
# Development server
uvicorn app.main:app --reload

# Or using Docker Compose
docker-compose up
```

The API will be available at http://localhost:8000

## Subagent System with @Mentions

The PratikoAI multi-agent system includes 9 AI subagents that you can interact with using @mentions:

### Management Subagents (Always Active)
- **@Egidio** (Architect) - Architecture decisions, tech stack, ADRs, veto power
- **@Ottavio** (Scrum Master) - Sprint planning, task coordination, progress tracking

### Specialized Subagents (Activated on Demand)
- **@Ezio** (Backend Expert) - Python, FastAPI, LangGraph, RAG implementation
- **@Livia** (Frontend Expert) - Next.js, React, UI/UX, Tailwind CSS
- **@Severino** (Security Audit) - GDPR compliance, security reviews, data protection
- **@Clelia** (Test Generation) - pytest, test coverage (target: 69.5%), TDD
- **@Primo** (Database Designer) - PostgreSQL, pgvector optimization, indexes
- **@Dario** (DevOps Engineer) - GitHub integration, CI/CD monitoring, PR creation, cost optimization
- **@Valerio** (Performance Optimizer) - Cache optimization, query performance (prepared, not active)

### Using @Mentions in Claude Code

When working with Claude Code, you can @mention subagents directly:

```
@Egidio remind me why we chose pgvector over Pinecone

@Ezio implement the FAQ migration to pgvector

@Clelia write tests for the new feedback endpoint

@Dario create a PR for the completed FAQ migration task
```

See `.claude/subagent-names.json` for the complete name mapping.

## Slack Integration (Subagent Notifications)

The PratikoAI multi-agent system uses Slack for real-time notifications from:
- **Architect subagent (@Egidio):** Veto alerts (critical decisions)
- **Scrum Master subagent (@Ottavio):** Progress updates every 2 hours
- Task completion, blockers, and sprint summaries

### Setup Slack Notifications

**IMPORTANT:** Slack channels do NOT auto-create. You must manually create them first.

**1. Create Slack workspace** (if you don't have one):
   - Go to https://slack.com/get-started

**2. Create Slack channels manually:**
   ```
   #architect-alerts  - Critical architecture veto notifications
   #scrum-updates     - 2-hour progress updates from Scrum Master
   ```
   - In Slack, click "+" next to Channels
   - Create both channels with exact names above (including the #)

**3. Create incoming webhook:**
   - Go to https://api.slack.com/apps
   - Create a new app: "PratikoAI Notifications"
   - Enable "Incoming Webhooks"
   - Add webhook to workspace
   - Copy webhook URL

**4. Configure .env:**
   ```bash
   # Slack Integration (for Subagent Notifications)
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
   SLACK_CHANNEL_ARCHITECT=#architect-alerts
   SLACK_CHANNEL_SCRUM=#scrum-updates
   SLACK_ENABLED=true
   ```

**5. Test the integration:**
   ```bash
   python scripts/test_slack_notifications.py
   ```

**For detailed setup instructions, see:** [docs/setup/SLACK_INTEGRATION.md](docs/setup/SLACK_INTEGRATION.md)

## Development

### Code Quality

The project uses automated code quality tools:

```bash
# Run all checks
./scripts/check_code.sh

# Auto-fix issues
./scripts/check_code.sh --fix

# Run specific tools
ruff check .           # Linting
ruff format .          # Formatting
mypy app/              # Type checking
pytest --cov=app       # Tests with coverage
```

### Pre-commit Hooks

Pre-commit hooks run automatically on every commit:
- Ruff (linting + formatting)
- MyPy (type checking)
- pytest (test coverage ≥69.5%)
- detect-secrets (prevent committing secrets)

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/api/test_chat.py

# View coverage report
open htmlcov/index.html
```

## Architecture

- **RAG Pipeline:** 134-step LangGraph orchestration
  - See: `app/orchestrators/golden.py`
- **Hybrid Search:** FTS + Vector + Recency
  - See: `app/retrieval/postgres_retriever.py`
- **Multi-Agent System:** Architect, Scrum Master, specialized subagents
  - See: `.claude/subagents/*.md`
- **Architectural Decisions:** Documented as ADRs
  - See: `docs/architecture/decisions.md`

## API Documentation

Once the server is running:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

## Environment Variables

Key environment variables (see `.env.example` for complete list):

| Variable | Description | Required |
|----------|-------------|----------|
| `LLM_API_KEY` | OpenAI API key | Yes |
| `POSTGRES_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `JWT_SECRET_KEY` | JWT token secret | Yes |
| `SLACK_WEBHOOK_URL` | Slack webhook for notifications | No* |
| `SLACK_ENABLED` | Enable Slack notifications | No* |

\* Required for subagent notifications

## Deployment

### Docker Compose (Production)

```bash
# Build and start all services
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f app

# Stop services
docker-compose -f docker-compose.prod.yml down
```

### Hetzner VPS (Current Setup)

The application is deployed on Hetzner VPS (Germany) for GDPR compliance.

Deployment configuration:
- PostgreSQL with pgvector
- Redis for caching
- Nginx reverse proxy
- SSL/TLS with Let's Encrypt
- fail2ban for security

## Roadmap

See [ARCHITECTURE_ROADMAP.md](ARCHITECTURE_ROADMAP.md) for the complete roadmap.

Current priorities:
- ✅ Sprint 0: Subagent system setup
- 🔄 Test coverage: 4% → 69.5%
- ⏳ DEV-BE-67: Migrate FAQ embeddings to pgvector
- ⏳ DEV-BE-76: Fix cache key + semantic layer
- ⏳ DEV-BE-75: Deploy QA environment

## Contributing

1. Create a feature branch from `master`
2. Make your changes
3. Ensure all tests pass and coverage ≥69.5%
4. Run `./scripts/check_code.sh` to verify code quality
5. Create a pull request

## License

[Add license information]

## Support

For issues or questions:
- GitHub Issues: https://github.com/mickgian/PratikoAi-BE/issues
- Email: STAKEHOLDER_EMAIL (via environment variable)

---

**Last Updated:** 2025-11-17
