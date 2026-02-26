# ADR-036: No Document Upload/Storage in Interactive Procedures

## Status
**ACCEPTED** — 2026-02-26

## Context

FR-001 (Procedure Interattive) includes a Figma design (`ProceduraInterattivaPage.tsx`) that shows
document upload, download, and delete functionality within each procedure step. The design includes:

- A `Document` interface with `uploaded: boolean`, `uploadDate: string` fields
- Upload buttons ("Carica") for each required document per step
- Download/Delete buttons for already-uploaded documents
- A "Documenti richiesti" section showing upload status per document

Task DEV-344 ("Procedura Notes and Attachments") explicitly plans to implement
`add_attachment(progress_id, step_num, file)` with 10MB file upload support.

### The Problem

Storing studio/client documents on the server is **not viable** for the web application:

1. **Security risk**: Client documents (identity cards, tax forms, contracts) are highly sensitive.
   Storing them on a shared server creates a liability if breached. The server becomes a
   high-value target.

2. **GDPR compliance**: Permanent storage of client documents on a third-party server requires
   explicit legal basis, data processing agreements, and retention policies. The existing
   FR-008 document analysis feature already established the principle of **temporary/in-memory
   processing only** with 30-minute auto-deletion (see `Policy_Documenti` in PRATIKO_2.0_REFERENCE).

3. **Storage costs**: Documents accumulate rapidly. A studio with 200 clients and 10 procedures
   each, with 5 documents per procedure = 10,000 files. At 5MB average = 50GB per studio.
   This scales linearly with studios.

4. **Not the core value**: PratikoAI's value is AI-assisted guidance, not document management.
   Studios already have established document management workflows (local folders, email,
   gestionale software).

5. **Future desktop app**: A local desktop application with a local database is the proper venue
   for document storage, where files never leave the user's machine.

### What FR-008 Already Decided

FR-008 (Upload & Analysis) explicitly states:
```yaml
Policy_Documenti:
  storage:
    tipo: "temporaneo in memoria"
    persistenza: false
  eliminazione:
    automatica: true
    trigger: ["fine sessione", "richiesta utente", "timeout 30 minuti inattività"]
  dati_estratti:
    salvati: false
  gdpr_compliance:
    informativa: "I documenti caricati vengono elaborati in tempo reale
                  e non vengono salvati sui nostri server."
```

Procedure document storage would directly contradict this policy.

## Decision

**Remove document upload/storage from FR-001 Interactive Procedures.**

Replace the upload-based "Documenti richiesti" section with a **document verification checklist**:

### What changes:

| Before (Upload-based) | After (Checklist-based) |
|---|---|
| Upload/Download/Delete buttons per document | Checkbox per document ("Ricevuto" / "Verificato") |
| `uploaded: boolean` + `uploadDate` | `verified: boolean` + `verifiedAt` + optional `note` |
| Server stores actual files | Server stores only verification status |
| 10MB file upload endpoint | No file handling needed |
| "Carica" button | Checkbox + optional note field |

### What stays:

- **Notes per step**: Text notes remain (DEV-344 notes functionality is preserved)
- **Document checklist items**: The list of required documents per step remains
- **Document names**: Procedure templates still define which documents are needed
- **Progress tracking**: "3 of 5 documents verified" progress still works

### New document checklist model (conceptual):

```python
# Inside ProceduraProgress.completed_steps JSONB
{
  "step_1": {
    "checklist": {"cl_001": true, "cl_002": true},
    "documents": {
      "doc_001": {"verified": true, "verified_at": "2026-02-20T10:00:00", "note": "Ricevuto via email"},
      "doc_002": {"verified": false, "note": null}
    },
    "notes": [...]
  }
}
```

## Consequences

### Positive
- No server-side file storage liability
- Full GDPR compliance (no client documents stored)
- Consistent with FR-008 "no persistence" policy
- Simpler implementation (no file upload infrastructure for procedures)
- Lower storage costs
- Accountants can still track document collection progress

### Negative
- Users cannot view documents directly in the procedure UI
- Documents must be managed externally (local filesystem, email, gestionale)

### Future
- **Desktop app (v3.0+)**: When a local desktop application is built with a local SQLite/PostgreSQL
  database, document upload can be added. Files would be stored locally on the user's machine,
  never uploaded to the server.
- **Temporary analysis**: If a user needs to analyze a document during a procedure, they can use
  the existing FR-008 chat-based upload (temporary, auto-deleted after 30min).

## Affected Tasks

| Task | Change |
|---|---|
| **DEV-344** | Remove "attachment support" scope. Keep "notes" scope only. Rename to "Procedura Notes and Document Checklist" |
| **DEV-305** | Procedure template `steps[].documents[]` becomes checklist-only (no upload fields) |
| **DEV-306** | `ProceduraProgress.completed_steps` JSONB tracks document verification, not uploads |
| **Figma design** | Replace upload UI with checkbox-based document verification |
