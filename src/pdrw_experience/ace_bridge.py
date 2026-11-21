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


def prepare_ace_samples(cases: list[dict]) -> dict:
    """Create ACE-compatible offline task records; no model call or disk write."""
    result = {"train": [], "val": [], "blocked": [], "engine": "ACE", "model_calls": 0}
    groups = {"TRAIN": set(), "VAL": set()}
    for case in cases:
        validate_case(case)
        cid = case["case_id"]
        if case["split"] == "TEST":
            continue  # sealed evaluation cases must never enter ACE adaptation
        if case["classification"] != "PUBLIC" or any(
            s["visibility"] != "PUBLIC" for s in case["source_refs"]
        ):
            result["blocked"].append({"case_id": cid, "reason": "NONPUBLIC_SOURCE"})
            continue
        target = case.get("reviewed_target")
        if target is None:
            result["blocked"].append({"case_id": cid, "reason": "NO_INDEPENDENT_REFERENCE_TARGET"})
            continue
        groups[case["split"]].add(case["case_group"])
        result["train" if case["split"] == "TRAIN" else "val"].append({
            "context": (f"Case {cid}; type {case['case_type']}; research question: "
                        f"{case['research_question']}; method: {case['method']}; "
                        f"observed outcome: {case['observed_outcome']}; "
                        f"limitations: {'; '.join(case['limitations'])}. "
                        "This is a described case, not proof of causal generality."),
            "question": target["question"],
            "target": target["answer"],
            "review_ref": target["review_ref"],
            "case_id": cid,
        })
    overlap = groups["TRAIN"] & groups["VAL"]
    if overlap:
        raise RecordError(f"TRAIN/VAL case_group leakage: {sorted(overlap)}")
    result["status"] = (
        "READY_FOR_EXPLICIT_ACE_RUN"
        if result["train"] and result["val"] and not result["blocked"]
        else "BLOCKED"
    )
    return result


class ScientificDataProcessor:
    """ACE-compatible exact-reference baseline, not a scientific judge."""

    def process_task_data(self, rows):
        return rows

    def answer_is_correct(self, predicted, ground_truth):
        return isinstance(predicted, str) and isinstance(ground_truth, str) and (
            predicted.strip() == ground_truth.strip()
        )

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
