# PD-RW-Agent Case Knowledge Mirror -> Experience (v0.2.0a1)

## Scope

This is a local, read-only, **contract-verified** adapter for the Knowledge Mirror emitted by PD-RW-Agent `rc/v1.0-integration` (inspected commit `9177b6eb822aaa0d1482ef40f54369a8612c42dd`, mirror version 1.2). It does not directly scan or write CASE_LIBRARY. GitHub sources are code only, not the runtime data store.

**Status:** synthetic mirror contract/CLI tests only; no actual operator CASE_LIBRARY has been inspected or imported by this project, and no ACE run was performed.

## 1. Export an approved subset with existing PD-RW-Agent

Install/configure PD-RW-Agent following its RC instructions, including `PDRW_CASE_LIBRARY_ROOT`, `PDRW_AGENT_CONFIG`, and `PDRW_WORKFLOW_ROOT`. Place all runtime data *outside public Git repositories*. Use selected real Case IDs in a private JSON file, e.g. `case-scope.json`:

~~~json
{"case_ids":["YOUR_EXISTING_CASE_ID_A","YOUR_EXISTING_CASE_ID_B"]}
~~~

Example Windows PowerShell (paths are placeholders; replace with actual private paths):

~~~powershell
pdrw-agent case-knowledge-build --out "D:\\PD-RW-runtime\\case-mirror" --scope-file "D:\\PD-RW-runtime\\case-scope.json"
pdrw-agent case-knowledge-verify --dir "D:\\PD-RW-runtime\\case-mirror"
~~~

Require upstream verification `status=MIRROR_VERIFIED` before proceeding. If upstream returns `MIRROR_PROBLEMS`, investigate rather than coercing status. A mirror may be internally valid but marked `publishable=false`; this does not grant external data transfer, and this adapter forbids converting those cases to PUBLIC.

## 2. Inspect the mirror without changing source data

~~~powershell
pdrw-exp mirror-inspect "D:\\PD-RW-runtime\\case-mirror"
~~~

This validates all manifest-listed files against SHA-256 and byte counts, the `content_sha256`, the compact `indexes/cases.jsonl` index and each Markdown card's `---json` frontmatter. It checks card IDs, source grouping and index/card cross-fields. It reports counts only, not private content.

**Trust boundary:** manifest integrity proves internal consistency, not that a malicious party couldn't rewrite both manifest and files. Use upstream live-library verification and an approved trusted host for original records.

## 3. Add explicit per-case annotations

Create a private `case-annotations.json`, following `examples/mirror-annotations.template.json`. The required properties are:

- `snapshot_as_of`: conservative date for this snapshot; **not** the original publication or experiment date.
- `cases[CASE_ID].split`: TRAIN, VAL, or TEST; all cases with the same `source_group_id` must be assigned the same split.
- `cases[CASE_ID].classification`: PRIVATE by default in research use. PUBLIC requires explicit operator approval and a publishable mirror; neither guarantees permission for external model calls.
- `cases[CASE_ID].case_type`: success/failure/paper/mixed (explicit annotation; never guessed from the paper title).
- `cases[CASE_ID].method` AND `method_source_ref`: user-provided faithful method summary and source reference. Missing method information blocks import.
- If mirror `research_problem_basis` is TITLE rather than DECLARED, additionally provide an explicit `research_question` annotation; do not present title-derived text as a verified research question.
- Source-reported results and stated limitations must be present; missing data blocks import.

No `reviewed_target` is generated. This tool never asserts the scientific result was independently verified.

## 4. Import only to a new private local directory

~~~powershell
pdrw-exp mirror-import "D:\\PD-RW-runtime\\case-mirror" --annotations "D:\\PD-RW-runtime\\case-annotations.json" --out-dir "D:\\PD-RW-runtime\\exp-import-001" --dry-run

pdrw-exp mirror-import "D:\\PD-RW-runtime\\case-mirror" --annotations "D:\\PD-RW-runtime\\case-annotations.json" --out-dir "D:\\PD-RW-runtime\\exp-import-001"
~~~

A successful run creates:
- `cases.jsonl`: validated ScientificCase records;
- `source-index.json`: local **mirror-card** source paths, for verifying this snapshot's card bytes later;
- `report.json`: converted/blocked counts, mirror digest and explicit `original_evidence_verified=false`.

The output directory must be new and outside the mirror. The original CASE_LIBRARY and mirror are never modified. A blocked input creates no files. Do not commit the private output to this public repository.

## Distinguishing source layers

The imported `source_refs` point to `mirror-card:<CASE_ID>` with its verified Markdown SHA-256. The separate optional `mirror_provenance` field retains original bibliographic references, original case-card SHA-256 as reported, evidence grade and original source reference strings. **These are not independently verified primary Run/PDF bytes.** A future PD-RW-Agent evidence adapter must check them before any scientific-source attestation.

`available_at` is set conservatively to `snapshot_as_of`; no earlier historical availability is inferred from `updated_at`. For as-of evaluation before this snapshot, obtain legitimately frozen contemporaneous evidence instead of backdating the mirror.

## ACE and Orchestrator integration state

Import does not grant any model-call permission. PRIVATE case records are blocked by ACE's current public-data gate. PUBLIC data still need independently reviewed factual targets, signed receipts and actual source-byte checks before ACE calls. `NORMALIZED_FACT` is not an open-ended scientific-strategy quality judge.

Orchestrator's `accept_advisories()` already accepts validated P4 guidance, but the live Experience provider is not integrated yet. Do not claim a scientific benefit until frozen A/B/C comparisons on unseen cases.
