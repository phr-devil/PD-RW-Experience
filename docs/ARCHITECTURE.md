# Architecture — fail-closed evidence-grounded experience

1. **Case Adapter:** accepts host-prepared structured records and source pointers. PDF parsing and CASE_LIBRARY integration are not yet implemented.
2. **ACE Bridge:** data preflight creates only objectively annotated `NORMALIZED_FACT` tasks. The official ACE Generator/Reflector/Curator handles the learning loop; this repo does not replicate it.
3. **Source & Review Trust:** optional declared lineage inspection versus mandatory detached Ed25519 receipt + original source-byte SHA-256 verification for export and real model calls. Signature is **not** scientific verification.
4. **Experience Library:** stateless JSON/JSONL read-only lesson retrieval, bounded search, case visibility and signed evidence matching. Not a second original CASE_LIBRARY.
5. **Orchestrator contract:** Guidance v1 `level=experience` P4 only. Decision, experimental authorization and PD-RW hard rules remain elsewhere.
6. **Feedback:** unverified receipt only; no automatic confidence inflation, source modification or rule promotion.

## Defense in depth

- **Identity and authority:** original PD-RW/author records, host-granted filesystem/network permissions, trusted reviewer public key outside the inputs.
- **Evidence:** hash actual files under an explicit trusted root; a declared review is insufficient.
- **Learning:** protect TRAIN/VAL/TEST by case group and exact source digest, block TEST from adaptation, require `as_of` for source and review availability. Near-duplicate semantic case leakage still requires a separate audit.
- **Paid calls:** dual opt-in + signed run grant + pinned clean ACE commit; ACE in a killable subprocess with wall time and counted `timed_llm_call` invocations. This does not enforce provider retries, actual dollars or a full network sandbox; the trusted host must enforce those.
- **Evaluation:** objective fact labels are normalized and may list preapproved variants; a freeform scientific strategy or novelty statement is NOT automatically graded.
- **Advice:** signed, source-byte-matched REVIEWED cases can supply P4 guidance, but `scientific_validity_verified=false` remains true even after receipt verification.

## Scientific policy source

PD-RW-Agent rc/v1.0-integration at inspected commit `9177b6eb822aaa0d1482ef40f54369a8612c42dd`. The reader should treat this as reference lineage, not evidence of a locally installed version. Do not duplicate the science ledger.

## Current engineering scope

Unit/CLI tests are synthetic. Real source access, independent scientific adjudication, a production identity-aware key store, live ACE run and Orchestrator real handoff remain pending verification.
