"""Opt-in external ACE bridge. No ACE code or credentials are vendored here.

Supervised targets require an independently reviewed reference answer; this is
*not* a general scientific truth oracle. Model calls run only after explicit
dual opt-in, and are restricted to PUBLIC training/validation case metadata.
"""
from __future__ import annotations

import importlib
import os
from pathlib import Path
import subprocess

from .core import RecordError, validate_case

ACE_BASELINE_COMMIT = "82709de050e1db6e6ef2f07bcb0393560b94992a"


def _normalize_answer(text: str) -> str:
    """Only normalization, not an LLM judgment of scientific equivalence."""
    import unicodedata
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def prepare_ace_samples(
    cases: list[dict], *, as_of: str,
    target_receipts: dict | None = None,
    trusted_public_key: bytes | None = None,
) -> dict:
    """ACE data preparation: future- and group-isolated, fact labels only."""
    import json
    from .core import _date
    from .trust import digest, verify_receipt

    _date(as_of, "as_of")
    if (target_receipts is None) != (trusted_public_key is None):
        raise RecordError("TARGET_TRUST_CONFIG_INCOMPLETE")
    result = {"train": [], "val": [], "blocked": [],
              "engine": "ACE", "model_calls": 0,
              "review_attested": target_receipts is not None}
    seen_ids = set()
    groups = {}
    source_hashes = {}
    for case in cases:
        validate_case(case)
        cid = case["case_id"]
        if cid in seen_ids:
            raise RecordError("DUPLICATE_CASE_ID")
        seen_ids.add(cid)
        split = case["split"]
        group = case["case_group"].strip().casefold()
        if group in groups and groups[group] != split:
            raise RecordError(f"CASE_GROUP_LEAKAGE:{group}:{groups[group]}:{split}")
        groups[group] = split
        for source in case["source_refs"]:
            sha = source["sha256"].lower()
            if sha in source_hashes and source_hashes[sha] != split:
                raise RecordError(f"SOURCE_BYTES_LEAKAGE:{sha}")
            source_hashes[sha] = split
        if split == "TEST":
            result["blocked"].append({"case_id": cid, "reason": "TEST_IN_ADAPTATION_INPUT"})
            continue
        if (case["available_at"] > as_of or
                any(source["available_at"] > as_of for source in case["source_refs"])):
            result["blocked"].append({"case_id": cid, "reason": "FUTURE_SOURCE_OR_CASE"})
            continue
        if case["classification"] != "PUBLIC" or any(
            src["visibility"] != "PUBLIC" for src in case["source_refs"]
        ):
            result["blocked"].append({"case_id": cid, "reason": "NONPUBLIC_SOURCE"})
            continue
        target = case.get("reviewed_target")
        if target is None:
            result["blocked"].append({"case_id": cid, "reason": "NO_INDEPENDENT_REFERENCE_TARGET"})
            continue
        if target["reviewed_at"] > as_of:
            result["blocked"].append({"case_id": cid, "reason": "FUTURE_TARGET_REVIEW"})
            continue
        if target_receipts is not None:
            subject = {"case_id": cid, "case_sha256": digest(case),
                       "reviewed_target": target}
            try:
                verify_receipt(subject, target_receipts.get(cid),
                               kind="TARGET_REVIEW", trusted_public_key=trusted_public_key,
                               as_of=as_of)
            except (RecordError, TypeError) as exc:
                result["blocked"].append({"case_id": cid, "reason": f"TARGET_REVIEW_UNATTESTED:{exc}"})
                continue
        answer = json.dumps({"evaluation_type": "NORMALIZED_FACT",
                             "answer": target["answer"],
                             "accepted_answers": target.get("accepted_answers", [])},
                            ensure_ascii=False, sort_keys=True)
        result["train" if split == "TRAIN" else "val"].append({
            "context": (f"Case {cid}; type {case['case_type']}; research question: "
                        f"{case['research_question']}; method: {case['method']}; "
                        f"observed outcome: {case['observed_outcome']}; "
                        f"limitations: {'; '.join(case['limitations'])}. "
                        "Answer the reviewed factual extraction question, not general scientific merit."),
            "question": target["question"],
            "target": answer,
            "review_ref": target["review_ref"],
            "case_id": cid,
        })
    if result["blocked"] or not result["train"] or not result["val"]:
        result["status"] = "BLOCKED"
    elif target_receipts is None:
        result["status"] = "READY_FOR_LOCAL_DRY_RUN_ONLY"
    else:
        result["status"] = "READY_FOR_EXPLICIT_ACE_RUN"
    return result


