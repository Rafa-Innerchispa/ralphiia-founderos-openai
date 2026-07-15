# Smart Quoter Integration

QuoteOps reuses the existing InnerSpark Smart Quoter service at `127.0.0.1:2026` through a read-only adapter.

## Reused operations

- `GET /api/quote/client-lookup/{client_id}` for existing client context.
- `POST /api/quote/diagnose` for the existing local diagnostic engine.
- `POST /api/quote/diagnose/refine` for operator-guided refinement.

## QuoteOps Boundary

The adapter lives at `quoteops/adapters/smart_quoter.py`. QuoteOps exposes these calls through its own API and frontend, but does not let the legacy service create clients, save quotes, or deliver messages without the QuoteOps approval gate.

The frontend labels the source as Smart Quoter 2026 and marks writes as blocked.

## Validation

- Smart Quoter process verified on port `2026`.
- Read-only client lookup verified with RUC `0992364866001` and HTTP 200.
- QuoteOps adapter and frontend compile successfully.
- QuoteOps targeted tests pass.
