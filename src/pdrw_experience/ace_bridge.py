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
    source_root: str | None = None, source_index: dict | None = None,
) -> dict:
    """ACE data preparation: future- and group-isolated, fact labels only."""
    import json
    from .core import _date
    from .trust import digest, verify_receipt, verify_source_bytes

    _date(as_of, "as_of")
    trust_fields = (target_receipts, trusted_public_key, source_root, source_index)
    if any(x is not None for x in trust_fields) and any(x is None for x in trust_fields):
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
                verify_source_bytes([case], [
                    {"case_id": cid, "source_id": source["source_id"],
                     "sha256": source["sha256"]} for source in case["source_refs"]
                ], source_root=source_root, source_index=source_index)
            except (RecordError, TypeError, OSError) as exc:
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


def run_ace_offline(
    cases: list[dict], *, ace_root: str, provider: str, model: str,
    save_dir: str, as_of: str, target_receipts: dict | None,
    trusted_public_key: bytes | None, source_root: str | None,
    source_index: dict | None, execution_grant: dict | None,
    max_model_calls: int = 10, max_wall_seconds: int = 120,
    execute: bool = False,
) -> dict:
    """Run approved public ACE samples with a bounded worker, never in-process.

    Provider-side dollar caps and egress policy remain an external requirement:
    a call budget is not a dollar guarantee or a full security sandbox.
    """
    import json
    import sys
    from datetime import date
    from .trust import verify_receipt, digest

    prepared = prepare_ace_samples(
        cases, as_of=as_of, target_receipts=target_receipts,
        trusted_public_key=trusted_public_key,
        source_root=source_root, source_index=source_index)
    if prepared["status"] != "READY_FOR_EXPLICIT_ACE_RUN":
        raise RecordError("ACE_DATA_NOT_INDEPENDENTLY_ATTESTED")
    if not execute or os.environ.get("PDRW_EXPERIENCE_ALLOW_MODEL_CALLS") != "YES":
        raise RecordError("ACE_DISABLED: requires --execute and PDRW_EXPERIENCE_ALLOW_MODEL_CALLS=YES")
    if type(max_model_calls) is not int or not 1 <= max_model_calls <= 30:
        raise RecordError("ACE_MODEL_CALL_CAP_INVALID")
    if type(max_wall_seconds) is not int or not 1 <= max_wall_seconds <= 300:
        raise RecordError("ACE_WALL_SECONDS_CAP_INVALID")
    if provider not in {"openai", "together", "sambanova", "commonstack"} or not model.strip():
        raise RecordError("ACE_PROVIDER_OR_MODEL_UNSUPPORTED")
    job = {
        "as_of": as_of, "provider": provider, "model": model,
        "max_model_calls": max_model_calls,
        "max_wall_seconds": max_wall_seconds,
        "ace_commit": ACE_BASELINE_COMMIT,
        "case_hashes": sorted(digest(case) for case in cases),
    }
    if execution_grant is None or trusted_public_key is None:
        raise RecordError("ACE_SIGNED_RUN_GRANT_REQUIRED")
    verify_receipt(job, execution_grant, kind="ACE_RUN_GRANT",
                   trusted_public_key=trusted_public_key,
                   as_of=date.today().isoformat())
    root = Path(ace_root).expanduser().resolve(strict=True)
    if not (root / "ace" / "__init__.py").is_file():
        raise RecordError("ACE_CHECKOUT_ROOT_INVALID")
    try:
        revision = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True, timeout=5).stdout.strip()
        dirty = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all"],
            capture_output=True, text=True, check=True, timeout=5).stdout.strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise RecordError("ACE_GIT_STATUS_NOT_ATTESTABLE") from exc
    if revision != ACE_BASELINE_COMMIT or dirty:
        raise RecordError("ACE_COMMIT_MISMATCH_OR_DIRTY_CHECKOUT")
    destination = Path(save_dir).expanduser().resolve()
    if destination.is_relative_to(root):
        raise RecordError("ACE_RESULTS_CANNOT_LIVE_INSIDE_UPSTREAM_CHECKOUT")
    destination.mkdir(parents=True, exist_ok=True)
    payload = {
        "root": str(root), "provider": provider, "model": model,
        "save_dir": str(destination), "train": prepared["train"],
        "val": prepared["val"], "max_model_calls": max_model_calls,
    }
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pdrw_experience._ace_worker"],
            input=json.dumps(payload, ensure_ascii=False), text=True,
            capture_output=True, timeout=max_wall_seconds, check=False,
            cwd=str(root), env=os.environ.copy())
    except subprocess.TimeoutExpired as exc:
        raise RecordError("ACE_WORKER_WALL_TIMEOUT_KILLED") from exc
    if proc.returncode:
        raise RecordError(f"ACE_WORKER_FAILED_EXIT_{proc.returncode}")
    marker = "PDRW_ACE_RESULT_JSON="
    result_line = next((line[len(marker):] for line in reversed(proc.stdout.splitlines())
                        if line.startswith(marker)), None)
    if result_line is None:
        raise RecordError("ACE_WORKER_NO_RESULT_RECEIPT")
    result = json.loads(result_line)
    if result.get("model_calls", max_model_calls + 1) > max_model_calls:
        raise RecordError("ACE_CALL_BUDGET_EXCEEDED")
    return result
