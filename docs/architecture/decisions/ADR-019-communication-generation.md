# ADR-019: Communication Generation as LangGraph Tool

**Status:** PROPOSED
**Date:** 2025-12-15
**Decision Makers:** PratikoAI Architect (Egidio), Michele Giannone (Stakeholder)
**Context Review:** PratikoAI 2.0 - FR-004 Proactive Suggestions & Communication Generation

---

## Context

### The Vision

PratikoAI 2.0 enables professionals to generate and send personalized communications to their clients about relevant regulations, deadlines, and opportunities.

Example flow:
1. **Trigger**: Professional asks "Prepara una comunicazione sulla rottamazione per i miei clienti forfettari"
2. **AI Generation**: System generates professional Italian message using client data
3. **Review**: Professional reviews and approves the draft
4. **Send**: Email or WhatsApp link generated for sending

### Requirements (Stakeholder Confirmed)

1. **Always approval**: AI prepares, professional always approves before sending
2. **WhatsApp support**: Generate wa.me links (zero cost, MVP-friendly)
3. **Email support**: Use existing SMTP (Gmail) for MVP
4. **Templates**: Pre-defined templates for common scenarios
5. **Personalization**: Insert client name, company, relevant details
6. **Audit trail**: Log all communications for compliance

### Existing Patterns

PratikoAI already uses LangGraph tools for specialized tasks:

```python
# Existing tool pattern
class FAQTool:
    """Tool for retrieving FAQ answers."""

    async def execute(self, query: str) -> FAQResult:
        return await self.faq_service.get_answer(query)

class CCNLTool:
    """Tool for CCNL calculations."""

    async def execute(self, ccnl: str, query: str) -> CCNLResult:
        return await self.ccnl_service.calculate(ccnl, query)
```

---

## Decision

### ADOPT: Communication Generation as LangGraph Tool

We will implement communication generation as a **LangGraph tool** following established patterns, with a **4-step workflow state machine** for approval flow.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    LangGraph RAG Pipeline                       │
├─────────────────────────────────────────────────────────────────┤
│ User Query: "Prepara comunicazione rottamazione per forfettari" │
│                              │                                  │
│                              ▼                                  │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │              MessageGeneratorTool                           │ │
│ │  - Identify intent: CREATE_COMMUNICATION                    │ │
│ │  - Extract: topic=rottamazione, target=forfettari           │ │
│ │  - Generate: Professional Italian message                   │ │
│ │  - Create: Communication(status=DRAFT)                      │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                              │                                  │
│                              ▼                                  │
│ Response: "Ho preparato una bozza per 3 clienti. Vuoi           │
│            approvarla o modificarla?"                           │
└─────────────────────────────────────────────────────────────────┘
```

### Component 1: MessageGeneratorTool

**File:** `app/core/langgraph/tools/message_generator_tool.py`

```python
from pydantic import BaseModel
from app.services.communication_service import CommunicationService

class MessageGeneratorInput(BaseModel):
    """Input schema for message generation."""
    topic: str
    target_criteria: dict  # e.g., {"regime_fiscale": "FORFETTARIO"}
    channel: str = "email"  # "email" or "whatsapp"
    template_id: str | None = None

class MessageGeneratorTool:
    """
    LangGraph tool for generating professional communications.

    Follows established tool pattern (FAQTool, CCNLTool).
    """

    name = "message_generator"
    description = """
    Generate professional communications for clients.
    Use when user asks to:
    - Prepare a message/communication
    - Notify clients about something
    - Send information to clients
    """

    def __init__(self, communication_service: CommunicationService):
        self.communication_service = communication_service

    async def execute(
        self,
        input: MessageGeneratorInput,
        user: User,
        matched_clients: list[Client]
    ) -> CommunicationResult:
        """
        Generate communication draft for matched clients.

        Always creates DRAFT status - never sends automatically.
        """
        # Generate personalized message
        content = await self._generate_content(
            topic=input.topic,
            template_id=input.template_id,
            client_count=len(matched_clients)
        )

        # Create communication records (one per client or batch)
        communications = await self.communication_service.create_batch_draft(
            studio_id=user.studio_id,
            client_ids=[c.id for c in matched_clients],
            subject=self._generate_subject(input.topic),
            content=content,
            channel=input.channel,
            created_by=user.id
        )

        return CommunicationResult(
            communications=communications,
            message=f"Ho preparato una bozza per {len(matched_clients)} clienti.",
            action_required="REVIEW_AND_APPROVE"
        )
