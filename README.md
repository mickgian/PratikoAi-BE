 # FastAPI LangGraph Backend Guidelines

  ## Architecture

  • Framework: FastAPI with Python 3.13+
  • AI/LLM: LangGraph with OpenAI GPT models
  • Database: PostgreSQL with SQLAlchemy ORM
  • Authentication: JWT tokens with bcrypt password hashing
  • Observability: Langfuse for LLM tracing
  • Rate Limiting: slowapi (Flask-Limiter for FastAPI)
  • Monitoring: Prometheus metrics + Grafana dashboards
  • Package Management: UV for fast dependency management

  ## Prerequisites

  • Python 3.13+
  • UV package manager for dependency management
  • PostgreSQL database
  • Docker & Docker Compose (optional)

  ## Current Implementation Status

  • Authentication: ✅ JWT-based auth with registration/login
  • Password Validation: ✅ 8+ chars, upper/lower, number, special char
  • Error Handling: ✅ Structured validation errors (422) and business logic errors (400)
  • User Management: ✅ User registration, login, profile management
  • Session Management: ✅ Session creation and management
  • Rate Limiting: ✅ Configurable per-endpoint limits
  • Current Feature: Chat implementation with LangGraph integration

  ## Tech Stack

  • Web Framework: FastAPI
  • ORM: SQLAlchemy with async support
  • Database: PostgreSQL
  • LLM Framework: LangGraph
  • Authentication: JWT with python-jose
  • Password Hashing: bcrypt
  • Validation: Pydantic models
  • Testing: pytest with async support
  • Rate Limiting: slowapi
  • Observability: Langfuse
  • Metrics: Prometheus
  • Monitoring: Grafana
  • Package Manager: UV

  ## Development Setup

  • Install dependencies: `uv sync`
  • Copy environment: `cp .env.example .env.development`
  • Run development server: `make dev`
  • Run staging: `make staging`
  • Run production: `make production`
  • Swagger docs: http://localhost:8000/docs

  ### Docker Development
  • Build Docker: `make docker-build-env ENV=development`
  • Run Docker: `make docker-run-env ENV=development`

  ## Key Commands

  • Start server: `make dev` (or `uvicorn app.main:app --reload --port 8000`)
  • Run tests: `pytest`
  • Run tests with coverage: `pytest --cov=app`
  • Database migrations: `alembic upgrade head`
  • Create migration: `alembic revision --autogenerate -m "description"`
  • Install dependencies: `uv sync`

  ## Development Notes

  • JWT tokens: 30 days access + 365 days refresh (development) - TODO: reduce for production
  • Server runs on: http://localhost:8000
  • API docs: http://localhost:8000/docs
  • Current branch: main (or specify current feature branch)

  ## API Architecture

  • Base URL: `/api/v1`
  • Authentication endpoints: `/api/v1/auth/`
  • Chat endpoints: `/api/v1/chat/`
  • User endpoints: `/api/v1/users/`
  • Health check: `/health`

  ## Error Response Format

  • **422 Validation Errors**:
  ```json
  {
    "detail": "Validation error",
    "errors": [
      {"field": "password", "message": "Password must contain at least one number"}
    ]
  }

  • 400 Business Logic Errors:
  {
    "detail": "Email already registered"
  }

  • 401 Authentication Errors:
  {
    "detail": "Invalid credentials"
  }
````
  ## Database Management

  • ORM handles table creation automatically
  • Manual schema: Run schemas.sql if needed
  • Connection format: postgresql://user:pass@host:port/dbname
  • Tables: Users, Sessions, Messages, checkpoint tables for LangGraph
  • Use Alembic for migrations
  • Follow SQLAlchemy async patterns

  ## Database Schema

  • Users table: id, email, hashed_password, created_at, updated_at
  • Sessions table: session_id, user_id, name, created_at
  • Messages table: id, session_id, content, role, timestamp
  • Checkpoint tables: checkpoint_blobs, checkpoint_writes, checkpoints (for LangGraph)

  ## LangGraph Configuration

  • Default model: gpt-4o-mini
  • Temperature: 0.2
  • Max tokens: 2000
  • Retry attempts: 3
  • Langfuse integration for tracing
  • Graph state management for conversation flow
  • Checkpoint persistence in PostgreSQL

  ## Monitoring Stack

  ### 📊 **Quick Access URLs**
  • **Grafana Dashboards**: http://localhost:3000 (admin/admin)
  • **Prometheus Metrics**: http://localhost:9090
  • **Langfuse LLM Tracing**: http://localhost:3000 (if configured)
  • **AlertManager**: http://localhost:9093

  ### 🎛️ **Available Dashboards**
  • **System Overview**: Executive summary of all key metrics
  • **Cost Analysis**: User cost tracking (€2.00/month target)
  • **Business Metrics**: Revenue tracking (€25k ARR target)
  • **Performance**: API response times and system health
  • **Alert Management**: Active alerts and incident tracking

  ### 🚨 **Alert System**
  • **14 Critical Alerts** across cost, business, performance, security
  • **4 Notification Channels**: Email, Slack, Webhook, PagerDuty
  • **Business-Aligned Thresholds**: €2.50/user cost, 5s API response, 95% payment success

  ### 🤖 **Automation Scripts**
  • **Daily Reports**: `make monitoring-daily` - Email business summaries
  • **Cost Optimization**: `make monitoring-costs` - Identify savings opportunities  
  • **Health Checks**: `make monitoring-health` - System validation
  • **Dashboard Backups**: `make monitoring-backup` - Configuration protection

  ### 🚀 **Getting Started**
  ```bash
  # Start monitoring stack
  make monitoring-start
  
  # Run health check
  make monitoring-health
  
  # Generate daily report
  make monitoring-daily
  
  # Full monitoring suite
  make monitoring-suite
  ```

  ### 📚 **Documentation**
  • **Complete Guide**: [MONITORING.md](MONITORING.md) - Full system documentation
  • **Quick Start**: [monitoring/QUICK_START.md](monitoring/QUICK_START.md) - 15-minute setup
  • **Alert Runbooks**: [monitoring/RUNBOOKS.md](monitoring/RUNBOOKS.md) - Response procedures
  • **Automation Guide**: [monitoring/AUTOMATION_GUIDE.md](monitoring/AUTOMATION_GUIDE.md) - Scripts usage

  ## Model Evaluation

  • Interactive evaluation: make eval
  • Quick evaluation: make eval-quick
  • No-report evaluation: make eval-no-report
  • Custom metrics: Add markdown files to evals/metrics/prompts/
  • Reports generated in: evals/reports/evaluation_report_YYYYMMDD_HHMMSS.json
  • Metrics include: success rate, timing, trace-level details

  ## Evaluation Features

  • Interactive CLI with colored output and progress bars
  • Flexible configuration with runtime customization
  • Detailed JSON reports with comprehensive metrics
  • Automatic Langfuse trace fetching and analysis

  ## Security Guidelines

  • Password requirements: 8+ chars, uppercase, lowercase, number, special char
  • JWT secret key must be set in environment variables
  • Rate limiting applied to all endpoints
  • Input validation using Pydantic models
  • SQL injection protection via SQLAlchemy ORM
  • CORS configured for frontend origins
  • Input sanitization for all user inputs

  ## Environment Variables

  # Required
  JWT_SECRET_KEY=your-secret-key
  POSTGRES_URL=postgresql://user:pass@localhost/dbname
  LLM_API_KEY=your-openai-api-key

  # Optional with defaults
  JWT_ACCESS_TOKEN_EXPIRE_HOURS=720  # 30 days for dev
  JWT_REFRESH_TOKEN_EXPIRE_DAYS=365
  LLM_MODEL=gpt-4o-mini
  LANGFUSE_PUBLIC_KEY=your-key
  LANGFUSE_SECRET_KEY=your-secret
  EVALUATION_LLM=gpt-4o-mini
  EVALUATION_API_KEY=your-openai-key

  ## Environment-Specific Configuration

  • .env.development - Local development settings
  • .env.staging - Staging environment
  • .env.production - Production environment
  • .env.example - Template with all available options

  ## Coding Standards

  • Use async/await for all database operations
  • Follow PEP 8 style guidelines
  • Use type hints throughout the codebase
  • Keep functions focused on single responsibility
  • Use dependency injection for database sessions
  • Handle exceptions with appropriate HTTP status codes
  • Log all authentication attempts and errors
  • Structured logging with environment-specific formatting

  ## Testing Requirements

  • Unit tests for all business logic
  • Integration tests for API endpoints
  • Test database fixtures for clean test data
  • Mock external API calls (OpenAI, Langfuse)
  • Test authentication flows thoroughly
  • Aim for 80%+ code coverage
  • Use pytest with async support

  ## Directory Structure
```
  app/
  ├── api/v1/          # API route handlers
  ├── core/            # Core utilities, config, security
  ├── models/          # SQLAlchemy models
  ├── schemas/         # Pydantic models
  ├── services/        # Business logic layer
  ├── utils/           # Helper utilities
  ├── main.py          # FastAPI application entry point
  evals/
  ├── metrics/prompts/ # Evaluation metric definitions
  ├── reports/         # Generated evaluation reports
  └── evaluator.py     # Evaluation framework
  docker/              # Docker configuration files
  monitoring/          # Prometheus & Grafana configs
