# ACE integration: explicit, external, and bounded

## Why ACE

Use the official Agentic Context Engineering Generator/Reflector/Curator Playbook loop instead of reimplementing it. Source: https://github.com/ace-agent/ace (Apache-2.0 LICENSE.txt).
Reviewed baseline commit: 82709de050e1db6e6ef2f07bcb0393560b94992a.

Alternative comparison designs: ExpeL and ReasoningBank. LangMem is a future alternative for memory extraction and retrieval; v0.1 installs none of them.

## Offline preparation

Python >= 3.11; install this package alone and run:
- pdrw-exp ace-preflight examples/ace-cases.synthetic.jsonl
- Expected: two supervised public cases, distinct TRAIN/VAL case_group, zero model calls.
- Any missing reviewed_target, private source, or mixed TRAIN/VAL group blocks preparation.
- No TEST examples are included. Keep future evaluation cases in a separate, frozen study.

A reviewed_target is an externally created (question, answer, review_ref) record. The reference target is for **evaluation of extraction**, not a universal truth about scientific merit. An LLM-generated self-label cannot be silently treated as human ground truth.

## Optional live run

1. Clone official ACE into an isolated environment; checkout exactly the pinned commit. Follow official setup (uv, API credentials, dependencies).
2. Install this package in the same isolated Python environment and verify import ace resolves inside that checkout.
3. Use ONLY independently approved PUBLIC case metadata with reviewed targets, and prepare a private local --save-dir (outside repository).
4. Set environment variable PDRW_EXPERIENCE_ALLOW_MODEL_CALLS=YES; pass --execute explicitly.
5. Example, after provider-level spending limits are configured:
   pdrw-exp ace-run /path/to/public-reviewed.jsonl --ace-root /path/to/ace --provider openai --model YOUR_SUPPORTED_MODEL --save-dir /private/ace-results --execute
6. This invokes the upstream ACE.offline run with 1 epoch, 1 reflection round, test_workers=1 and 2048 max tokens per call. **These are configuration limits, NOT an enforced total API call or budget cap.** Provider limits, monitoring and cancellation are required for paid calls.
7. Raw ACE playbook and generated answers are not scientifically validated. Inspect, extract candidate lessons, link source hashes and perform independent review before marking REVIEWED.

Current limitation: no automated converter from raw ACE playbook bullets into trusted Lesson records. This is intentional: source and reasoning attribution must not be invented. First integration milestone is a reviewable candidate exporter, not automatic promotion.

ACE compatibility is based on its inspected upstream source interface, not on a successful live model experiment. Do not claim a passing live run until independently observed.
