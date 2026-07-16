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

## FEMAR end-to-end and ChatGPT MCP

- Added a real work item per conversation mission with deterministic IDs, status, next action, source channel, and a bounded timeline.
- Expanded the FEMAR proposal into three packages: selective rehabilitation, hybrid modernization, and full renewal.
- Added typed multimodal evidence contracts so ChatGPT can persist facts, product candidates, and supplier prices extracted from images, PDFs, product labels, site photos, and price lists.
- Added explicit source linkage, SHA-256 provenance when the original is stored, confidence, page/region, warnings, review status, and human confirmation/rejection.
- Added idempotent supplier offers with exact costs, source reference, optional stored attachment evidence, package assignment, and staging-only catalog drafts.
- Added read-only exact catalog reconciliation so known SKUs are linked, while unknown products and services require explicit human approval into the isolated staging catalog.
- Kept supplier cost separate from selling price. Selecting a package never copies cost into the customer price; selling values remain zero until entered by a human.
- Expanded the generated PDF to include selected package, quote lines, subtotal, tax, and total while intentionally excluding internal supplier costs.
- Added a typed staging MCP surface for mission, evidence, supplier offer, package, quote, approval, and delivery operations. It exposes no shell, arbitrary Mongo query, or generic URL execution.
- Preserved the production boundary: the shared RalphiIA MCP service and gateway were audited read-only and were not restarted or modified.

## Real supplier catalog ingestion

- Archived nine original PDF/image sources with SHA-256 provenance and recorded nine human-confirmed multimodal evidence entries.
- Deduplicated 39 priced products before persistence: four existing catalog SKUs were linked and 35 missing items were approved only in the isolated QuoteOps staging catalog.
- Preserved unknown tax treatment as `null` because the supplier sources did not state whether tax was included.
- Kept imported catalog prices outside FEMAR packages until a human selects the technical architecture; supplier cost never became selling price.
- Verified 39 unique SKUs, 39 canonical links, zero duplicate staging SKUs, and zero production catalog writes.

## Evidence-backed multichannel decisions

- Added one shared decision workspace per mission for confirmed requirements, assumptions, validation needs, open questions, selected assistant metadata, and alternatives A/B/C.
- Added a common idempotent channel-event contract so web, ChatGPT MCP, WhatsApp, Telegram, and typed API clients can start or continue the same mission. Channel event IDs are persisted through mission operation keys instead of relying only on process memory.
- Added typed MCP and HTTP operations to update the decision brief, upsert a configuration alternative, and record explicit human approval or rejection.
- Configuration callers can reference only supplier offer lines already stored in the mission. QuoteOps resolves SKU, description, supplier, canonical item, unit cost, and line cost from the source offer; caller-supplied cost fields are rejected.
- Added compatibility safeguards: verified lines require confirmed evidence and an approved staging/canonical catalog link; unknown, ambiguous, duplicated, rejected, or unreviewed items are blocked with bilingual errors.
- Added a technical review gate before package selection. Only an approved alternative can become an editable quote; its selling prices still start at zero and internal costs remain out of the customer PDF.
- Added a bilingual responsive decision panel for requirements, questions, assistant selection metadata, sourced products, quantities, roles, compatibility, evidence, rationale, risks, gaps, and human review.
- Kept runtime truth separate from assistant metadata. Selecting a decision assistant never changes or overstates the QuoteOps runtime label.
- Locked approved or delivered quotes against later requirement, configuration, package, or price edits. Editing a pre-approval configuration invalidates the stale quote and requires a fresh technical review.
