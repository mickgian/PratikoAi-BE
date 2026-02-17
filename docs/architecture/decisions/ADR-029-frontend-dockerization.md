# ADR-029: Frontend Dockerization

## Status
Accepted

## Date
2026-02-17

## Context

The PratikoAI frontend (Next.js 15 + React 19) was previously configured for Vercel deployment:
- `vercel.json`, `.vercel/` directory, `deploy.sh` for Vercel CLI
- `package.json` scripts: `deploy:preview`, `deploy:prod` using `npx vercel`
- No `output: 'standalone'` in `next.config.ts`
- No Dockerfile or Docker-related configuration

Per ADR-006 (Hetzner over AWS) and the deployment plan, both backend and frontend must run on Hetzner infrastructure using Docker Compose.

## Decision

### Dockerize the Next.js frontend with standalone output mode

1. **Add `output: 'standalone'`** to `next.config.ts`
   - Produces a self-contained Node.js server (~25MB vs ~200MB full node_modules)
   - Enables Docker deployment without the full `node_modules` directory

2. **Multi-stage Dockerfile** (3 stages):
   - **deps**: `npm ci` in isolated layer (cached unless package-lock changes)
   - **builder**: `npm run build` with build-time environment variables
   - **runner**: Minimal `node:20-alpine` with standalone output + static assets

3. **Build-time API URL** via `NEXT_PUBLIC_API_URL` build arg
   - QA: `https://api-qa.pratiko.app`
   - Production: `https://api.pratiko.app`
   - Baked at build time (Next.js `NEXT_PUBLIC_*` convention)

4. **Frontend deploys alongside backend** in Docker Compose
   - No separate Vercel infrastructure
   - Caddy reverse proxy handles HTTPS and routing

### What Stays
- Vercel files (`.vercel/`, `vercel.json`) remain for potential future use
- `deploy.sh` and Vercel scripts remain but are not used in the pipeline
- All frontend tests and Playwright E2E setup unchanged

## Consequences

### Positive
- Single infrastructure (Hetzner) for entire stack
- Full control over frontend deployment and configuration
- No vendor lock-in to Vercel
- GDPR compliance (EU-hosted, per ADR-006)
- Cost savings (frontend hosting included in server cost)

### Negative
- No Vercel edge network (CDN/edge functions) - mitigated by Caddy compression
- Manual scaling (no Vercel auto-scaling) - acceptable for current user base
- Build-time `NEXT_PUBLIC_*` requires rebuild for API URL changes

## Related
- **ADR-006:** Hetzner over AWS
- **ADR-028:** Deployment Pipeline Architecture
