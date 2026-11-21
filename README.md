# PD-RW-Experience

**Status: v0.1 foundation (offline-first; no measured research gain).** An evidence-grounded adapter for distilling scientific cases into *candidate* research lessons. ACE is the preferred external learning engine; this repository does **not** implement a competing LLM, training loop, or a second scientific authority.

## Scope and authority

- **PD-RW**: authoritative scientific rules and author decisions.
- **Original projects and CASE_LIBRARY**: source evidence, protocols, immutable Runs. Read-only; not mirrored here.
- **PD-RW-Agent v1.0 RC**: existing case retrieval, applicability, evidence reviews, and project recovery. Reuse rather than reimplement.
- **PD-RW-Experience**: case contracts, supervised ACE task preparation, provenance checks, conditional lesson retrieval, experience feedback exchange.
- **PD-RW-Orchestrator**: task and agent selection; experience remains P4 advisory, never permission or a scientific verdict.

**Boundary:** schema checks prove only structure and declared references; they do not certify a paper's claims, a Run's validity, or author's authorization. Do not auto-promote lessons into PD-RW hard rules.

## Quick start (Python 3.11+)

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
pdrw-exp case-check examples/case.synthetic.json
pdrw-exp lesson-review examples/lesson.synthetic.json --cases examples/case.synthetic.json
pdrw-exp ace-preflight examples/ace-cases.synthetic.jsonl
pdrw-exp retrieve examples/lesson.synthetic.json --cases examples/case.synthetic.json --task-type experiment_design --query leakage --as-of 2026-04-01
```

Tests and examples are synthetic and do not require model API keys or access original research files. The ACE bridge is opt-in; see [ACE integration](docs/ACE_INTEGRATION.md). No external model call occurs in ordinary commands.

## Design

`case-check` → `ace-preflight` → **external ACE Generator/Reflector/Curator** → `lesson-review` → `retrieve` → `feedback-check`.

Paper text is **not** automatically extracted from arbitrary PDFs in v0.1: structured case records are the supported input. The ACE adapter expects independently reviewed task targets before paid model calls, otherwise returns a blocked preflight. Raw ACE playbook bullets are **candidate suggestions**, not reviewed lessons.

## Public-repository data rules

This repository is **public**. Do not commit unpublished papers, private case libraries, research transcripts, full Runs, credentials, SEALED/VAL, or personal data. `examples/` are synthetic only. Keep runtime outputs and sensitive material outside the repository. Never send private material to a third-party model without explicit permission and an approved boundary.

## Status

- Implemented: deterministic structural case/lesson checks, read-only retrieval to Orchestrator P4 guidance, ACE supervised-data preflight and opt-in adapter, tests.
- Not claimed: automatic scientific verification, PDF extraction, production CASE_LIBRARY connector, live ACE model runs, transfer-quality gain, agent-to-agent deployment.
- Next: independently verified case/lesson datasets; read-only PD-RW-Agent bridge; bounded ACE comparison; blinded `baseline / RAG / distilled` eval.

[Architecture](docs/ARCHITECTURE.md) · [ACE bridge](docs/ACE_INTEGRATION.md) · [Roadmap](docs/ROADMAP.md) · [Other system](https://github.com/phr-devil/PD-RW-Orchestrator)
