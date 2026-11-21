# PD-RW-Orchestrator Guidance v1 consumer contract

PD-RW-Experience exports **only** `level=experience` P4 advisory fields compatible with `https://github.com/phr-devil/PD-RW-Orchestrator/blob/main/schemas/guidance.schema.json`:

`id`, `level`, `source`, `text`, `task_types`, `evidence_refs`, `conditions`.

Orchestrator does not gain permission, scientific fact or a binding policy by consuming these fields. Its Experience adapter currently validates provider messages only; a real live integration has not been verified.

## Read-only request

Provide host-authenticated reviewer trust key, signed receipt catalog and source index in addition to lesson/case material:

~~~bash
pdrw-exp retrieve /private/lessons.json --cases /private/cases.json --task-type experiment_design --query leakage --as-of 2026-11-21 --limit 3 --receipts /trusted/lesson-receipts.json --trusted-public-key /trusted/reviewer.pub.pem --source-root /trusted/sources --source-index /trusted/source-index.json
~~~

Only currently visible, public, nonconflicting, signed, source-byte-matched, TRAIN-derived Lessons are exportable. The signature and byte check do not prove scientific correctness. The `conditions` field is a task-side applicability hypothesis, not a verified match.

## Feedback

`pdrw-exp feedback-check /private/feedback.json` returns `RECEIVED_UNVERIFIED`. It never mutates the Playbook or upgrades a rule.

Do not allow an untrusted Agent to select or replace the trusted reviewer key or the root of original evidence. The trusted host owns identity and all side effects. No cross-repository code changes are part of this contract.
