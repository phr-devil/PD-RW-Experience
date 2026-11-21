# Development roadmap — verify capabilities before expanding

## M0: repo foundation (this increment)

- Structured Case/Lesson/Feedback schemas and CLI.
- SOURCE MATCH and time-as-of checks, classification, TRAIN/VAL/TEST isolation.
- ACE preflight and explicit optional bridge; no API calls during normal operation.
- Synthetic tests and GitHub CI, public-data hygiene.
- Deliver status as ENGINEERING_ONLY, not science validated.

## M1: read-only source bridge

- Connect through pinned PD-RW-Agent RC CLI/MCP for official CASE_LIBRARY records; no second original-data database.
- Verify source bytes/hash where permitted, scope review signatures, and fail closed when unavailable.
- Add PDF/paper adapter using approved parser; capture DOI, title, claim/limitations, citation spans, copyright constraints.

## M2: candidate learning

- ACE run on independently annotated public benchmark samples.
- Parse raw ACE outputs into candidate lessons with citation support; conflicts, generality, and provenance reviewed by independent human/authorized host.
- Compare with ExpeL/ReasoningBank methods if ACE cannot meet benchmarks; LangMem only if needed.
- No blanket generalization from one failed project.

## M3: integration and effectiveness

- Versioned Experience Query/Feedback contract with PD-RW-Orchestrator.
- Evaluate frozen baseline vs raw-case retrieval vs distilled lessons at matched model/time/compute budget.
- Report valid findings, false positives, overgeneralization, token cost, failure rate; negative findings stay visible.
- Never promote to PD-RW rules automatically.

## Acceptance evidence

M0: install, tests pass, examples operate with zero model calls. M1–M3 remain NOT_RUN until independently measured. The success metric is improved correct scientific decisions per total cost, not number of lessons.