```

  ## Rate Limiting Configuration

  • Default limits: 200 per day, 50 per hour
  • Endpoint-specific limits:
  - Chat: 30 per minute
  - Chat stream: 20 per minute
  - Register: 10 per hour
  - Login: 20 per minute
  • Configurable via environment variables

  ## Common Tasks

  • Add new endpoint: Create route in api/v1/, add schema, implement service
  • Database changes: Create Alembic migration, update models
  • Add authentication: Use get_current_user dependency
  • Rate limiting: Apply @limiter.limit() decorator
  • LLM integration: Use LangGraph state management patterns
  • Add evaluation metric: Create markdown file in evals/metrics/prompts/

  ## Troubleshooting

  • Database connection issues: Check POSTGRES_URL and ensure PostgreSQL is running
  • JWT token errors: Verify JWT_SECRET_KEY is set and consistent
  • Rate limiting issues: Check slowapi configuration and Redis connection
  • LLM API errors: Verify LLM_API_KEY and check OpenAI quota
  • Langfuse connection: Check LANGFUSE_* environment variables
  • Docker issues: Ensure Docker daemon is running and ports are available
  • Evaluation failures: Check evaluation model API key and Langfuse configuration

  ## Performance Considerations

  • Use async database operations throughout
  • Implement connection pooling for PostgreSQL
  • Cache frequently accessed data where appropriate
  • Monitor LLM API usage and costs via Langfuse
  • Use pagination for large data sets
  • Optimize database queries with proper indexing
  • Monitor system metrics via Prometheus/Grafana

  ## Production Deployment

  • Set secure JWT_SECRET_KEY in production
  • Use environment-specific configuration files
  • Set up proper logging and monitoring
  • Configure rate limiting based on expected traffic
  • Secure database with proper credentials
  • Set up SSL/TLS for production
  • Monitor via Grafana dashboards
  • Set up automated backups for PostgreSQL
  • Configure appropriate resource limits

  ## Monitoring & Debugging

  • Use Langfuse for LLM call tracing and debugging
  • Monitor API performance via Prometheus metrics
  • View system health via Grafana dashboards
  • Check application logs for detailed error information
  • Use evaluation reports to track model performance over time
