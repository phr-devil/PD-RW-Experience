# Architecture and authority

## Owned components

1. Case Adapter: structured records from source-referenced paper/project evidence; v0.1 requires JSON/JSONL already prepared by an approved document/CASE_LIBRARY reader.
2. ACE Bridge: strict offline supervised-data preflight, pinned external ACE checkout, opt-in run. ACE implements Generator, Reflector and Curator; this repo does not copy that code.
3. Evidence Review: deterministic references/dates/classification/condition checks, **not** scientific fact verification.
4. Experience Library: structured Lesson records, conflict states and search; v0.1 provides stateless file-based read-only retrieval, not an independent CASE_LIBRARY.
5. Interfaces: Python library and CLI, output compatible with Orchestrator Guidance v1, level=experience only.

## Authorities and lineage

- PD-RW is the authoritative policy/H decisions and authorization provenance.
- Research project files and original Runs are authoritative factual observations, subject to real validation.
- PD-RW-Agent 1.0 RC (pinned review commit 9177b6eb822aaa0d1482ef40f54369a8612c42dd) has existing science/context operations. This project does not re-implement or assert that it verifies scientific truth.
- Experience is P4 advisory only. Its reviewed status means only a **declared** review artifact, not cryptographically authenticated approval. No automatic new permissions, science verdict, rule promotion or STOP.
- Orchestrator consumes Guidance schema with id, level, source, text, task_types, evidence_refs, conditions. It retains decision and execution control.

## Defensive data flow

Structured input → case-check → ACE preflight (train/val only) → explicitly consented ACE external learning → raw ACE playbook stays CANDIDATE → human/independent evidence review → structured lesson-review → P4 retrieval → feedback-check (no auto-update).

Source hashes are declared pointers checked for equality. Without original bytes or read-only PD-RW-Agent evidence service, this cannot attest hashes against disk. Stored references never imply an original file was independently accessed.

## Privacy and leakage

- Repository is PUBLIC; use synthetic examples only. Private cases and SEALED must stay outside this repo.
- Private classification or private source visibility blocks ACE; TEST split is excluded from ACE data preparation and all retrieval.
- Retrievable lessons must be REVIEWED-declared with review_ref, source-matched, PUBLIC, originating from TRAIN and visible by as_of. Missing cases/conflicts cause exclusion.
- The external ACE implementation may call third-party APIs and write detailed logs; provide only explicitly approved public metadata, pin code and enforce budgets outside.
- Never rely on a model to self-certify scientific novelty, citation validity or Run integrity.

## Roadmap and limitations

The current MVP does not parse PDFs, attest original source bytes, authenticate review signoff or run a live model. Full integration with PD-RW-Agent is intentionally pending adapter/permission testing. For blinded research evaluation, freeze the lesson index and as-of cutoff before TEST is observed.
