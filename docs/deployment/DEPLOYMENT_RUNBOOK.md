# PratikoAI Deployment Runbook

Step-by-step guide for deploying PratikoAI to QA and Production environments.

## Architecture Overview

```
                          GitHub Actions
                               |
                     +---------+---------+
                     |                   |
               build-images.yml    deploy-{env}.yml
                     |                   |
                     v                   v
                   GHCR            Hetzner Server
              (Docker images)           |
                                 Docker Compose
                                        |
                    +-------+-------+-------+-------+
                    |       |       |       |       |
                  Caddy    App   Frontend   DB    Redis
                 (HTTPS)  (BE)   (Next.js) (PG)
```

## Prerequisites

### GitHub Secrets Required

| Secret | Description |
|--------|-------------|
| `HETZNER_QA_HOST` | QA server IP address |
| `HETZNER_QA_SSH_KEY` | SSH private key for QA deploy user |
| `HETZNER_PROD_HOST` | Production server IP |
| `HETZNER_PROD_SSH_KEY` | SSH private key for prod deploy user |
| `OPENAI_API_KEY` | OpenAI API key (for CI tests) |

### GitHub Repository Variables

| Variable | Description |
|----------|-------------|
| `HF_INTENT_MODEL` | HuggingFace model ID (default: `mdeberta`) |
| `STAKEHOLDER_EMAIL` | Email for deployment notifications |

### GitHub Environments

1. **qa**: Auto-deploy on push to `develop`
2. **production**: Requires manual approval, auto-deploy on push to `master`

---

## First-Time QA Setup

### 1. Provision Server

```bash
# Run from local machine as root on fresh Hetzner CX33
ssh root@<QA_SERVER_IP> 'bash -s' < scripts/server-setup.sh
```

This installs Docker, creates deploy user, configures firewall, sets up backups.

### 2. Configure DNS (at Hostinger)

| Type | Name | Value |
|------|------|-------|
| A | `api-qa` | `<QA Server IP>` |
| A | `app-qa` | `<QA Server IP>` |
| A | `flags-qa` | `<QA Server IP>` |

### 3. Deploy Application Files

```bash
# SSH as deploy user
ssh deploy@<QA_SERVER_IP>

# Create directory structure
mkdir -p /opt/pratikoai/caddy /opt/pratikoai/backups

# Copy compose files (from local)
scp docker-compose.yml docker-compose.qa.yml deploy@<QA_SERVER_IP>:/opt/pratikoai/
scp caddy/Caddyfile deploy@<QA_SERVER_IP>:/opt/pratikoai/caddy/
```

### 4. Create Environment File

On the QA server, create `/opt/pratikoai/.env.qa` with real secrets:

```bash
# Required variables:
APP_ENV=qa
POSTGRES_USER=aifinance
POSTGRES_PASSWORD=<strong-random-password>
POSTGRES_DB=aifinance
REDIS_URL=redis://redis:6379/0
JWT_SECRET_KEY=<64-char-random-string>
LLM_API_KEY=<openai-api-key>
OPENAI_API_KEY=<openai-api-key>
MISTRAL_API_KEY=<mistral-api-key>
LANGFUSE_PUBLIC_KEY=<langfuse-public-key>
LANGFUSE_SECRET_KEY=<langfuse-secret-key>
LANGFUSE_HOST=https://cloud.langfuse.com
ALLOWED_ORIGINS=https://app-qa.pratiko.app
HF_TOKEN=<huggingface-token>
STRIPE_SECRET_KEY=<stripe-test-key>
STRIPE_WEBHOOK_SECRET=<stripe-webhook-secret>
```

### 5. Seed Database

```bash
# On the QA server
cd /opt/pratikoai

# Start only the database
docker compose -f docker-compose.yml -f docker-compose.qa.yml up -d db

# Restore from dev backup
scp local-backup.sql.gz deploy@<QA_SERVER_IP>:/opt/pratikoai/backups/
docker compose exec -T db gunzip -c /opt/pratikoai/backups/local-backup.sql.gz | \
    docker compose exec -T db psql -U aifinance aifinance

# Start everything
docker compose -f docker-compose.yml -f docker-compose.qa.yml up -d
```

### 6. Verify Deployment

```bash
./scripts/smoke_test.sh https://api-qa.pratiko.app https://app-qa.pratiko.app
```

---

## Routine Deployments

### Deploy to QA (Automatic)

1. Merge PR to `develop` branch
2. GitHub Actions automatically:
   - Builds backend + frontend Docker images
   - Pushes to GHCR
   - SSHs into QA server
   - Deploys backend first, waits for health check
   - Deploys frontend
   - Runs smoke tests
   - Sends email notification

### Deploy to Production (Manual Approval)

1. Merge PR from `develop` to `master`
2. GitHub Actions builds images
3. **Manual approval required** (GitHub Environment protection)
4. After approval: same deploy sequence as QA
5. Creates GitHub Release with auto-generated notes

---

## Rollback Procedures

### Quick Rollback (Previous Image)

```bash
# SSH into server
ssh deploy@<SERVER_IP>
cd /opt/pratikoai

# Find previous image tag
docker images ghcr.io/mickgian/pratikoai-backend --format "{{.Tag}}"

# Roll back to previous tag
export IMAGE_TAG=<previous-tag>
docker compose -f docker-compose.yml -f docker-compose.<env>.yml up -d app frontend
```

### Database Rollback

```bash
# On the server
cd /opt/pratikoai

# Stop app
docker compose stop app frontend

# Restore from backup
docker compose exec -T db psql -U aifinance -c "DROP DATABASE aifinance; CREATE DATABASE aifinance;"
gunzip -c backups/db-backup-YYYYMMDD.sql.gz | docker compose exec -T db psql -U aifinance aifinance

# Restart
docker compose up -d app frontend
```

### Alembic Migration Rollback

```bash
# SSH into server, exec into app container
docker compose exec app /app/.venv/bin/alembic downgrade -1
```

---

## Monitoring

### QA Environment
- **LLM observability**: Langfuse (cloud.langfuse.com)
- **Infrastructure**: Hetzner Dashboard
- **Logs**: `docker compose logs -f app` or `docker compose logs -f frontend`

### Production Environment
- All of the above, plus:
- **Prometheus**: `https://grafana.pratiko.app` (when enabled)
- **Grafana dashboards**: Application metrics, DB performance, Redis stats

---

## Troubleshooting

### Container won't start
```bash
docker compose logs app --tail=50
docker compose exec app /app/.venv/bin/alembic current  # Check migration state
```

### Database connection issues
```bash
docker compose exec db pg_isready -U aifinance
docker compose logs db --tail=20
```

### HTTPS certificate issues
```bash
docker compose logs caddy --tail=20
# Caddy auto-provisions certs; ensure DNS points to server IP
```

### Out of memory
```bash
docker stats  # Check container memory usage
free -h       # Check host memory
```
