# ADR-033: Redis Security Hardening (Incident Response)

## Status
Accepted

## Date
2026-02-25

## Context

On 2026-02-25, we received a notification from the German Federal Office for Information Security (BSI/CERT-Bund), forwarded by Hetzner's abuse team, reporting that our Redis 7.4.7 instance on `167.235.17.13:6379` was openly accessible from the internet without authentication.

### Root Causes

**1. Docker bypasses UFW firewall.**
Our `docker-compose.yml` exposed Redis with `ports: "6379:6379"`, which binds to `0.0.0.0` (all network interfaces). Docker achieves port publishing by inserting iptables rules in the `nat/PREROUTING` chain, which is evaluated *before* UFW's `INPUT` chain filter rules. This means UFW's `deny incoming` policy has zero effect on Docker-published ports — a well-known but frequently overlooked Docker behavior.

**2. No Redis authentication configured.**
The `redis-server` command had no `--requirepass` flag. While `app/core/config.py` already supported `REDIS_PASSWORD` via environment variable, it defaulted to an empty string and was never set in any environment.

**3. No network segmentation.**
Redis was published on the host's external interface rather than restricted to the internal Docker bridge network. QA and production compose overrides inherited the base port mapping without removing it.

**4. Metrics endpoint also exposed.**
The `redis-exporter` service (port 9121) was exposed on all interfaces with an empty `REDIS_PASSWORD`, leaking cache key patterns (`llm_responses:*`, `conversations:*`, `embeddings:*`) and Redis internals to anyone on the internet.

### Impact Assessment

- **Data at risk:** LLM response cache, conversation history cache, HyDE document cache, MultiQuery cache
- **Attack surface:** Unauthenticated `FLUSHALL`, `CONFIG SET`, `KEYS *`, arbitrary data read/write
- **Duration of exposure:** Unknown (since initial deployment until 2026-02-24 04:37 UTC when BSI scanned)
- **Evidence of exploitation:** No evidence found, but cannot rule out read-only data exfiltration

## Decision

### Defense-in-depth: Three layers of protection

We adopt a defense-in-depth strategy for all internal services (Redis, PostgreSQL, monitoring exporters), ensuring that no single misconfiguration can expose them to the internet.

#### Layer 1: Network isolation (Docker compose)
- **Development:** Bind published ports to `127.0.0.1` only (`127.0.0.1:6379:6379`)
- **QA/Production:** Remove port mappings entirely (`ports: []`) — services communicate only via the internal Docker bridge network

#### Layer 2: Application authentication
- Redis requires password via `--requirepass ${REDIS_PASSWORD}`
- **Development:** Defaults to `devpass` for convenience
- **QA/Production:** Mandatory with `${REDIS_PASSWORD:?REDIS_PASSWORD required}` — Docker Compose refuses to start if the variable is unset
- Redis exporter receives the same password for metrics collection

#### Layer 3: Host firewall (iptables-persistent)
- Replace UFW with `iptables-persistent` in the server setup script, since UFW cannot protect Docker-published ports
- Explicitly block internal service ports (6379, 9121, 5432/5433, 9090, 9187, 9100, 9093, 8081) from external access via `INPUT` and `FORWARD` chain rules
- Rules persisted across reboots via `netfilter-persistent save`

### Why not UFW?

UFW operates on the `INPUT` and `OUTPUT` chains of the `filter` table. Docker's port publishing uses `DNAT` rules in the `nat/PREROUTING` chain, which redirects incoming packets to container IPs *before* they reach the `INPUT` chain. The packets then traverse the `FORWARD` chain (also not managed by UFW). This is a fundamental architectural mismatch — UFW was designed for host services, not container networking.

## Consequences

### Positive
- Redis no longer accessible from the internet (verified immediately via iptables rules applied on the server)
- Authentication required even for internal connections — protects against lateral movement if another container is compromised
- Server setup script now correctly handles Docker's firewall bypass, preventing recurrence on new server provisioning
- Pattern established for all future internal services: never publish on `0.0.0.0`, always require auth

### Negative
- `iptables-persistent` replaced UFW, which removed the simpler `ufw status` interface (acceptable tradeoff for actual security)
- Developers must set `REDIS_PASSWORD` (or accept the `devpass` default in development)
- Existing QA deployment requires adding `REDIS_PASSWORD` to `.env.qa` and restarting Redis (one-time migration step)

### Deployment Steps (QA)
1. Generate password: `openssl rand -base64 32`
2. Add `REDIS_PASSWORD=<generated>` to `.env.qa` on the server
3. Redeploy with updated compose files: `docker compose -f docker-compose.yml -f docker-compose.qa.yml up -d`
4. Verify: `docker compose exec redis redis-cli -a $REDIS_PASSWORD ping` should return `PONG`

## Files Changed

| File | Change |
|------|--------|
| `docker-compose.yml` | Redis bound to `127.0.0.1`, `--requirepass` added, `REDIS_PASSWORD` passed to app, exporter secured |
| `docker-compose.qa.yml` | `ports: []`, mandatory `REDIS_PASSWORD` for redis and app |
| `docker-compose.production.yml` | Same as QA |
| `scripts/server-setup.sh` | Replaced UFW with iptables-persistent, added explicit port blocking |

## References

- BSI/CERT-Bund report: CB-Report (2026-02-24, Redis 7.4.7 on 167.235.17.13)
- [Docker and iptables documentation](https://docs.docker.com/engine/network/packet-filtering-firewalls/)
- [Redis security best practices](https://redis.io/docs/latest/operate/oss_and_stack/management/security/)
- ADR-006: Hetzner hosting decision
- ADR-003: pgvector / PostgreSQL infrastructure
