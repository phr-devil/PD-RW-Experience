# PD-RW-Experience

**Status: v0.1.1 engineering prototype; scientific benefit NOT_MEASURED.** Evidence-grounded research experience preparation, reviewed lesson retrieval and opt-in ACE adaptation. **Not an LLM, a publication pipeline or a second scientific authority.**

## Responsibilities

- **PD-RW:** scientific rules, author decisions, hard boundaries.
- **Original research projects and CASE_LIBRARY:** original evidence and immutable Runs; not copied into this repository.
- **PD-RW-Agent v1.0 RC:** existing case, applicability, source/Run and scientific review services. Reuse via a future read-only adapter; no claims of a completed integration.
- **PD-RW-Experience:** case/lesson contracts, supervised ACE fact-task preparation, signed review receipt and real source-hash checks, P4 advisory export, unverified feedback.
- **PD-RW-Orchestrator:** selects and hands off tasks; experience suggestions remain P4 untrusted advice, never grants or scientific verdicts.

## Quick start (Python 3.11+)

~~~bash
python -m pip install -e ".[dev]"
python -m pytest -q
pdrw-exp case-check examples/case.synthetic.json
pdrw-exp lesson-review examples/lesson.synthetic.json --cases examples/case.synthetic.json
pdrw-exp ace-preflight examples/ace-cases.synthetic.jsonl --as-of 2026-04-01
pdrw-exp feedback-check examples/feedback.synthetic.json
~~~

These are **synthetic, no-model-call demonstrations**. A successful unsigned `lesson-review` shows `DECLARED_LINEAGE_MATCHED_ONLY`; ACE preflight without approved target receipts returns `READY_FOR_LOCAL_DRY_RUN_ONLY`, not proof of a runnable approved study.

### Signed lesson retrieval

**Do not treat `status=REVIEWED` or a file's self-declared SHA-256 as certification.** To export P4 guidance, supply all of:

- A detached Ed25519 review receipt signed outside this repository by an authorized reviewer.
- The corresponding **trusted reviewer public key, supplied by the operator/host**, never by the untrusted case.
- An approved read-only source root and trusted source-index mapping. The original bytes are SHA-256 checked at retrieval.
- An explicit `--as-of` cutoff. Only PUBLIC, TRAIN, visible, unconflicted, signed/source-verified experience can be exported.

~~~bash
pdrw-exp retrieve /private/lessons.json --cases /private/cases.json --task-type experiment_design --query leakage --as-of 2026-04-01 --receipts /trusted/lesson-receipts.json --trusted-public-key /trusted/reviewer.pub.pem --source-root /trusted/sources --source-index /trusted/source-index.json
~~~

**Trust configuration is part of the authenticated host boundary**; giving an untrusted agent the freedom to nominate a new public key does not establish a credible review identity. A signed receipt attests signer approval and the bound record, **not scientific truth or correctness**. See [trust contract](docs/TRUST_AND_REVIEW.md).

## ACE integration

Core implementation is the pinned upstream [ACE](https://github.com/ace-agent/ace) (Apache-2.0), not vendored. Compare ExpeL and ReasoningBank as methods, LangMem only if integration demands it.

- This version limits supervised ACE samples to explicitly annotated `NORMALIZED_FACT` extraction and independently signed reference targets. Synonyms must be enumerated in `accepted_answers`; open-ended novelty assessment is NOT graded with string equality.
- One source/case group cannot cross TRAIN, VAL or TEST. TEST supplied to adaptation input blocks the run. Dates and target-review visibility are checked.
- Live runs require signed target receipts, original source bytes, a separate signed run grant, explicit `--execute` and `PDRW_EXPERIENCE_ALLOW_MODEL_CALLS=YES`. The isolated worker is bounded to declared calls and wall time and requires a clean pinned ACE checkout. **Provider-side dollar limits/egress approval remain mandatory; caller-side call count is not a hard cost guarantee.**
- No real ACE run is claimed. See [ACE integration](docs/ACE_INTEGRATION.md).

## Limitations and status

- Completed: versioned Case/Lesson/Feedback schemas, fail-closed signed review/source-byte export, ACE factual target gating, cross-split and visibility tests, a budgeted external worker interface, synthetic CI.
- **Not completed:** PDF-to-case pipeline, live CASE_LIBRARY connector, independent scientific methodology judgment, raw ACE playbook-to-evidenced-Lesson conversion, real paid-model ACE validation, Orchestrator integration test or demonstrated increase in research quality.
- This repository is **public**. Never commit unpublished papers, private CASE_LIBRARY contents, full Runs, personal data, passwords, API tokens or provider logs. Keep private inputs and outputs outside the checkout.

[Architecture](docs/ARCHITECTURE.md) · [Review trust](docs/TRUST_AND_REVIEW.md) · [ACE](docs/ACE_INTEGRATION.md) · [Orchestrator](docs/ORCHESTRATOR_CONTRACT.md) · [Roadmap](docs/ROADMAP.md).
