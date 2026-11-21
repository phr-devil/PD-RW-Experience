import copy
import json
import pytest

from pdrw_experience.ace_bridge import (
    ScientificDataProcessor, prepare_ace_samples, run_ace_offline)
from pdrw_experience.core import RecordError


def prepared(bundle, **kwargs):
    return prepare_ace_samples(bundle["cases"], as_of=bundle["as_of"], **kwargs)


def trust(bundle):
    return dict(target_receipts=bundle["target_receipts"],
                trusted_public_key=bundle["public_key"],
                source_root=bundle["root"], source_index=bundle["source_index"])


def test_ace_dry_run_is_not_verified(bundle):
    result = prepared(bundle)
    assert result["status"] == "READY_FOR_LOCAL_DRY_RUN_ONLY"
    assert len(result["train"]) == len(result["val"]) == 1
    assert not result["review_attested"] and result["model_calls"] == 0


def test_ace_preflight_signed_targets_and_real_bytes(bundle):
    result = prepared(bundle, **trust(bundle))
    assert result["status"] == "READY_FOR_EXPLICIT_ACE_RUN"
    assert result["review_attested"]
    assert len(result["train"]) == 1


def test_ace_blocks_missing_target(bundle):
    cases = copy.deepcopy(bundle["cases"])
    del cases[0]["reviewed_target"]
    result = prepare_ace_samples(cases, as_of=bundle["as_of"])
    assert result["status"] == "BLOCKED"
    assert "NO_INDEPENDENT_REFERENCE_TARGET" in str(result["blocked"])


def test_ace_private_sources_blocked(bundle):
    cases = copy.deepcopy(bundle["cases"])
    cases[0]["source_refs"][0]["visibility"] = "PRIVATE"
    result = prepare_ace_samples(cases, as_of=bundle["as_of"])
    assert "NONPUBLIC_SOURCE" in str(result["blocked"])


def test_ace_group_leakage_across_splits(bundle):
    cases = copy.deepcopy(bundle["cases"])
    cases[1]["case_group"] = cases[0]["case_group"]
    with pytest.raises(RecordError, match="CASE_GROUP_LEAKAGE"):
        prepare_ace_samples(cases, as_of=bundle["as_of"])


def test_ace_source_hash_leakage_across_splits(bundle):
    cases = copy.deepcopy(bundle["cases"])
    cases[1]["source_refs"][0]["sha256"] = cases[0]["source_refs"][0]["sha256"]
    with pytest.raises(RecordError, match="SOURCE_BYTES_LEAKAGE"):
        prepare_ace_samples(cases, as_of=bundle["as_of"])


def test_ace_duplicate_case_id_rejected(bundle):
    cases = copy.deepcopy(bundle["cases"])
    cases[1]["case_id"] = cases[0]["case_id"]
    with pytest.raises(RecordError, match="DUPLICATE_CASE_ID"):
        prepare_ace_samples(cases, as_of=bundle["as_of"])


def test_test_split_is_not_training_input(bundle):
    cases = copy.deepcopy(bundle["cases"])
    cases[1]["split"] = "TEST"
    result = prepare_ace_samples(cases, as_of=bundle["as_of"])
    assert result["status"] == "BLOCKED"
    assert "TEST_IN_ADAPTATION_INPUT" in str(result["blocked"])


def test_future_case_or_review_blocked(bundle):
    cases = copy.deepcopy(bundle["cases"])
    cases[0]["available_at"] = "2026-12-01"
    # Keep record internally consistent: source is not after case.
    result = prepare_ace_samples(cases, as_of=bundle["as_of"])
    assert "FUTURE_SOURCE_OR_CASE" in str(result["blocked"])
    cases = copy.deepcopy(bundle["cases"])
    cases[0]["reviewed_target"]["reviewed_at"] = "2026-12-01"
    result = prepare_ace_samples(cases, as_of=bundle["as_of"])
    assert "FUTURE_TARGET_REVIEW" in str(result["blocked"])


def test_forged_target_review_blocks(bundle):
    receipts = copy.deepcopy(bundle["target_receipts"])
    receipts["SYN-001"]["signature"] = "AA=="
    result = prepared(bundle, **{**trust(bundle), "target_receipts": receipts})
    assert result["status"] == "BLOCKED"
    assert "TARGET_REVIEW_UNATTESTED" in str(result["blocked"])


def test_fact_answers_allow_explicit_approved_aliases(bundle):
    data = prepared(bundle)["train"][0]
    target = data["target"]
    p = ScientificDataProcessor()
    assert p.answer_is_correct(" FUTURE ASSISTED anchors are not prefix valid ", target)
    assert p.answer_is_correct("Future-assisted anchors are not prefix-valid.", target)
    assert not p.answer_is_correct("This approach is scientifically universal", target)
    assert not p.answer_is_correct("x", "x")
    assert p.evaluate_accuracy(["a", "b"], [target, target]) == 0.0


def test_unapproved_freeform_science_target_rejected(bundle):
    cases = copy.deepcopy(bundle["cases"])
    cases[0]["reviewed_target"]["evaluation_type"] = "LLM_JUDGE_NOVELTY"
    with pytest.raises(RecordError, match="NORMALIZED_FACT"):
        prepare_ace_samples(cases, as_of=bundle["as_of"])


def test_ace_does_not_run_without_trusted_data(bundle, monkeypatch):
    monkeypatch.setenv("PDRW_EXPERIENCE_ALLOW_MODEL_CALLS", "YES")
    with pytest.raises(RecordError, match="NOT_INDEPENDENTLY_ATTESTED"):
        run_ace_offline(bundle["cases"], ace_root="/missing", provider="openai",
                        model="dummy", save_dir="/tmp", as_of=bundle["as_of"],
                        target_receipts=None, trusted_public_key=None,
                        source_root=None, source_index=None,
                        execution_grant=None, execute=True)


def test_ace_does_not_run_without_explicit_optin(bundle, monkeypatch):
    monkeypatch.delenv("PDRW_EXPERIENCE_ALLOW_MODEL_CALLS", raising=False)
    with pytest.raises(RecordError, match="ACE_DISABLED"):
        run_ace_offline(bundle["cases"], ace_root="/missing", provider="openai",
                        model="dummy", save_dir="/tmp", as_of=bundle["as_of"],
                        execution_grant=None, execute=False, **trust(bundle))


def test_ace_needs_signed_spend_grant(bundle, monkeypatch):
    monkeypatch.setenv("PDRW_EXPERIENCE_ALLOW_MODEL_CALLS", "YES")
    with pytest.raises(RecordError, match="ACE_SIGNED_RUN_GRANT_REQUIRED"):
        run_ace_offline(bundle["cases"], ace_root="/missing", provider="openai",
                        model="dummy", save_dir="/tmp", as_of=bundle["as_of"],
                        execution_grant=None, execute=True, **trust(bundle))


def test_ace_input_size_is_bounded(bundle):
    cases = copy.deepcopy(bundle["cases"])
    cases[0]["method"] = "z" * 13000
    result = prepare_ace_samples(cases, as_of=bundle["as_of"])
    assert "ACE_INPUT_SIZE_CAP_EXCEEDED" in str(result["blocked"])


def test_ace_batch_size_cap(bundle):
    with pytest.raises(RecordError, match="ACE_BATCH_SIZE_CAP_EXCEEDED"):
        prepare_ace_samples(bundle["cases"] * 17, as_of=bundle["as_of"])
