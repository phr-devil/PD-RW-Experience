# PD-RW-Experience architecture

- **PD-RW:** authoritative scientific governance, author grants and decisions.
- **PD-RW-Agent:** source project/case/Run verification and case-knowledge mirror export; no writes by Experience.
- **Case Mirror adapter (v0.2.0a1):** internal consistency verification against a PD-RW-Agent v1.2 manifest, full byte hash checks of indexed mirror files, explicit local annotations, group-aware split isolation, and private ScientificCase staging. No original source hash attestation and no fabricated historical date.
- **ACE adapter (v0.1.1):** pinned external engine, objective factual extraction only, signed target/grant preflight, bounded worker; not yet real scientific strategy distillation.
- **Scientific review / experience library:** signed lesson review and source bytes verification, reviewed-only P4 retrieval, and feedback in unverified status; no auto-rule promotion.
- **PD-RW-Orchestrator:** reads proposed P4 guidance via existing Guidance v1 contract; live end-to-end provider still pending.

## Distinguish three types of source

1. `CASE_LIBRARY` original project/PDF/Run is the primary scientific evidence; may be private.
2. PD-RW-Agent's Markdown Case Knowledge Mirror is a *verified derivative text*, not an independent verification of original observations.
3. Experience's `ScientificCase.source_refs` for this adapter intentionally point only to the mirror Markdown bytes, with `mirror_provenance.original_source_bytes_verified=false`. Never promote secondary evidence to original Run validation.

A manifest + card checksum is internal integrity only. The host must separately verify the upstream mirror against its actual original library, control publication/data-use rights, pin the reviewer trust root and run original scientific review.

## Defense in depth

- Case group plus exact mirror-card hash split checks; no TEST examples sent to ACE adaptation.
- Snapshot date is explicit and conservative; historical as-of replay requires historical original evidence.
- No inference of missing method, research question from title, evidence strength or publication permission.
- PRIVATE input stays local; external model calls remain separately gated.
- Signed review means identity and subject binding, not research truth.
- Paid calls are subject to host/provider spending caps in addition to worker call/time controls.
- Orchestrator receives at most P4 advice; no permission escalation.

## Verification status

Current CI: synthetic upstream-format mirror and CLI/ACE regression tests. Actual operator CASE_LIBRARY, WorkBuddy session, publication impact and improvement over case retrieval have **not** been tested.
