# ADR-028: Deployment Pipeline Architecture

## Status
Accepted

## Date
2026-02-17

## Context

PratikoAI has operated exclusively in local development since project inception. The application is now feature-complete enough for its first alpha QA deployment. We need a deployment pipeline that:

- Supports GitFlow branching (`feature -> develop -> release -> master`)
- Deploys to Hetzner Cloud servers (per ADR-006)
- Uses Docker Compose (NOT Kubernetes) for orchestration
- Automates image builds, deployments, and smoke tests
- Coordinates backend and frontend releases safely

Previous deployment infrastructure (AWS ECS via boto3, Docker Hub push, orchestrated deployments) was speculative and never used. This ADR supersedes those implementations.

## Decision

### Pipeline Architecture

```
Conventional Commits -> GitHub Actions CI/CD -> GHCR -> Hetzner Docker Compose
```

**Components:**

1. **Container Registry:** GitHub Container Registry (GHCR) replaces Docker Hub
   - Free for public repos, included with GitHub Teams
   - Native `GITHUB_TOKEN` authentication (no separate secrets)

2. **CI/CD:** GitHub Actions with three core workflows:
   - `build-images.yml`: Multi-stage Docker builds with Buildx layer caching
   - `deploy-qa.yml`: Auto-deploys on push to `develop`
   - `deploy-production.yml`: Auto-deploys on push to `master` with manual approval gate

3. **Reverse Proxy:** Caddy with automatic Let's Encrypt HTTPS
   - Required for `.app` TLD (HSTS preloaded)
   - Simpler than nginx (automatic cert management)

4. **Deployment Ordering:** Backend always deploys before frontend
   - Expand-Contract pattern for breaking API changes
   - Health check validation between backend and frontend deployment

5. **Monitoring:** Langfuse for LLM observability + Hetzner Dashboard for infra
   - No Prometheus/Grafana on QA (saves ~1.5GB RAM)
   - Prometheus/Grafana enabled on production only

### Archived Infrastructure

The following files are moved to `.github/workflows-archive/`:
- `deploy.yaml` (Docker Hub push)
- `orchestrated-deployment.yml` (AWS ECS)
- `coordination-system.yml` (AWS-specific)
- `version-management.yml` (replaced by python-semantic-release)

## Consequences

### Positive
- First real deployment pipeline (previously development-only)
- Simple Docker Compose approach matches team size (1-2 developers)
- Automated deployments reduce manual error
- GHCR is free and tightly integrated with GitHub Actions
- Caddy eliminates certificate management complexity

### Negative
- Docker Compose limits horizontal scaling (acceptable for current user base)
- GHCR requires GitHub Actions (no local push without extra setup)
- Single-server architecture has no failover (acceptable for QA/alpha)

## Related
- **ADR-006:** Hetzner over AWS
- **ADR-029:** Frontend Dockerization
- **ADR-030:** ML Model Versioning
