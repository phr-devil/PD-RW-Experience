import copy
import json
from pathlib import Path
import pytest
from pdrw_experience.core import (
    RecordError, load_records, retrieve_guidance, review_lesson,
    validate_case, validate_feedback, validate_lesson)

EXAMPLES = Path(__file__).parents[1] / "examples"


def fixtures():
    return (load_records(EXAMPLES / "case.synthetic.json")[0],
            load_records(EXAMPLES / "lesson.synthetic.json")[0])


def trust(bundle):
    return dict(receipt=bundle["lesson_receipts"][bundle["lesson"]["lesson_id"]],
                trusted_public_key=bundle["public_key"],
                source_root=bundle["root"], source_index=bundle["source_index"],
                as_of=bundle["as_of"])


def guidance_trust(bundle):
    return dict(receipts=bundle["lesson_receipts"],
                trusted_public_key=bundle["public_key"],
                source_root=bundle["root"], source_index=bundle["source_index"])


def test_shapes():
    case, lesson = fixtures()
    assert validate_case(case)["case_id"] == "SYN-001"
    assert validate_lesson(lesson)["lesson_id"] == "SYN-L001"


def test_declared_match_is_not_authenticated():
    case, lesson = fixtures()
    data = review_lesson(lesson, [case])
    assert data["status"] == "DECLARED_LINEAGE_MATCHED_ONLY"
    assert not data["review_authorization_verified"]
    assert not data["scientific_validity_verified"]


def test_signed_review_and_original_bytes(bundle):
    data = review_lesson(bundle["lesson"], bundle["cases"], **trust(bundle))
    assert data["status"] == "ATTESTED_SOURCE_MATCHED_FOR_ADVISORY"
    assert data["source_bytes_verified"] and data["review_authorization_verified"]
    assert not data["scientific_validity_verified"]


def test_untrusted_review_cannot_export(bundle):
    with pytest.raises(RecordError, match="TRUSTED_REVIEW"):
        retrieve_guidance([bundle["lesson"]], bundle["cases"],
                          task_type="experiment_design", query="leakage",
                          as_of=bundle["as_of"])


def test_p4_advisory_only_with_review(bundle):
    result = retrieve_guidance(
        [bundle["lesson"]], bundle["cases"], task_type="experiment_design",
        query="leakage", as_of=bundle["as_of"], **guidance_trust(bundle))
    assert len(result) == 1
    assert result[0]["level"] == "experience"
    assert result[0]["source"].startswith("PD-RW-Experience:")
    assert result[0]["evidence_refs"] == ["SYN-001#synthetic:run:001"]
    assert result[0]["conditions"]


def test_future_or_test_blocked(bundle):
    kw = guidance_trust(bundle)
    assert not retrieve_guidance([bundle["lesson"]], bundle["cases"],
                                 task_type="experiment_design", query="leakage",
                                 as_of="2026-01-01", **kw)
    mutated = copy.deepcopy(bundle["cases"])
    mutated[0]["split"] = "TEST"
    assert not retrieve_guidance([bundle["lesson"]], mutated,
                                 task_type="experiment_design", query="leakage",
                                 as_of=bundle["as_of"], **kw)


def test_source_bytes_modified_after_review(bundle):
    first = Path(bundle["root"]) / bundle["source_index"]["SYN-001"]["synthetic:run:001"]
    first.write_text("Tampered!", encoding="utf-8")
    result = review_lesson(bundle["lesson"], bundle["cases"], **trust(bundle))
    assert result["status"] == "BLOCKED"
    assert "SOURCE_BYTES_HASH_MISMATCH" in result["reasons"][0]


def test_forged_signature_blocked(bundle):
    receipt = copy.deepcopy(bundle["lesson_receipts"]["SYN-L001"])
    receipt["signature"] = "AA=="
    result = review_lesson(bundle["lesson"], bundle["cases"],
                           **{**trust(bundle), "receipt": receipt})
    assert result["status"] == "BLOCKED"


def test_cross_case_reference_mismatch_blocked(bundle):
    lesson = copy.deepcopy(bundle["lesson"])
    lesson["case_refs"][0]["sha256"] = "f" * 64
    assert review_lesson(lesson, bundle["cases"], **trust(bundle))["status"] == "BLOCKED"


def test_conflict_and_candidate_not_retrievable(bundle):
    lesson = copy.deepcopy(bundle["lesson"])
    lesson["status"] = "CANDIDATE"
    assert not retrieve_guidance([lesson], bundle["cases"],
                                 task_type="experiment_design", query="",
                                 as_of=bundle["as_of"], **guidance_trust(bundle))
    lesson = copy.deepcopy(bundle["lesson"])
    lesson["conflicts_with"] = ["SYN-L002"]
    assert not retrieve_guidance([lesson], bundle["cases"],
                                 task_type="experiment_design", query="",
                                 as_of=bundle["as_of"], **guidance_trust(bundle))


def test_private_source_and_path_escape_blocked(bundle, tmp_path):
    from pdrw_experience.trust import verify_source_bytes
    index = copy.deepcopy(bundle["source_index"])
    index["SYN-001"]["synthetic:run:001"] = "../outside.txt"
    (tmp_path.parent / "outside.txt").write_text("outside")
    with pytest.raises(RecordError, match="SOURCE_OUTSIDE_TRUSTED_ROOT"):
        verify_source_bytes(bundle["cases"], bundle["lesson"]["case_refs"],
                            source_root=bundle["root"], source_index=index)


def test_bad_digest_is_rejected():
    case, _ = fixtures()
    case["source_refs"][0]["sha256"] = "invalid"
    with pytest.raises(RecordError):
        validate_case(case)


def test_feedback_stays_unverified():
    feedback = load_records(EXAMPLES / "feedback.synthetic.json")[0]
    result = validate_feedback(feedback)
    assert result["status"] == "RECEIVED_UNVERIFIED"
    assert result["automatic_lesson_update"] is False
