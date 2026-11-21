"""Synthetic, externally signed receipts for tests only (never production authority)."""
import base64
import hashlib
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pdrw_experience.core import load_records
from pdrw_experience.trust import canonical_bytes, digest


def sign(private_key, subject, kind, reviewed_at):
    payload = {
        "schema_version": "1.0", "kind": kind,
        "subject_sha256": digest(subject), "reviewed_at": reviewed_at,
        "decision": ("APPROVED_FOR_EXECUTION" if kind == "ACE_RUN_GRANT"
                     else "APPROVED_FOR_ADVISORY"),
    }
    return {"payload": payload, "signature":
            base64.b64encode(private_key.sign(canonical_bytes(payload))).decode("ascii")}


@pytest.fixture
def bundle(tmp_path):
    examples = Path(__file__).parents[1] / "examples"
    cases = load_records(examples / "ace-cases.synthetic.jsonl")
    lesson = load_records(examples / "lesson.synthetic.json")[0]
    source_index = {}
    for number, case in enumerate(cases):
        original = ("Synthetic input " + str(number)).encode("utf-8")
        sha = hashlib.sha256(original).hexdigest()
        case["source_refs"][0]["sha256"] = sha
        location = f"original_{number}.txt"
        (tmp_path / location).write_bytes(original)
        source_index[case["case_id"]] = {case["source_refs"][0]["source_id"]: location}
        if number == 0:
            lesson["case_refs"][0]["sha256"] = sha
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo)
    target_receipts = {}
    for case in cases:
        subject = {"case_id": case["case_id"], "case_sha256": digest(case),
                   "reviewed_target": case["reviewed_target"]}
        target_receipts[case["case_id"]] = sign(
            private_key, subject, "TARGET_REVIEW",
            case["reviewed_target"]["reviewed_at"])
    lesson_receipt = sign(private_key, lesson, "LESSON_REVIEW",
                          lesson["available_at"])
    return {
        "cases": cases, "lesson": lesson, "root": str(tmp_path),
        "source_index": source_index, "public_key": public_key,
        "private_key": private_key, "target_receipts": target_receipts,
        "lesson_receipts": {lesson["lesson_id"]: lesson_receipt},
        "as_of": "2026-04-01",
    }


def store_cli_bundle(tmp_path, bundle):
    filepaths = {}
    for field, value in {
        "cases": bundle["cases"], "lesson": bundle["lesson"],
        "source_index": bundle["source_index"],
        "receipts": bundle["lesson_receipts"],
        "target_receipts": bundle["target_receipts"],
    }.items():
        path = tmp_path / (field + ".json")
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        filepaths[field] = str(path)
    pub = tmp_path / "trusted-review-pub.pem"
    pub.write_bytes(bundle["public_key"])
    filepaths["public_key"] = str(pub)
    return filepaths
