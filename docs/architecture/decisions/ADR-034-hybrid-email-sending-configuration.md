# ADR-034: Hybrid Email Sending Configuration

## Status
Accepted

## Date
2026-02-26

## Context

PratikoAI sends emails on behalf of studios (Italian accounting firms) — welcome emails,
task digests, communication campaigns, and ingestion reports. Currently, all emails are
sent from `noreply@pratikoai.com` via a single global SMTP configuration.

### Problems with the current approach

1. **Low trust**: Clients of a studio receive emails from an unknown `pratikoai.com` domain,
   reducing open rates. Italian commercialisti have a trusted, personal relationship with
   their clients — emails from `info@studiorossi.it` have significantly higher credibility.

2. **Shared blast radius**: If the PratikoAI domain gets spam-listed, ALL studios are
   affected simultaneously.

3. **No brand identity**: Studios cannot present communications under their own brand.

4. **Reply handling**: Replies go to PratikoAI, not the studio.

### Requirements

- Studios on the **Base plan (€25/mo)** should work out of the box with zero configuration.
- Studios on **Pro (€75/mo)** and **Premium (€150/mo)** plans should have the option to
  configure their own SMTP for branded email sending.
- GDPR (Art. 32) mandates appropriate security measures for stored credentials.
- Credentials must never leak in logs, API responses, or error messages.

## Decision

### Hybrid email sending with plan-based gating

We implement a two-tier email sending system:

| Tier | Plans | Sender | Configuration |
|------|-------|--------|---------------|
| **Default** | All (Base, Pro, Premium) | `"Studio Name" <comunicazioni@pratikoai.com>` with `Reply-To: studio@email.it` | Zero-config, works immediately |
| **Custom SMTP** | Pro, Premium only | `"Studio Name" <info@studiorossi.it>` via studio's own SMTP server | Studio configures in Settings UI |

### Key design choices

#### 1. Separate `studio_email_configs` table (not JSONB)

SMTP credentials are sensitive data. Storing them in a dedicated table with encrypted
columns provides:
- Clear data lifecycle (easy to purge on studio deletion / GDPR erasure)
- Column-level encryption via Fernet (key in env var, not DB)
- Audit trail via `updated_at` timestamp
- Clean foreign key to `user` (owner of the config)

#### 2. Fernet symmetric encryption for SMTP password

- Encryption key stored in `SMTP_ENCRYPTION_KEY` environment variable
- Password encrypted at write time, decrypted only when establishing SMTP connection
- Password field is **write-only** in API — never returned in GET responses
- Uses `cryptography.fernet.Fernet` (AES-128-CBC with HMAC-SHA256)

#### 3. Plan gating at service level

The `StudioEmailConfigService` checks `user.billing_plan_slug` before allowing
SMTP configuration. This is enforced at:
- API endpoint level (403 for Base plan users)
- Service level (double-check before saving)

#### 4. Fallback chain

When sending an email for a user/studio:
1. Check if user has a verified custom SMTP config → use it
2. If no custom config or config fails → fall back to PratikoAI default SMTP
3. If default SMTP also fails → log error, do not silently drop

#### 5. Connection validation before save

When a studio submits SMTP credentials, the service:
1. Encrypts the password
2. Attempts an SMTP handshake (EHLO + STARTTLS + LOGIN) without sending any email
3. Only persists the config if the handshake succeeds
4. Marks config as `is_verified = True`

### Security hardening

| Threat | Mitigation |
|--------|------------|
| Credential leakage in logs | Password field excluded from `__repr__`, `dict()`, and structured logs |
| Credential leakage in API | Password is write-only; GET returns `has_password: true` instead |
| SSRF via malicious SMTP host | Allowlist ports (25, 465, 587); connection timeout 10s; no IP ranges (10.x, 172.x, 192.168.x) |
| Brute-force config testing | Rate limit: 5 test attempts per hour per user |
| Key compromise | Fernet key rotation supported; re-encrypt all passwords with new key |
| Unauthorized access | Only the user who created the config can read/update/delete it |

### Data model

```python
class StudioEmailConfig(SQLModel, table=True):
    __tablename__ = "studio_email_configs"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, index=True)

    # SMTP settings
    smtp_host: str = Field(max_length=255)
    smtp_port: int = Field(default=587)
    smtp_username: str = Field(max_length=255)
    smtp_password_encrypted: str = Field(max_length=1024)  # Fernet-encrypted
    use_tls: bool = Field(default=True)

    # Sender identity
    from_email: str = Field(max_length=255)
    from_name: str = Field(max_length=255)
    reply_to_email: str | None = Field(default=None, max_length=255)

    # Status
    is_verified: bool = Field(default=False)
    is_active: bool = Field(default=True)

    # Audit
    created_at: datetime
    updated_at: datetime
```

### API endpoints

```
POST   /api/v1/email-config          — Create/update SMTP config (Pro/Premium only)
GET    /api/v1/email-config          — Get config (password redacted)
DELETE /api/v1/email-config          — Remove custom config (reverts to default)
POST   /api/v1/email-config/test     — Send test email to verify config
```

## Consequences

### Positive

- **Zero-friction onboarding**: Base plan studios send emails immediately with no setup
- **Professional branding**: Pro/Premium studios send from their own domain
- **Isolated reputation**: Custom SMTP studios don't share PratikoAI's domain reputation
- **Revenue driver**: Custom email is a clear upsell from Base → Pro
- **GDPR compliant**: Encrypted credentials, write-only API, clear data lifecycle

### Negative

- **Credential storage burden**: We become responsible for securing SMTP passwords (mitigated by Fernet encryption + env-based key)
- **Variable deliverability**: Studios with misconfigured email servers may experience delivery failures (mitigated by connection validation + fallback)
- **Support overhead**: Studios may need help configuring SMTP settings (mitigated by test endpoint + clear error messages in Italian)

## Related

- **ADR-017**: Multi-tenancy architecture (studio model)
- **ADR-027**: Usage-based billing (plan tiers: Base/Pro/Premium)
- **ADR-033**: Redis security hardening (defense-in-depth pattern reused here)
- **DEV-412**: Email tracking with link-based consent
