# ACE external engine: supervised factual preflight and explicit paid execution

Pinned upstream `https://github.com/ace-agent/ace` commit `82709de050e1db6e6ef2f07bcb0393560b94992a` (Apache-2.0). Do not vendor source or use an unpinned working tree.

## Safe preparation

~~~bash
pdrw-exp ace-preflight examples/ace-cases.synthetic.jsonl --as-of 2026-04-01
~~~

Expected status: `READY_FOR_LOCAL_DRY_RUN_ONLY`, with model_calls=0. This only checks public, typed, date-bounded synthetic data. It does **not** authorize model requests.

Actual supervised ACE preparation requires case-level `reviewed_target` with `evaluation_type=NORMALIZED_FACT`, `reviewed_at`, reference answer, explicit accepted answers and a review reference. Every target must have a matching external `TARGET_REVIEW` Ed25519 receipt and the source bytes must be hashed under the trusted host root. A typed objective score avoids turning scientifically equivalent free-form answers into false training mistakes.

Example with authorized local evidence:

~~~bash
pdrw-exp ace-preflight /private/approved_cases.jsonl --as-of 2026-11-21 --receipts /trusted/target-receipts.json --trusted-public-key /trusted/reviewer.pub.pem --source-root /trusted/sources --source-index /trusted/source-index.json
~~~

Result `READY_FOR_EXPLICIT_ACE_RUN` means **the declared factual-target task is eligible**, not that the lesson is scientifically true or a paper is publishable.

## Live ACE interface (NOT_RUN)

The caller must also supply:
1. A clean checkout of the pinned ACE SHA, in an isolated Python environment with official dependencies installed.
2. A separate, valid `ACE_RUN_GRANT` Ed25519 signed receipt for the exact `job` payload assembled in `run_ace_offline`. No signer is bundled.
3. Explicit `--execute` and `PDRW_EXPERIENCE_ALLOW_MODEL_CALLS=YES`.
4. Host-enforced credentials/allowlist and **provider-side budget/spending caps**. The worker's `--max-model-calls` guards only upstream `timed_llm_call` entrypoints, not retries buried inside the provider SDK; the subprocess `--max-wall-seconds` kills overlong jobs but cannot retroactively undo charges.
5. An output directory outside the GitHub checkouts with restricted permissions.

~~~bash
pdrw-exp ace-run /private/approved_cases.jsonl --as-of 2026-11-21 --ace-root /isolated/ace --provider openai --model YOUR_APPROVED_MODEL --save-dir /private/ace-outputs --receipts /trusted/target-receipts.json --trusted-public-key /trusted/reviewer.pub.pem --source-root /trusted/sources --source-index /trusted/source-index.json --execution-grant /trusted/run-grant.json --max-model-calls 10 --max-wall-seconds 120 --execute
~~~

The supervised task trains ACE to answer annotated factual questions; it **does not yet prove** transferable scientific experience distillation. Raw ACE playbook must remain CANDIDATE until it is converted into sourced Lessons and independently reviewed.

LangMem remains optional; ExpeL and ReasoningBank are methodological comparison choices. No model fine-tuning is required by this repo.
