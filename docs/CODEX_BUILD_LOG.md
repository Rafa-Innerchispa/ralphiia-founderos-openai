# Codex Build Log

## 2026-07-16 — Build evidence generator

- Added deterministic, offline generation of `docs/evidence/manifest.json`.
- Labels each claim as measured, derived, or pending; measured Git evidence is separated from public-progress and session-document references.
- Enforces a publish boundary: secret-like data, bearer tokens, credential assignments, and Windows paths cause generation to fail or be redacted before output.
- Does not assert GPT-5.6 as QuoteOps runtime and does not invent usage or token metrics.
- Pending operator artifacts: sanitized live staging health/OpenAPI captures, screenshots, demo video, and approved Session IDs.

## 2026-07-16 — Integration hardening

- Replaced the evidence tests with standard-library `unittest`; no `pytest` dependency remains.
- Made the source revision resolve to the newest reachable functional/non-evidence commit, excluding evidence-only changes, so a cherry-pick or regeneration does not self-reference.
- Expanded fail-closed redaction/rejection to emails, IPv4, `/home/...` paths, Ecuadorian 10/13-digit identifiers, and 9–15 digit phones, while allowing Git hashes, dates, and relative paths.
- Verification: focused `unittest` 7 tests passed; full `unittest discover` 52 tests passed. The suite emitted one existing Starlette/httpx deprecation warning.
