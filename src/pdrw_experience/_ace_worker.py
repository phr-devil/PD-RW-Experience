"""Isolated ACE process. Called only by the signed-grant parent bridge.

Max model calls are counted at the pinned ACE timed_llm_call entrypoints;
the parent enforces a subprocess wall timeout. Provider API retries or dollar
costs are NOT bounded by this counter: trusted provider limits remain required.
"""
from __future__ import annotations

import importlib
import json
import sys


class CallBudget:
    def __init__(self, limit: int):
        if type(limit) is not int or not 1 <= limit <= 30:
            raise ValueError("ACE model call limit invalid")
        self.limit = limit
        self.used = 0

    def guard(self, fn):
        def counted(*args, **kwargs):
            if self.used >= self.limit:
                raise RuntimeError("ACE_MODEL_CALL_CAP_REACHED")
            self.used += 1
            return fn(*args, **kwargs)
        return counted


def main():
    args = json.load(sys.stdin)
    root = args["root"]
    if root not in sys.path:
        sys.path.insert(0, root)
    ace = importlib.import_module("ace")
    if not str(ace.__file__).startswith(root + "/") and not str(ace.__file__).startswith(root + "\\"):
        raise RuntimeError("ACE_IMPORT_OUTSIDE_PINNED_CHECKOUT")

    limiter = CallBudget(args["max_model_calls"])
    for module_name in ("ace.core.generator", "ace.core.reflector", "ace.core.curator"):
        module = importlib.import_module(module_name)
        fn = getattr(module, "timed_llm_call", None)
        if fn is None:
            raise RuntimeError(f"ACE_UPSTREAM_CALL_INTERFACE_CHANGED:{module_name}")
        module.timed_llm_call = limiter.guard(fn)

    from .ace_bridge import ScientificDataProcessor
    engine = ace.ACE(
        api_provider=args["provider"], generator_model=args["model"],
        reflector_model=args["model"], curator_model=args["model"],
        max_tokens=2048, use_bulletpoint_analyzer=False)
    config = {
        "num_epochs": 1, "max_num_rounds": 1, "curator_frequency": 1,
        "eval_steps": 10, "save_steps": 10, "playbook_token_budget": 4000,
        "task_name": "pdrw_scientific_fact_extraction",
        "json_mode": False, "no_ground_truth": False,
        "save_dir": args["save_dir"], "test_workers": 1,
        "use_bulletpoint_analyzer": False, "api_provider": args["provider"],
    }
    engine.run(
        mode="offline", train_samples=args["train"],
        val_samples=args["val"], test_samples=[],
        data_processor=ScientificDataProcessor(), config=config)
    print("PDRW_ACE_RESULT_JSON=" + json.dumps({
        "status": "ACE_RETURNED_CANDIDATE_ONLY",
        "model_calls": limiter.used, "save_dir": args["save_dir"],
        "scientific_validity_verified": False,
        "budget_scope": "PINNED_TIMED_LLM_CALL_ENTRYPOINTS_ONLY"
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
