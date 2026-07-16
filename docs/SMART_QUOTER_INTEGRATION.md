# Smart Quoter Integration

QuoteOps reuses selected capabilities from the existing InnerSpark Smart Quoter service at `127.0.0.1:2026` through a read-only adapter. The repository and service were audited without edits on 2026-07-15.

## Reused operations

- `GET /api/quote/client-lookup/{client_id}` for existing client context.
- `POST /api/quote/diagnose` for the existing local diagnostic engine.
- `POST /api/quote/diagnose/refine` for operator-guided refinement.

## QuoteOps Boundary

The adapter lives at `quoteops/adapters/smart_quoter.py`. QuoteOps exposes these calls through its own API and frontend, but does not let the legacy service create clients, save quotes, or deliver messages without the QuoteOps approval gate.

The frontend labels the source as Smart Quoter 2026 and marks writes as blocked.

The conversation-first UI does not copy the legacy dashboard. It reuses only the useful concepts of progressive diagnosis, operator refinement, client context, editable quoting, PDF, and delivery gates. QuoteOps owns the new mission state, bilingual experience, idempotency, trace model, and approval boundary.

## Validation

- Smart Quoter process verified on port `2026`.
- OpenAPI title observed: `InnerSpark Smart Quoter API`, version `0.1.0`.
- Read-only audit observed the available quote, audio, diagnostic, refinement, developer-helper, delivery, and transcription routes. No create, save, upload, delivery, or developer-helper route was called during the audit.
- Read-only client lookup verified with an authorized, masked RUC `099******6001` and HTTP 200.
- QuoteOps adapter and frontend compile successfully.
- QuoteOps targeted tests pass.
