# Build Week Changes

- New repository: `ralphiia-quoteops`
- New scope: QuoteOps for OpenAI Build Week 2026
- New API minimum: health, meta, and intake preview
- New contracts: intake, missing information, risks, proposal options, review, mission state
- New external trust anchor: provider-neutral RUC verification with an Intuito Azure adapter, bounded retry, token cache, one-time refresh on 401, typed errors, and provenance.
- New identity workflow: compare verified taxpayer data with RalphiIA parties/clients and Contífico, expose conflicts, prefill a draft, and require approval.
- New isolated persistence: staging party/client/identity-map collections with unique RUC indexes and idempotent confirmation.
- New frontend module: live RUC lookup, evidence signals, reconciliation status, conflict count, and approval action.

## Conversation-first P0

- Replaced the technical cockpit with a central, responsive chat for project and quote creation.
- Added a persistent ES/EN selector and a translation catalog that covers UI text, workflow states, validation guidance, and backend mission messages.
- Added an idempotent conversation mission API with persisted progressive state in the isolated QuoteOps MongoDB database and in-memory continuity when MongoDB is unavailable.
- Added the FEMAR access-control case path: long-form project text, real attachment upload, sanitized filenames, 25 MB limit, SHA-256 evidence, missing-information questions, risks, assumptions, options, and progress.
- Added a single Ecuadorian identity boundary for 10-digit cédula and 13-digit RUC. Cédula uses local checksum validation and read-only internal reconciliation; only an authorized RUC calls Intuito.
- Reused the existing RalphiIA and Contífico identity readers without production writes or duplicate creation.
- Added an integration trace projection for MCP, Intuito, Contífico, Smart Quoter, MongoDB, and PDF with real source, observed call, status, latency, UTC time, and sanitized result.
- Added editable quote lines with zero initial prices, preventing invented commercial values.
- Added idempotent price update, human approval, real PDF artifact generation, and isolated delivery registration.
- Changed deterministic intake metadata from a model-like fallback label to `deterministic_rules`.
- Added unit and API integration coverage for conversation, language, attachments, identity validation, idempotency, quote transition, approval, PDF, and delivery.
- Preserved all unrelated untracked parser, reconciliation, cash-flow, and watchdog files.

## Public progress feed

- Added a bilingual, read-only `GET /api/public/progress` contract for the separate Astro website.
- Added a curated public manifest for milestones, decisions, verification evidence, and H1-H7 progress.
- Reduced integration visibility to name and status only in the public projection; internal sources, calls, latency, results, customer data, documents, and identifiers remain private.
- Added defensive redaction for Ecuadorian identifiers, IP addresses, local paths, and secret-like values.
- Added stable revisions and a 15-second refresh hint so a static Astro site can update without rebuilding.
