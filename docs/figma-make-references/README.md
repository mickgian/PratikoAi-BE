# Figma Make Design References

Source code extracted from the PratikoAI Figma Make project as design specifications.

**Figma Make Project:** https://www.figma.com/make/zeerNWSwapo0VxhMEc6DWx/PratikoAI-Landing-Page

## How to Use
These files serve as design references for Claude Desktop APP. They contain the exact React+Tailwind
component code from Figma Make, showing layout, styling, mock data structures, and interaction patterns.

## How to Update
When new screens are created in Figma Make, use the Figma MCP `get_design_context` tool or
`ReadMcpResourceTool` with URI `file://figma/make/source/zeerNWSwapo0VxhMEc6DWx/components/{ComponentName}.tsx`
to fetch the latest source and save it here.

## Available References

| File | Description | Used By |
|------|-------------|---------|
| `GestioneComunicazioniPage.tsx` | Communication Dashboard (Screen 1) | DEV-330, 332, 335, 336, 338 |
| `ClientListPage.tsx` | Client List with filters, bulk actions | DEV-308, 312, 314, 316, 318 |
| `ClientDetailPage.tsx` | Client Detail/Edit form (5 tabs) | DEV-308, 312, 317, 320, 322 |
| `ClientImportPage.tsx` | Excel/CSV Import wizard (3 steps) | DEV-310, 312, 313 |
| `ScadenzeFiscaliPage.tsx` | Fiscal Deadlines calendar/list | DEV-385, 386, 437, 438 |
| `GDPRCompliancePage.tsx` | GDPR Compliance dashboard | DEV-378, 380 |
| `DashboardPage.tsx` | ROI Dashboard & Analytics (Screen 3) | DEV-354, 355, 356, 434, 435, 436 |
| `NotificationsDropdown.tsx` | Notification Panel (Screen 6) | DEV-384, 385, 422-427, 440 |
| `MatchingNormativoPage.tsx` | Matching Results page wrapper (Screen 4) | DEV-326 |
| `RisultatiMatchingNormativoPanel.tsx` | Matching Results panel (Screen 4) | DEV-320, 326 |
| `ProcedureSelector.tsx` | Slash Command Procedure Selector (Screen 7) | DEV-402 |
| `ProceduraInterattivaPage.tsx` | Procedura Interattiva page (Screen 2) | DEV-340, 342, 343, 344 |
| `ClientMentionAutocomplete.tsx` | Client Mention Autocomplete dropdown + pill + context card (Screen 8) | DEV-403 |
| `ClientActionPicker.tsx` | Client Action Picker — 4-action grid + full profile card (Screen 8) | DEV-403, 428, 429 |
| `ChatPage.tsx` | Chat Page entry point with mentions integration (Screen 8) | DEV-403, 430, 433, 439 |
