# Figma Prompt: Replace Document Upload with Verification Checklist (ADR-035)

## Context

In the **Procedura Interattiva** page (Screen 2), the "Documenti richiesti" section currently shows
upload/download/delete buttons for each document. Per ADR-035, we are removing server-side document
storage from procedures and replacing it with a checkbox-based verification system.

---

## Figma Make Prompt

```
CONTEXT:
In the Procedura Interattiva page, the "Documenti richiesti" section currently has Upload, Download,
and Delete buttons for each document. We need to change this to a simple checkbox-based verification
system. No files are uploaded — the accountant simply checks off that they have received/verified
each document.

DESIGN TASK:
Replace the "Documenti richiesti" section in the Procedura Interattiva step detail with a
"Documenti da verificare" (Documents to verify) section. Use the existing PratikoAI design system
colors: Blu Petrolio (#2A5D67), Avorio (#F8F5F1), and the existing green (#22C55E) for verified items.

CHANGES REQUIRED:

1. SECTION HEADER:
   - Change "Documenti richiesti" → "Documenti da verificare"
   - Keep the FileText icon

2. EACH DOCUMENT ROW:
   - Remove the Upload button ("Carica" with Upload icon)
   - Remove the Download button (Download icon)
   - Remove the Delete button (Trash icon)
   - Add a CHECKBOX on the left side of each document row (same style as the checklist checkboxes above)
   - Checkbox is disabled in "Modalità consultazione", enabled in client-specific mode

3. DOCUMENT ROW — NOT VERIFIED STATE:
   - Unchecked checkbox on the left
   - Document name in Blu Petrolio (#2A5D67)
   - If required: red "Obbligatorio" label below the name (keep as-is)
   - White background with light border (border-[#C4BDB4]/20)

4. DOCUMENT ROW — VERIFIED STATE:
   - Checked checkbox on the left (green check)
   - Document name in green (#16A34A)
   - "Verificato il [date]" in small green text below the name
   - Optional italic note in gray below (e.g., "Ricevuto via email dal cliente")
   - Light green background (bg-green-50) with green border (border-green-200)
   - Green checkmark icon on the right side

5. ADD OPTIONAL NOTE FIELD:
   - When a user checks a document, show a small optional text input below the checkbox
   - Placeholder: "Nota (opzionale): es. ricevuto via email..."
   - Same style as the notes text area but smaller and inline
   - This allows the accountant to note HOW they received the document without uploading it

6. PROGRESS INDICATOR:
   - Below the document list, show: "2 di 5 documenti verificati" (2 of 5 documents verified)
   - Use a small progress bar or fraction indicator
   - Green when all documents are verified

VISUAL REFERENCE:
The document verification rows should look similar to the checklist items above them in the same
step card. The main visual difference is:
- Checklist items = task completion checkboxes (things the accountant needs to DO)
- Document items = collection verification checkboxes (documents the accountant needs to HAVE)

Use a subtle visual distinction: document rows could have a small FileText icon next to the checkbox
to differentiate them from task checklist items.

KEEP UNCHANGED:
- The rest of the Procedura Interattiva page layout (sidebar, stepper, header, notes section)
- The "Note e allegati" section at the bottom (rename to just "Note" — remove "allegati" reference)
- The step navigation buttons at the bottom
- The client selector modal
- All color palette and spacing conventions
```

---

## Summary of Visual Changes

| Element | Before | After |
|---|---|---|
| Section title | "Documenti richiesti" | "Documenti da verificare" |
| Document row action | Upload/Download/Delete buttons | Checkbox (verified/not) |
| Verified state | Green with "Caricato il..." | Green with "Verificato il..." + optional note |
| Not verified state | Gray FileText icon + "Carica" button | Unchecked checkbox + "Obbligatorio" if required |
| Notes section title | "Note e allegati" | "Note" |
| File upload infrastructure | Upload button, drag-drop zone | None — removed entirely |

## Related

- **ADR-036:** `docs/architecture/decisions/ADR-036-no-document-storage-in-procedures.md`
- **Updated Figma reference:** `docs/figma-make-references/ProceduraInterattivaPage.tsx`
- **Task:** DEV-344 (renamed to "Procedura Notes and Document Checklist")