class ScientificDataProcessor:
    """Only objectively annotated factual answers; not general science grading."""

    def process_task_data(self, rows):
        return rows

    def answer_is_correct(self, predicted, ground_truth):
        import json
        if not isinstance(predicted, str) or not isinstance(ground_truth, str):
            return False
        try:
            ref = json.loads(ground_truth)
        except (ValueError, TypeError):
            return False
        if not isinstance(ref, dict) or ref.get("evaluation_type") != "NORMALIZED_FACT":
            return False
        answers = [ref.get("answer"), *ref.get("accepted_answers", [])]
        return _normalize_answer(predicted) in {
            _normalize_answer(s) for s in answers if isinstance(s, str) and s.strip()
        }

    def evaluate_accuracy(self, predictions, ground_truths):
        if len(predictions) != len(ground_truths):
            raise ValueError("predictions and references have different lengths")
        if not predictions:
            return 0.0
        return sum(self.answer_is_correct(p, t) for p, t in zip(predictions, ground_truths)) / len(predictions)


def run_ace_offline(cases: list[dict], *, ace_root: str, provider: str,
                    model: str, save_dir: str, execute: bool = False) -> dict:
    prepared = prepare_ace_samples(cases)
    if prepared["status"] != "READY_FOR_EXPLICIT_ACE_RUN":
        raise RecordError("ACE task blocked: public reviewed TRAIN and VAL required, no blocked cases")
    if not execute or os.environ.get("PDRW_EXPERIENCE_ALLOW_MODEL_CALLS") != "YES":
        raise RecordError("ACE_DISABLED: requires --execute and PDRW_EXPERIENCE_ALLOW_MODEL_CALLS=YES")
    if provider not in {"openai", "together", "sambanova", "commonstack"}:
        raise RecordError("ACE provider unsupported by the pinned upstream interface")
    if not model.strip():
        raise RecordError("ACE model is required")
    root = Path(ace_root).expanduser().resolve()
    if not (root / "ace" / "__init__.py").is_file():
        raise RecordError("ACE checkout root invalid")
    try:
        revision = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True,
            text=True, check=True, timeout=5
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise RecordError("ACE checkout commit cannot be attested") from exc
    if revision != ACE_BASELINE_COMMIT:
        raise RecordError(f"ACE commit mismatch: expected {ACE_BASELINE_COMMIT}")
    ace_module = importlib.import_module("ace")
    imported = Path(ace_module.__file__).resolve()
    if root not in imported.parents:
        raise RecordError("ACE import does not come from the pinned checkout")
    engine = ace_module.ACE(
        api_provider=provider, generator_model=model, reflector_model=model,
        curator_model=model, max_tokens=2048, use_bulletpoint_analyzer=False,
    )
    config = {
        "num_epochs": 1, "max_num_rounds": 1, "curator_frequency": 1,
        "eval_steps": 10, "save_steps": 10, "playbook_token_budget": 4000,
        "task_name": "pdrw_scientific_case_extraction", "json_mode": False,
        "no_ground_truth": False, "save_dir": str(Path(save_dir).resolve()),
        "test_workers": 1, "use_bulletpoint_analyzer": False,
        "api_provider": provider,
    }
    # External ACE may make multiple metered calls and write logs. Provider-level
    # spending limits and private output directory are the host's responsibility.
    return engine.run(
        mode="offline", train_samples=prepared["train"],
        val_samples=prepared["val"], test_samples=[],
        data_processor=ScientificDataProcessor(), config=config,
    )