```

### Component 2: Communication Service

**File:** `app/services/communication_service.py`

```python
from enum import Enum
from sqlmodel import SQLModel

class CommunicationStatus(str, Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    SENT = "sent"
    FAILED = "failed"
    REJECTED = "rejected"

class CommunicationService:
    """
    Service for managing communications with workflow state machine.

    Workflow: DRAFT -> PENDING_REVIEW -> APPROVED -> SENT
    """

    async def create_draft(
        self,
        studio_id: UUID,
        client_id: UUID,
        subject: str,
        content: str,
        channel: str,
        created_by: UUID
    ) -> Communication:
        """Create a new communication in DRAFT status."""
        communication = Communication(
            studio_id=studio_id,
            client_id=client_id,
            subject=subject,
            content=content,
            channel=channel,
            status=CommunicationStatus.DRAFT,
            created_by=created_by
        )
        await self.db.add(communication)
        await self.db.commit()

        await self._audit_log("COMMUNICATION_CREATED", communication)
        return communication

    async def submit_for_review(
        self,
        communication_id: UUID,
        user: User
    ) -> Communication:
        """Submit draft for review. Only creator can submit."""
        communication = await self._get_communication(communication_id)
        self._validate_studio_access(communication, user)

        if communication.status != CommunicationStatus.DRAFT:
            raise InvalidStateTransition(f"Cannot submit {communication.status} for review")

        communication.status = CommunicationStatus.PENDING_REVIEW
        await self.db.commit()

        await self._audit_log("COMMUNICATION_SUBMITTED", communication)
        return communication

    async def approve(
        self,
        communication_id: UUID,
        user: User
    ) -> Communication:
        """
        Approve communication for sending.

        Note: For MVP, same user can approve (single-operator studio).
        Future: Require different approver than creator.
        """
        communication = await self._get_communication(communication_id)
        self._validate_studio_access(communication, user)

        if communication.status != CommunicationStatus.PENDING_REVIEW:
            raise InvalidStateTransition(f"Cannot approve {communication.status}")

        communication.status = CommunicationStatus.APPROVED
        communication.approved_by = user.id
        communication.approved_at = datetime.utcnow()
        await self.db.commit()

        await self._audit_log("COMMUNICATION_APPROVED", communication)
        return communication

    async def send(
        self,
        communication_id: UUID,
        user: User
    ) -> Communication:
        """Send approved communication via configured channel."""
        communication = await self._get_communication(communication_id)
        self._validate_studio_access(communication, user)

        if communication.status != CommunicationStatus.APPROVED:
            raise InvalidStateTransition(f"Cannot send {communication.status}")

        try:
            if communication.channel == "email":
                await self._send_email(communication)
            elif communication.channel == "whatsapp":
                # WhatsApp generates link, doesn't auto-send
                communication.whatsapp_link = self._generate_whatsapp_link(communication)

            communication.status = CommunicationStatus.SENT
            communication.sent_at = datetime.utcnow()
        except Exception as e:
            communication.status = CommunicationStatus.FAILED
            communication.error_message = str(e)

        await self.db.commit()
        await self._audit_log("COMMUNICATION_SENT", communication)
        return communication
```

### Component 3: WhatsApp Link Service

**File:** `app/services/whatsapp_link_service.py`

```python
from urllib.parse import quote

class WhatsAppLinkService:
    """
    Generate wa.me links for WhatsApp communication.

    No API integration needed - just URL generation.
    """

    BASE_URL = "https://wa.me"

    def generate_link(
        self,
        phone: str,
        message: str
    ) -> str:
        """
        Generate WhatsApp click-to-chat link.

        Args:
            phone: International format without + (e.g., "393401234567")
            message: Message to pre-fill (will be URL encoded)

        Returns:
            wa.me URL with pre-filled message
        """
        # Normalize phone number
        normalized_phone = self._normalize_phone(phone)

        # URL encode message
        encoded_message = quote(message, safe='')

        return f"{self.BASE_URL}/{normalized_phone}?text={encoded_message}"

    def _normalize_phone(self, phone: str) -> str:
        """Remove +, spaces, dashes from phone number."""
        return ''.join(c for c in phone if c.isdigit())
```

### Component 4: Communication Templates

**File:** `app/templates/communications/`

```jinja2
{# templates/communications/rottamazione.html #}
Gentile {{ client.nome }},

La informiamo che la Rottamazione Quater è stata estesa ai contribuenti
in regime forfettario.

Questa agevolazione potrebbe interessare la sua posizione fiscale.

**Cosa prevede:**
- Pagamento del debito senza sanzioni e interessi di mora
- Possibilità di rateizzazione fino a 18 rate
- Scadenza adesione: {{ deadline | date("d/m/Y") }}

Le consigliamo di contattarci per valutare insieme se aderire
all'agevolazione.

Cordiali saluti,
{{ studio.name }}
```

```jinja2
{# templates/communications/scadenza_f24.html #}
Gentile {{ client.nome }},

Le ricordiamo che il {{ deadline | date("d/m/Y") }} scade il termine
per il versamento {{ payment_type }}.

**Dettagli:**
- Importo da versare: € {{ amount | number_format(2, ',', '.') }}
- Codice tributo: {{ tax_code }}

Per qualsiasi chiarimento, non esiti a contattarci.

Cordiali saluti,
{{ studio.name }}
```

### Database Model

**File:** `app/models/communication.py`

```python
from sqlmodel import SQLModel, Field, Relationship
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy import Column, DateTime, Text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB

class CommunicationStatus(str, Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    SENT = "sent"
    FAILED = "failed"
    REJECTED = "rejected"

class CommunicationChannel(str, Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"

class Communication(SQLModel, table=True):
    __tablename__ = "communication"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    studio_id: UUID = Field(foreign_key="studio.id", index=True)
    client_id: UUID = Field(foreign_key="client.id", index=True)

    # Content
    subject: str = Field(max_length=200)
    content: str = Field(sa_column=Column(Text))
    channel: CommunicationChannel = Field(sa_column=Column(SAEnum(CommunicationChannel)))

    # Workflow
    status: CommunicationStatus = Field(
        default=CommunicationStatus.DRAFT,
        sa_column=Column(SAEnum(CommunicationStatus), index=True)
    )
    created_by: UUID = Field(foreign_key="user.id")
    approved_by: UUID | None = Field(default=None, foreign_key="user.id")

    # Timestamps
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    approved_at: datetime | None = None
    sent_at: datetime | None = None

    # Channel-specific
    whatsapp_link: str | None = Field(default=None, max_length=500)
    email_message_id: str | None = Field(default=None, max_length=100)
    error_message: str | None = Field(default=None, max_length=500)

    # Metadata
    template_id: str | None = Field(default=None, max_length=50)
    metadata: dict = Field(default_factory=dict, sa_column=Column(JSONB))

    # Relationships
    client: "Client" = Relationship(back_populates="communications")
    studio: "Studio" = Relationship(back_populates="communications")
```

---

## Alternatives Considered

### 1. External Email Service (SendGrid, Postmark)

**Pros:**
- Better deliverability
- Built-in tracking (opens, clicks)
- Template management

**Cons:**
- Additional cost (~$20/month for 10K emails)
- Vendor dependency
- MVP complexity

**Decision:** Defer to post-MVP. Use existing Gmail SMTP for now.

### 2. WhatsApp Business API

**Pros:**
- Official integration
- Message templates
- Read receipts

**Cons:**
- Requires business verification (weeks)
- Per-message cost (~$0.05/message)
- Complex setup

**Decision:** Use wa.me links for MVP (zero cost, instant setup).

### 3. Separate Microservice for Communications

**Pros:**
- Separation of concerns
- Independent scaling

**Cons:**
- Operational complexity
- Latency overhead
- MVP overkill

**Decision:** Keep as service within monolith for MVP.

---

## Consequences

### Positive

1. **Follows patterns**: Same tool pattern as FAQTool, CCNLTool
2. **Always approval**: DRAFT → APPROVED workflow enforced
3. **Zero cost WhatsApp**: wa.me links require no API
4. **Audit trail**: All state transitions logged
5. **Template flexibility**: Jinja2 templates are easy to customize

### Negative

1. **Manual WhatsApp send**: User must click link and send
2. **Gmail limitations**: 500 emails/day limit
3. **No tracking**: Can't track email opens without external service

### Mitigations

1. **WhatsApp**: Clear UX showing link to click
2. **Email limits**: Monitor usage, upgrade to SendGrid if needed
3. **Tracking**: Add pixel tracking post-MVP

---

## API Endpoints

**File:** `app/api/v1/communications.py`

```python
from fastapi import APIRouter, Depends
from app.services.communication_service import CommunicationService

router = APIRouter(prefix="/communications", tags=["Communications"])

@router.post("/draft")
async def create_draft(
    request: CreateDraftRequest,
    user: User = Depends(get_current_user),
    service: CommunicationService = Depends()
) -> CommunicationResponse:
    """Create a new communication draft."""
    return await service.create_draft(
        studio_id=user.studio_id,
        client_id=request.client_id,
        subject=request.subject,
        content=request.content,
        channel=request.channel,
        created_by=user.id
    )

@router.patch("/{communication_id}/submit")
async def submit_for_review(
    communication_id: UUID,
    user: User = Depends(get_current_user),
    service: CommunicationService = Depends()
) -> CommunicationResponse:
    """Submit draft for review."""
    return await service.submit_for_review(communication_id, user)

@router.patch("/{communication_id}/approve")
async def approve_communication(
    communication_id: UUID,
    user: User = Depends(get_current_user),
    service: CommunicationService = Depends()
) -> CommunicationResponse:
    """Approve communication for sending."""
    return await service.approve(communication_id, user)

@router.post("/{communication_id}/send")
async def send_communication(
    communication_id: UUID,
    user: User = Depends(get_current_user),
    service: CommunicationService = Depends()
) -> CommunicationResponse:
    """Send approved communication."""
    return await service.send(communication_id, user)

@router.get("/")
async def list_communications(
    status: CommunicationStatus | None = None,
    user: User = Depends(get_current_user),
    service: CommunicationService = Depends()
) -> list[CommunicationResponse]:
    """List communications for user's studio."""
    return await service.list_communications(user.studio_id, status)
```

---

## Security Considerations

### Data Protection

| Data | Protection | Notes |
|------|------------|-------|
| Client email | Encrypted at rest | EncryptedType |
| Client phone | Encrypted at rest | EncryptedType |
| Message content | Not encrypted | May contain PII |
| WhatsApp link | Contains message | URL encoded |

### Access Control

1. **Studio isolation**: Can only access own studio's communications
2. **Role-based (future)**: Creator vs approver roles
3. **Audit logging**: All actions logged with user ID

### GDPR Compliance

1. **Consent**: Client must have consented to communications
2. **Retention**: Communications retained for audit (configurable)
3. **Deletion**: CASCADE delete when client deleted

---

## Testing Strategy

### Unit Tests

```python
# tests/services/test_communication_service.py

async def test_workflow_draft_to_sent():
    """Full workflow from draft to sent."""
    comm = await service.create_draft(...)
    assert comm.status == CommunicationStatus.DRAFT

    comm = await service.submit_for_review(comm.id, user)
    assert comm.status == CommunicationStatus.PENDING_REVIEW

    comm = await service.approve(comm.id, user)
    assert comm.status == CommunicationStatus.APPROVED

    comm = await service.send(comm.id, user)
    assert comm.status == CommunicationStatus.SENT

async def test_cannot_send_draft():
    """Cannot send without approval."""
    comm = await service.create_draft(...)

    with pytest.raises(InvalidStateTransition):
        await service.send(comm.id, user)

async def test_studio_isolation():
    """Cannot access other studio's communications."""
    comm = await service.create_draft(studio_id=studio_a.id, ...)

    with pytest.raises(PermissionDenied):
        await service.approve(comm.id, user_from_studio_b)
```

### Integration Tests

```python
# tests/integration/test_communication_generation.py

async def test_generate_communication_via_chat():
    """Chat generates communication draft."""
    response = await chat(
        user=user,
        query="Prepara una comunicazione sulla rottamazione per i forfettari"
    )

    assert "bozza" in response.lower()

    communications = await service.list_communications(
        user.studio_id,
        status=CommunicationStatus.DRAFT
    )
    assert len(communications) > 0
```

---

## References

- ADR-017: Multi-Tenancy Architecture (provides `studio_id`)
- ADR-018: Normative Matching Engine (provides matched clients)
- `app/core/langgraph/tools/faq_tool.py` - Tool pattern reference
- `app/services/email_service.py` - Existing email infrastructure
- docs/tasks/PRATIKO_2.0.md - Phase 3 tasks (DEV-2.0-031 to DEV-2.0-040)

---

## Revision History

- 2025-12-15: Initial version - Communication generation as LangGraph tool
