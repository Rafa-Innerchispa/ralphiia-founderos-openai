# Live RUC Evidence (Sanitized)

Date: 2026-07-14 (America/Guayaquil)

Environment:

- Host: `ralphi-ia-ver-10` (`192.168.1.4`)
- Repository: `/home/rlopez/projects/ralphiia-quoteops`
- Staging UI/API: port `8772`
- Persistence: `ralphiia_quoteops_staging`
- Production writes: disabled

Security controls:

- The confidential provider manual is not present in this repository.
- Provider credentials exist only in the server `.env`, mode `0600`.
- Token and credential values were never printed or written to evidence.
- Representative identification is not modeled, persisted, returned, or shown.
- Public tests use an HTTP mock and never contact the provider.

Live acceptance results:

| Check | Result | Sanitized evidence |
|---|---|---|
| DNS and TLS, token host | PASS | Azure host resolved; TLS verification result `0` |
| DNS and TLS, lookup host | PASS | Azure host resolved; TLS verification result `0` |
| Real token | PASS | Usable token received; value suppressed |
| Existing authorized RUC | PASS | `099236***6001`; provider verified; 29 establishments returned |
| RalphiIA comparison | PASS | Exact matches in `crm_parties` and `ops_clients` |
| New authorized RUC | PASS | `099340***5001`; provider verified; one establishment returned |
| First confirmation | PASS | Created one staging party and one staging client |
| Repeated live lookup | PASS | Resolved `quoteops_staging`; recommended action changed to `update` |
| Second confirmation | PASS | Same party/client IDs; `created=false`; `duplicate_count=1` |
| Frontend automatic load | PASS | Legal name, primary establishment, source matches, action, and approval gate rendered |
| Automated tests | PASS | 7 unit/contract tests |

Provider-authoritative checksum note:

The second owner-authorized RUC is structurally valid but does not pass the legacy local check-digit formula. The provider returned a verified taxpayer record. QuoteOps therefore records `checksum_valid=false` as an explicit warning while retaining the provider response as the authoritative live result. Invalid length or non-numeric input is still rejected before network access.

No production customer record was changed during this evidence run.
