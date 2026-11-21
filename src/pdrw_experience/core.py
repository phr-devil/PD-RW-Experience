"""Offline provenance checks and conservative experience export.

No schema-only check validates a scientific claim or authenticates authority.
Original cases are read only. This module has no model calls or data downloads.
"""
from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import re

SCHEMA_VERSION = "1.0"
KINDS = {"paper", "success", "failure", "mixed"}
SPLITS = {"TRAIN", "VAL", "TEST"}
CATEGORIES = {"research_strategy", "algorithm_strategy", "experimental_strategy",
              "publication_strategy"}
STATUSES = {"CANDIDATE", "REVIEWED", "CONFLICTED", "REFUTED"}
CLASSIFICATIONS = {"PUBLIC", "PRIVATE"}


class RecordError(ValueError):
    """Input is invalid or lacks the minimum information for safe processing."""


def _need_string(obj: dict, field: str) -> str:
    value = obj.get(field)
    if not isinstance(value, str) or not value.strip():
        raise RecordError(f"{field}: nonempty string required")
    return value.strip()


def _date(value: str, field: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise RecordError(f"{field}: YYYY-MM-DD required")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise RecordError(f"{field}: invalid date") from exc
    return value


def _strings(obj: dict, field: str, *, minimum: int = 0) -> list[str]:
    value = obj.get(field, [])
    if not isinstance(value, list) or len(value) < minimum or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise RecordError(f"{field}: list of nonempty strings required")
    return value


def _sha(value: object, field: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-fA-F0-9]{64}", value):
        raise RecordError(f"{field}: SHA-256 hex digest required")
    return value.lower()


def validate_case(record: dict) -> dict:
    if not isinstance(record, dict) or record.get("schema_version") != SCHEMA_VERSION:
        raise RecordError("case.schema_version must be 1.0")
    _need_string(record, "case_id")
    if record.get("case_type") not in KINDS:
        raise RecordError("case_type invalid")
    if record.get("split") not in SPLITS:
        raise RecordError("split must be TRAIN, VAL or TEST")
    if record.get("classification") not in CLASSIFICATIONS:
        raise RecordError("classification must be PUBLIC or PRIVATE")
    _date(record.get("available_at"), "available_at")
    for key in ("case_group", "research_question", "method", "observed_outcome"):
        _need_string(record, key)
    _strings(record, "limitations", minimum=1)
    sources = record.get("source_refs")
    if not isinstance(sources, list) or not sources:
        raise RecordError("source_refs: at least one original reference required")
    ids = set()
    for source in sources:
        if not isinstance(source, dict):
            raise RecordError("source_refs entries must be objects")
        sid = _need_string(source, "source_id")
        if sid in ids:
            raise RecordError("duplicate source_id")
        ids.add(sid)
        _sha(source.get("sha256"), "source.sha256")
        src_time = _date(source.get("available_at"), "source.available_at")
        if src_time > record["available_at"]:
            raise RecordError("case available_at predates source")
        if source.get("visibility") not in CLASSIFICATIONS:
            raise RecordError("source.visibility invalid")
    target = record.get("reviewed_target")
    if target is not None:
        if not isinstance(target, dict):
            raise RecordError("reviewed_target must be object")
        for key in ("question", "answer", "review_ref"):
            _need_string(target, key)
    return record


def validate_lesson(record: dict) -> dict:
    if not isinstance(record, dict) or record.get("schema_version") != SCHEMA_VERSION:
        raise RecordError("lesson.schema_version must be 1.0")
    for field in ("lesson_id", "claim", "mechanism"):
        _need_string(record, field)
    if record.get("category") not in CATEGORIES:
        raise RecordError("lesson.category invalid")
    if record.get("status") not in STATUSES:
        raise RecordError("lesson.status invalid")
    if record.get("classification") not in CLASSIFICATIONS:
        raise RecordError("lesson.classification invalid")
    _date(record.get("available_at"), "lesson.available_at")
    version = record.get("version")
    if type(version) is not int or version < 1:
        raise RecordError("lesson.version must be positive integer")
    _strings(record, "conditions", minimum=1)
    _strings(record, "limitations", minimum=1)
    _strings(record, "task_types", minimum=1)
    _strings(record, "keywords")
    _strings(record, "conflicts_with")
    refs = record.get("case_refs")
    if not isinstance(refs, list) or not refs:
        raise RecordError("lesson.case_refs required")
    unique = set()
    for ref in refs:
        if not isinstance(ref, dict):
            raise RecordError("case_refs entries must be objects")
        pair = (_need_string(ref, "case_id"), _need_string(ref, "source_id"))
        if pair in unique:
            raise RecordError("duplicate lesson case source reference")
        unique.add(pair)
        _sha(ref.get("sha256"), "lesson source sha256")
    if record.get("status") == "REVIEWED":
        _need_string(record, "review_ref")
    return record


def review_lesson(lesson: dict, cases: list[dict]) -> dict:
    """Validate declared lineage and conflicts, NOT the correctness of conclusions."""
    validate_lesson(lesson)
    indexed = {}
    for case in cases:
        validate_case(case)
        if case["case_id"] in indexed:
            raise RecordError("duplicate case_id in case catalog")
        indexed[case["case_id"]] = case
    reasons = []
    for ref in lesson["case_refs"]:
        case = indexed.get(ref["case_id"])
        if case is None:
            reasons.append(f"CASE_MISSING:{ref['case_id']}")
            continue
        source = next((s for s in case["source_refs"] if s["source_id"] == ref["source_id"]), None)
        if source is None or source["sha256"].lower() != ref["sha256"].lower():
            reasons.append(f"SOURCE_UNMATCHED:{ref['case_id']}:{ref['source_id']}")
            continue
        if case["available_at"] > lesson["available_at"]:
            reasons.append(f"FUTURE_CASE:{ref['case_id']}")
        if source["available_at"] > lesson["available_at"]:
            reasons.append(f"FUTURE_SOURCE:{ref['case_id']}")
        if case["classification"] != "PUBLIC" and lesson["classification"] == "PUBLIC":
            reasons.append(f"PRIVATE_TO_PUBLIC:{ref['case_id']}")
    if lesson.get("conflicts_with"):
        reasons.append("CONFLICT_REVIEW_REQUIRED")
    return {
        "lesson_id": lesson["lesson_id"],
        "status": "BLOCKED" if reasons else "DECLARED_LINEAGE_MATCHED_ONLY",
        "reasons": reasons,
        "scientific_validity_verified": False,
        "review_authorization_verified": False,
        "automatic_rule_promotion": False,
    }


def _terms(value: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9_-]+|[\u4e00-\u9fff]", value.lower()))


def retrieve_guidance(
    lessons: list[dict], cases: list[dict], *,
    task_type: str, query: str, as_of: str,
    limit: int = 5,
) -> list[dict]:
    """P4 advice only; fail closed on missing provenance, future or test cases."""
    _date(as_of, "as_of")
    if not task_type.strip() or type(limit) is not int or not 1 <= limit <= 20:
        raise RecordError("task_type or limit invalid")
    source_cases = {c["case_id"]: validate_case(c) for c in cases}
    if len(source_cases) != len(cases):
        raise RecordError("duplicate case_id")
    scored = []
    for lesson in lessons:
        validate_lesson(lesson)
        if (lesson["status"] != "REVIEWED" or
                lesson["classification"] != "PUBLIC" or
                task_type not in lesson["task_types"] or
                lesson["available_at"] > as_of):
            continue
        review = review_lesson(lesson, cases)
        if review["status"] != "DECLARED_LINEAGE_MATCHED_ONLY":
            continue
        if any(source_cases[ref["case_id"]]["split"] != "TRAIN"
               or source_cases[ref["case_id"]]["available_at"] > as_of
               or any(s["visibility"] != "PUBLIC" for s in source_cases[ref["case_id"]]["source_refs"])
               for ref in lesson["case_refs"]):
            continue
        tokens = _terms(query)
        searchable = _terms(" ".join([lesson["claim"], lesson["mechanism"],
                                      *lesson["conditions"], *lesson["keywords"]]))
        score = len(tokens & searchable)
        if query.strip() and score == 0:
            continue
        ids = [f"{r['case_id']}#{r['source_id']}" for r in lesson["case_refs"]]
        scored.append((score, lesson["lesson_id"], {
            "id": f"{lesson['lesson_id']}:v{lesson['version']}",
            "level": "experience",
            "source": f"PD-RW-Experience:{lesson['lesson_id']}:declared_review:{lesson['review_ref']}",
            "text": lesson["claim"],
            "task_types": lesson["task_types"],
            "evidence_refs": ids,
            "conditions": lesson["conditions"],
        }))
    return [row for _, _, row in sorted(scored, key=lambda x: (-x[0], x[1]))[:limit]]


def validate_feedback(feedback: dict) -> dict:
    if not isinstance(feedback, dict) or feedback.get("schema_version") != SCHEMA_VERSION:
        raise RecordError("feedback.schema_version must be 1.0")
    for k in ("task_id", "lesson_id", "observation"):
        _need_string(feedback, k)
    if feedback.get("outcome") not in {"POSITIVE", "NEGATIVE", "INCONCLUSIVE"}:
        raise RecordError("feedback.outcome invalid")
    _date(feedback.get("observed_at"), "feedback.observed_at")
    _strings(feedback, "evidence_refs", minimum=1)
    return {
        "status": "RECEIVED_UNVERIFIED",
        "automatic_lesson_update": False,
        "automatic_rule_promotion": False,
        "task_id": feedback["task_id"],
        "lesson_id": feedback["lesson_id"],
    }


def load_records(path: str | Path) -> list[dict]:
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    if file.suffix.lower() == ".jsonl":
        data = [json.loads(line) for line in text.splitlines() if line.strip()]
    else:
        data = json.loads(text)
        data = data if isinstance(data, list) else [data]
    if not all(isinstance(row, dict) for row in data):
        raise RecordError("records must be JSON objects")
    return data
