# RUC Trust Anchor Architecture

The RUC module is an identity-verification stage inside CaseOps, not an isolated lookup page.

Flow:

1. Normalize and validate the 13-digit input locally.
2. Obtain or reuse a server-side provider token.
3. Query the allowlisted RUC endpoint with bounded retries and one refresh on `401`.
4. Normalize the response into `TaxpayerVerification` without representative identification.
5. Resolve the same RUC read-only through RalphiIA parties, operational clients, and Contífico.
6. Produce matches, field conflicts, a recommended action, and a prefilled customer draft.
7. Require a named human approval.
8. Upsert staging party/client records by unique RUC and maintain an identity-map link.
9. Repeat lookup/confirmation safely without duplicate records.

Trust boundaries:

- Browser: receives normalized taxpayer and reconciliation data, never credentials or bearer tokens.
- QuoteOps API: owns validation, provider calls, approval gate, and trace IDs.
- Intuito adapter: only component allowed to contact the two configured Azure hosts.
- RalphiIA reader: imports existing resolvers in read-only mode; it does not duplicate their logic.
- Staging store: separate Mongo database with unique indexes. Production writes default to disabled.

The same `TaxpayerRegistryPort` behavior can support a future official provider or a judge sandbox fixture without changing the CaseOps workflow.
