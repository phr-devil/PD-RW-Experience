"""Detached Ed25519 review receipts and explicit source-byte verification.

Trust keys and source indexes MUST be supplied by the trusted host, not by
untrusted lesson or case files. Signers are external; no signing key lives here.
"""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .core import RecordError, _date


def canonical_bytes(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value: dict) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def verify_receipt(subject: dict, receipt: dict, *, kind: str,
                   trusted_public_key: bytes, as_of: str) -> dict:
    """Checks a signed *review decision*, never scientific correctness."""
    _date(as_of, "as_of")
    if not isinstance(receipt, dict) or set(receipt) != {"payload", "signature"}:
        raise RecordError("REVIEW_RECEIPT_INVALID")
    payload = receipt["payload"]
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version", "kind", "subject_sha256", "reviewed_at", "decision"
    }:
        raise RecordError("REVIEW_PAYLOAD_INVALID")
    if (payload["schema_version"] != "1.0" or payload["kind"] != kind
            or payload["decision"] != "APPROVED_FOR_ADVISORY"
            or payload["subject_sha256"] != digest(subject)):
        raise RecordError("REVIEW_PAYLOAD_MISMATCH")
    reviewed_at = _date(payload["reviewed_at"], "reviewed_at")
    if reviewed_at > as_of:
        raise RecordError("REVIEW_NOT_YET_VISIBLE")
    if "available_at" in subject and reviewed_at > subject["available_at"]:
        raise RecordError("REVIEW_AFTER_LESSON_AVAILABLE")
    try:
        key = serialization.load_pem_public_key(trusted_public_key)
        if not isinstance(key, Ed25519PublicKey):
            raise ValueError("wrong key algorithm")
        signature = base64.b64decode(receipt["signature"], validate=True)
        key.verify(signature, canonical_bytes(payload))
    except (InvalidSignature, ValueError, TypeError) as exc:
        raise RecordError("REVIEW_SIGNATURE_INVALID") from exc
    return {"reviewed_at": reviewed_at, "subject_sha256": digest(subject),
            "review_authorization_verified": True,
            "scientific_validity_verified": False}


def verify_source_bytes(cases: list[dict], source_refs: list[dict], *,
                        source_root: str | Path, source_index: dict) -> None:
    """Hash only explicit, root-contained original files; no directory scans."""
    root = Path(source_root).expanduser().resolve(strict=True)
    if not root.is_dir() or not isinstance(source_index, dict):
        raise RecordError("SOURCE_TRUST_CONFIG_INVALID")
    by_case = {c["case_id"]: c for c in cases}
    for ref in source_refs:
        case = by_case.get(ref["case_id"])
        if case is None:
            raise RecordError("SOURCE_CASE_MISSING")
        expected = next((s for s in case["source_refs"]
                         if s["source_id"] == ref["source_id"]), None)
        if expected is None:
            raise RecordError("SOURCE_REF_MISSING")
        paths = source_index.get(case["case_id"])
        if not isinstance(paths, dict):
            raise RecordError("SOURCE_PATH_UNREGISTERED")
        rel = paths.get(ref["source_id"])
        if not isinstance(rel, str) or not rel or Path(rel).is_absolute():
            raise RecordError("SOURCE_PATH_UNREGISTERED")
        path = (root / rel).resolve(strict=True)
        if not path.is_relative_to(root) or not path.is_file():
            raise RecordError("SOURCE_OUTSIDE_TRUSTED_ROOT")
        h = hashlib.sha256()
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                h.update(chunk)
        if h.hexdigest() != expected["sha256"].lower() or h.hexdigest() != ref["sha256"].lower():
            raise RecordError("SOURCE_BYTES_HASH_MISMATCH")
