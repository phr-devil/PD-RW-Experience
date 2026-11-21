# Orchestrator bridge — Guidance v1 / P4 only

Source consumer: https://github.com/phr-devil/PD-RW-Orchestrator/blob/main/schemas/guidance.schema.json

## Scope

This repository supplies structured experience guidance only. A P4 experience suggestion is not evidence of scientific truth, a permission grant, a new rule, or a next-stage command.

Supported read-only request is the equivalent of:

- task_type: experimental_design or another Orchestrator task type (literal string; e.g. experiment_design)
- query: research context keywords / short scientific problem statement
- as_of: ISO date for time-visible cases and lessons
- limit: maximum number of suggestions
- case catalog + lesson catalog: immutable, locally authorized JSON/JSONL inputs (no hidden filesystem scan)

Command:

    pdrw-exp retrieve examples/lesson.synthetic.json --cases examples/case.synthetic.json --task-type experiment_design --query leakage --as-of 2026-04-01 --limit 3

Response shape is an array of Guidance v1 objects:
- id: lesson id and version
- level: always experience
- source: PD-RW-Experience declared review pointer (not authenticated by this adapter)
- text: lesson claim
- task_types: registered scopes
- evidence_refs: case/source pointers
- conditions: when the lesson may apply

Unknown, future-dated, conflicting, private, non-TRAIN or unresolved references are suppressed. Only declared REVIEWED lessons can be returned and their declared review is **not** independently authenticated; downstream consumers must keep them P4, and may run additional PD-RW-Agent checks.

## Feedback direction

    pdrw-exp feedback-check /private/feedback.json

Feedback is received as UNVERIFIED with no automatic mutation. Future integration can validate it against source Run hashes, attach original authorization evidence and then propose a new lesson version. Experience must never auto-modify PD-RW.

## Source compatibility

- Current Orchestrator schema is version 1.0, relative to main as inspected on 2026-11-21.
- Current PD-RW-Agent reference is RC v1.0.0rc1 commit 9177b6eb822aaa0d1482ef40f54369a8612c42dd.
- Schema changes should be checked against both repositories, but this repo does not write to them.

This bridge does not run ARC, AIDE, R&D-Agent, or WorkBuddy and has no authority to launch experiments.
