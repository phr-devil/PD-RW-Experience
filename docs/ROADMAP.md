# Evidence-first development roadmap

## M0.1.1 — P0 scientific/operational safeguards (code and synthetic CI)

- [x] Deterministic, explicitly typed normalized fact labels; no unreviewed free-form scientific grader.
- [x] Detached signed Lesson review and actual original source hashing before P4 export.
- [x] Split isolation (case group, exact source digest, duplicate IDs, TEST blocked), as-of source and target reviews.
- [x] ACE external subprocess boundary, declared model-call and wall-time limits, clean pinned upstream, signed run-grant and explicit dual opt-in.
- [x] Synthetic signature tampering, source modification, split leakage, model-call cap and CLI regression tests.
- [ ] Real ACE paid experiment: NOT_RUN; provider-side spend and network controls are external requirements.
- [ ] Production reviewer identity, source connector and science review: NOT_IMPLEMENTED.

## M1 — real read-only source bridge

Use PD-RW-Agent rc/v1.0-integration to retrieve CASE_LIBRARY and source/Run provenance. No second original data store. Explicit authorization and a host-pinned reviewer trust key required. Add a PDF/paper adapter through mature parsers, preserving DOI, source spans, licensing and author-vs-evidence distinctions.

## M2 — actual experience distillation

Run ACE on approved, independently labeled cases. Convert raw playbook bullets into source-cited CANDIDATE Lessons and independently review mechanisms, scope and counterexamples. Compare ExpeL/ReasoningBank where helpful. Keep an objective extraction evaluation separate from transfer-quality assessment.

## M3 — real integration and scientific gain

Orchestrator requests signed P4 guidance and sends separately verified feedback. Paired frozen tests compare BASELINE / case RAG / ACE lessons at comparable model, compute and Token budget. Report false transfer, real scientific errors, evidence quality and cost. No auto-PD-RW rule promotion.

All performance improvements are NOT_MEASURED until real evaluation. Synthetic CI is not scientific validation.
