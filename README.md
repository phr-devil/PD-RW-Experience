# PD-RW-Experience

**v0.2.0a1 — first read-only Case Mirror integration; scientific benefit NOT_MEASURED.** An evidence-grounded adapter for structured research cases, opt-in ACE factual learning, independently reviewed Lessons and P4 guidance. Not an LLM, a paper-writing agent or a second scientific policy authority.

## Authority and scope

- PD-RW: source of binding research rules, author decisions, approval gates.
- Original projects and CASE_LIBRARY: scientific evidence and immutable Runs; remain outside this repository.
- PD-RW-Agent v1.0 RC: exports and verifies case-knowledge mirrors; Experience reads an approved local snapshot but does not reimplement the case library.
- Experience: read-only mirror contract verification, explicit source/annotation mapping, ACE bridge and candidate lesson review, stateless P4 advice.
- Orchestrator: selects tasks and Agents; no live provider integration is claimed for this stage.

## Quick start (Python 3.11+)

~~~bash
python -m pip install -e ".[dev]"
python -m pytest -q
pdrw-exp case-check examples/case.synthetic.json
pdrw-exp ace-preflight examples/ace-cases.synthetic.jsonl --as-of 2026-04-01
pdrw-exp feedback-check examples/feedback.synthetic.json
~~~

**New in v0.2:** after exporting an authorized Case Knowledge Mirror using the existing `pdrw-agent case-knowledge-build` and `case-knowledge-verify` CLI:

~~~bash
pdrw-exp mirror-inspect /private/case-mirror
pdrw-exp mirror-import /private/case-mirror --annotations /private/annotations.json --out-dir /private/exp-import-001 --dry-run
pdrw-exp mirror-import /private/case-mirror --annotations /private/annotations.json --out-dir /private/exp-import-001
~~~

The import writes only to a **new, explicitly chosen private local output directory**; it never touches the original library or mirror and never performs model calls. Missing evidence, classification, method, source grouping or split consistency blocks conversion. Imported source hashes verify **mirror Markdown cards**, not original experiment/PDF bytes. `snapshot_as_of` is a conservative snapshot time, never a claim that all these records existed historically.

Full format, Windows setup and field mapping: [Case Mirror integration](docs/CASE_MIRROR_INTEGRATION.md).

## Existing Lesson / ACE capabilities

- `lesson-review`: declared source matching, or independently signed Ed25519 reviewer receipt + actual referenced source byte checks. Signature does not establish scientific correctness.
- `retrieve`: requires host-pinned review trust and original referenced bytes; exports only P4 guidance compatible with the Orchestrator Guidance v1 contract.
- `ace-preflight`: objective `NORMALIZED_FACT` extraction only; independently reviewed targets and visible public sources required for live calls. No free-form scientific conclusion is scored by literal answer match.
- `ace-run`: explicit approved run grant, pinned clean upstream ACE commit, worker call/wall limits, and host/provider costs controls.

**Still NOT_DONE:** real CASE_LIBRARY import on the operator's machine, primary science source attestations, PDF parsing, actual ACE scientific strategy distillation, raw Playbook → cited Lessons, full Orchestrator real integration, and measured gain over direct-case retrieval.

This is a **public** code repository: do not commit private cases, mirror contents, unpublished papers, results, provider keys, run receipts, or credentials. Keep runtime outputs outside public Git checkouts.

[Case Mirror](docs/CASE_MIRROR_INTEGRATION.md) · [Architecture](docs/ARCHITECTURE.md) · [ACE](docs/ACE_INTEGRATION.md) · [Review trust](docs/TRUST_AND_REVIEW.md) · [Orchestrator contract](docs/ORCHESTRATOR_CONTRACT.md) · [Roadmap](docs/ROADMAP.md).
