import copy
import json
from pathlib import Path

import pytest

from pdrw_experience.core import (
    RecordError, load_records, retrieve_guidance, review_lesson,
    validate_case, validate_feedback, validate_lesson
)

ROOT = Path(__file__).parents[1] / "examples"


def fixtures():
    return load_records(ROOT / "case.synthetic.json")[0], load_records(ROOT / "lesson.synthetic.json")[0]


def test_case_and_lesson_shapes():
    case, lesson = fixtures()
    assert validate_case(case)["case_id"] == "SYN-001"
    assert validate_lesson(lesson)["lesson_id"] == "SYN-L001"


def test_lineage_declared_not_scientifically_verified():
    case, lesson = fixtures()
    result = review_lesson(lesson, [case])
    assert result["status"] == "DECLARED_LINEAGE_MATCHED_ONLY"
    assert result["scientific_validity_verified"] is False


def test_reference_mismatch_blocks():
    case, lesson = fixtures()
    lesson["case_refs"][0]["sha256"] = "f" * 64
    result = review_lesson(lesson, [case])
    assert result["status"] == "BLOCKED"
    assert "SOURCE_UNMATCHED" in result["reasons"][0]


def test_future_case_blocks():
    case, lesson = fixtures()
    lesson["available_at"] = "2025-01-01"
    assert "FUTURE_CASE:SYN-001" in review_lesson(lesson, [case])["reasons"]


def test_private_case_cannot_publish_public_lesson():
    case, lesson = fixtures()
    case["classification"] = "PRIVATE"
    assert "PRIVATE_TO_PUBLIC:SYN-001" in review_lesson(lesson, [case])["reasons"]


def test_p4_guidance_fields_and_as_of():
    case, lesson = fixtures()
    found = retrieve_guidance([lesson], [case], task_type="experiment_design",
                              query="leakage", as_of="2026-04-01")
    assert len(found) == 1
    assert found[0]["level"] == "experience"
    assert found[0]["source"].startswith("PD-RW-Experience:")
    assert found[0]["evidence_refs"] == ["SYN-001#synthetic:run:001"]
    assert not retrieve_guidance([lesson], [case], task_type="experiment_design",
                                 query="leakage", as_of="2026-01-01")


def test_test_case_cannot_be_retrieved():
    case, lesson = fixtures()
    case["split"] = "TEST"
    assert retrieve_guidance([lesson], [case], task_type="experiment_design",
                             query="leakage", as_of="2026-04-01") == []


def test_candidate_or_conflict_not_retrieved():
    case, lesson = fixtures()
    lesson["status"] = "CANDIDATE"
    assert retrieve_guidance([lesson], [case], task_type="experiment_design",
                             query="", as_of="2026-04-01") == []
    lesson["status"] = "REVIEWED"
    lesson["conflicts_with"] = ["SYN-L002"]
    assert retrieve_guidance([lesson], [case], task_type="experiment_design",
                             query="", as_of="2026-04-01") == []


def test_invalid_hash_rejected():
    case, _ = fixtures()
    case["source_refs"][0]["sha256"] = "not-a-sha"
    with pytest.raises(RecordError):
        validate_case(case)


def test_feedback_is_advisory_only():
    feedback = load_records(ROOT / "feedback.synthetic.json")[0]
    result = validate_feedback(feedback)
    assert result["status"] == "RECEIVED_UNVERIFIED"
    assert result["automatic_lesson_update"] is False
