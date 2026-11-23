"""Read-only PD-RW-Agent Knowledge Mirror v1.2 -> ScientificCase v1 adapter.

A verified mirror card is *secondary evidence*. It never proves that original
paper/Run bytes exist or that a recorded scientific claim is true.
"""
from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path

from .core import RecordError, validate_case

MAX_MANIFEST_BYTES = 2_000_000
MAX_FILES = 1500
MAX_FILE_BYTES = 8_000_000
MAX_CASES = 500
EXPECTED_MIRROR_VERSION = "1.2"
EXPECTED_CARD_FORMAT = "pdrw-case-card-v2"


def _json(data: bytes, what: str) -> dict:
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise RecordError(f"{what}: invalid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise RecordError(f"{what}: expected object")
    return value


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _day(value: object, field: str) -> str:
    if not isinstance(value, str) or len(value) != 10:
        raise RecordError(f"{field}: explicit YYYY-MM-DD required")
    try:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError()
    except ValueError as exc:
        raise RecordError(f"{field}: invalid YYYY-MM-DD") from exc
    return value


def _path(root: Path, rel: str) -> Path:
    if not isinstance(rel, str) or not rel or "\\" in rel or ":" in rel:
        raise RecordError("MIRROR_PATH_INVALID")
    p = Path(rel)
    if p.is_absolute() or any(part in {".", "..", ""} for part in p.parts):
        raise RecordError("MIRROR_PATH_INVALID")
    resolved = (root / rel).resolve(strict=True)
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise RecordError("MIRROR_PATH_OUTSIDE_ROOT_OR_MISSING")
    return resolved


def _bytes(path: Path, *, limit: int = MAX_FILE_BYTES) -> bytes:
    if path.stat().st_size > limit:
        raise RecordError("MIRROR_FILE_TOO_LARGE")
    return path.read_bytes()


def load_mirror(root: str | Path) -> dict:
    """Verify all files against the generated manifest and index/card contract.

    This checks internal integrity, *not* the truth or provenance of the
    original CASE_LIBRARY, original Runs or paper evidence.
    """
    directory = Path(root).expanduser().resolve(strict=True)
    if not directory.is_dir():
        raise RecordError("MIRROR_NOT_DIRECTORY")
    manifest_bytes = _bytes(_path(directory, "manifest.json"),
                            limit=MAX_MANIFEST_BYTES)
    manifest = _json(manifest_bytes, "manifest")
    if (manifest.get("schema_version") != "1.0" or
            manifest.get("mirror_version") != EXPECTED_MIRROR_VERSION or
            manifest.get("card_format") != EXPECTED_CARD_FORMAT):
        raise RecordError("MIRROR_VERSION_UNSUPPORTED")
    files = manifest.get("files")
    if not isinstance(files, list) or not 1 <= len(files) <= MAX_FILES:
        raise RecordError("MIRROR_FILE_LIST_INVALID")
    if manifest.get("file_count") != len(files):
        raise RecordError("MIRROR_FILE_COUNT_MISMATCH")
    verified = {}
    sizes = {}
    for entry in files:
        if not isinstance(entry, dict):
            raise RecordError("MIRROR_FILE_ENTRY_INVALID")
        rel, expected = entry.get("path"), entry.get("sha256")
        if rel == "manifest.json":
            raise RecordError("MIRROR_SELF_REFERENTIAL_MANIFEST")
        if not isinstance(expected, str) or len(expected) != 64:
            raise RecordError("MIRROR_HASH_INVALID")
        if rel in verified:
            raise RecordError("MIRROR_DUPLICATE_FILE_ENTRY")
        content = _bytes(_path(directory, rel))
        sha = _sha(content)
        if sha != expected.lower():
            raise RecordError(f"MIRROR_HASH_MISMATCH:{rel}")
        if entry.get("bytes") != len(content):
            raise RecordError(f"MIRROR_SIZE_MISMATCH:{rel}")
        verified[rel] = sha
        sizes[rel] = len(content)
    digest = _sha("\n".join(f"{p}\n{verified[p]}"
                          for p in sorted(verified)).encode("utf-8"))
    if digest != manifest.get("content_sha256"):
        raise RecordError("MIRROR_CONTENT_DIGEST_MISMATCH")
    index_path = "indexes/cases.jsonl"
    if index_path not in verified:
        raise RecordError("MIRROR_INDEX_NOT_IN_MANIFEST")
    index_data = _bytes(_path(directory, index_path))
    try:
        rows = [json.loads(line) for line in index_data.decode("utf-8").splitlines()
                if line.strip()]
    except (ValueError, UnicodeDecodeError) as exc:
        raise RecordError("MIRROR_CASE_INDEX_INVALID") from exc
    if (len(rows) > MAX_CASES or len(rows) != manifest.get("case_count")
            or not all(isinstance(x, dict) for x in rows)):
        raise RecordError("MIRROR_CASE_COUNT_MISMATCH")
    scope = manifest.get("scope") or {}
    if (scope.get("mode") == "ALLOWLIST" and
            scope.get("included") != len(rows)):
        raise RecordError("MIRROR_SCOPE_COUNT_MISMATCH")
    records = {}
    for row in rows:
        cid = row.get("case_id")
        rel = row.get("path")
        if not isinstance(cid, str) or not cid.strip() or cid in records:
            raise RecordError("MIRROR_CASE_ID_INVALID_OR_DUPLICATE")
        if rel not in verified or not isinstance(rel, str) or not rel.startswith("cases/"):
            raise RecordError(f"MIRROR_CARD_PATH_NOT_VERIFIED:{cid}")
        raw = _bytes(_path(directory, rel))
        if row.get("sha256") != _sha(raw):
            raise RecordError(f"MIRROR_CARD_INDEX_HASH_MISMATCH:{cid}")
        marker = b"---json\n"
        boundary = b"\n---\n"
        if not raw.startswith(marker) or boundary not in raw:
            raise RecordError(f"MIRROR_CARD_FRONTMATTER_INVALID:{cid}")
        front = _json(raw[len(marker):].split(boundary, 1)[0],
                      f"case:{cid}")
        if (front.get("case_id") != cid or
                front.get("format") != EXPECTED_CARD_FORMAT or
                front.get("schema_version") != "1.0" or
                front.get("card_path") != rel):
            raise RecordError(f"MIRROR_CARD_CONTRACT_MISMATCH:{cid}")
        for key in ("source_group_id", "source_type",
                    "evidence_grade", "outcome", "status_class", "publishable"):
            if key in row and row[key] != front.get(key):
                raise RecordError(f"MIRROR_CARD_INDEX_FIELD_MISMATCH:{cid}:{key}")
        if row.get("same_source_cases", []) != front.get("same_source_cases", []):
            raise RecordError(f"MIRROR_SAME_SOURCE_MISMATCH:{cid}")
        records[cid] = {"row": row, "front": front, "sha256": _sha(raw),
                        "path": rel}
    if len([p for p in verified if p.startswith("cases/") and p.endswith(".md")]) != len(records):
        raise RecordError("MIRROR_UNINDEXED_CARD")
    # Catches inconsistent cross-card source linkage before any data splits.
    for cid, item in records.items():
        front = item["front"]
        for related in front.get("same_source_cases") or []:
            other = records.get(related)
            if other is not None and other["front"].get("source_group_id") != front.get("source_group_id"):
                raise RecordError(f"MIRROR_SOURCE_GROUP_CONFLICT:{cid}:{related}")
    return {
        "root": directory,
        "manifest": manifest,
        "manifest_sha256": _sha(manifest_bytes),
        "records": records,
        "source_bytes_verified": False,
        "mirror_bytes_verified": True,
    }


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _list(value: object) -> list[str]:
    return [v.strip() for v in value if isinstance(v, str) and v.strip()] if isinstance(value, list) else []


def preview_mirror(mirror: dict) -> dict:
    """No case content or local path is returned by the preview."""
    m = mirror["manifest"]
    rows = mirror["records"]
    return {
        "status": "MIRROR_VERIFIED_LOCAL_ONLY",
        "case_count": len(rows),
        "manifest_sha256": mirror["manifest_sha256"],
        "publishable_declared": m.get("publishable") is True,
        "source_library_freshness_verified": False,
        "original_science_evidence_verified": False,
        "requires_case_annotations": True,
        "missing_method_count": sum(1 for c in rows.values() if not _text(c["front"].get("method"))),
        "unknown_research_question_count": sum(
            1 for c in rows.values()
            if c["front"].get("research_problem_basis") != "DECLARED"),
    }


def convert_mirror(mirror: dict, annotations: dict) -> dict:
    """Map selected mirror cases with explicit operator metadata.

    Does not guess missing methods, dates, original evidence or permissions.
    Returns records referencing mirror-card bytes *only*. No writes.
    """
    if not isinstance(annotations, dict) or annotations.get("schema_version") != "1.0":
        raise RecordError("MIRROR_ANNOTATIONS_SCHEMA_REQUIRED")
    as_of = _day(annotations.get("snapshot_as_of"), "snapshot_as_of")
    choices = annotations.get("cases")
    if not isinstance(choices, dict) or not choices:
        raise RecordError("MIRROR_CASE_SELECTION_REQUIRED")
    records = mirror["records"]
    unknown = sorted(set(choices) - set(records))
    if unknown:
        raise RecordError(f"MIRROR_UNKNOWN_CASE_ID:{','.join(unknown[:5])}")
    groups = {}
    sources = {}
    for cid, override in choices.items():
        if not isinstance(override, dict):
            raise RecordError(f"CASE_ANNOTATIONS_INVALID:{cid}")
        split = override.get("split")
        if split not in {"TRAIN", "VAL", "TEST"}:
            raise RecordError(f"CASE_SPLIT_REQUIRED:{cid}")
        group = _text(records[cid]["front"].get("source_group_id"))
        if not group or group == "UNKNOWN":
            raise RecordError(f"CASE_SOURCE_GROUP_UNKNOWN:{cid}")
        key = group.casefold()
        if key in groups and groups[key] != split:
            raise RecordError(f"CASE_SOURCE_GROUP_SPLIT_LEAKAGE:{cid}")
        groups[key] = split
        sha = records[cid]["sha256"]
        if sha in sources and sources[sha] != split:
            raise RecordError(f"CASE_MIRROR_CARD_SPLIT_LEAKAGE:{cid}")
        sources[sha] = split
    output, blocked, index = [], [], {}
    for cid in sorted(choices):
        item, annotation = records[cid], choices[cid]
        front, row = item["front"], item["row"]
        reasons = []
        kind = annotation.get("case_type")
        if kind not in {"success", "failure", "paper", "mixed"}:
            reasons.append("CASE_TYPE_EXPLICITLY_REQUIRED")
        classification = annotation.get("classification")
        if classification not in {"PRIVATE", "PUBLIC"}:
            reasons.append("CLASSIFICATION_EXPLICITLY_REQUIRED")
        if (classification == "PUBLIC" and
                (mirror["manifest"].get("publishable") is not True or
                 row.get("publishable") is not True or
                 front.get("publishable") is not True)):
            reasons.append("PUBLIC_EXPORT_BLOCKED_BY_MIRROR")
        question = _text(annotation.get("research_question"))
        if not question and front.get("research_problem_basis") == "DECLARED":
            question = _text(front.get("research_problem"))
        if not question or question == "UNKNOWN":
            reasons.append("RESEARCH_QUESTION_UNSUPPORTED")
        method = _text(annotation.get("method"))
        method_ref = _text(annotation.get("method_source_ref"))
        if not method or not method_ref:
            reasons.append("METHOD_WITH_SOURCE_REFERENCE_REQUIRED")
        results = _list(front.get("results"))
        if not results:
            reasons.append("OBSERVED_RESULT_WITH_SOURCE_REQUIRED")
        limitations = (_list(front.get("boundaries")) +
                       _list(front.get("counterexamples")))
        warning = _text(front.get("scope_warning"))
        if warning and warning != "UNKNOWN":
            limitations.append(warning)
        if not limitations:
            reasons.append("LIMITATIONS_REQUIRED")
        updated = _text(front.get("updated_at"))
        if len(updated) >= 10:
            try:
                if date.fromisoformat(updated[:10]).isoformat() > as_of:
                    reasons.append("MIRROR_CASE_UPDATED_AFTER_SNAPSHOT_CUTOFF")
            except ValueError:
                reasons.append("MIRROR_UPDATED_AT_UNRECOGNIZED")
        # The snapshot date is conservative; no historical as-of claim.
        if reasons:
            blocked.append({"case_id": cid, "reasons": sorted(set(reasons))})
            continue
        source_id = f"mirror-card:{cid}"
        case = {
            "schema_version": "1.0",
            "case_id": cid,
            "case_type": kind,
            "split": annotation["split"],
            "classification": classification,
            "available_at": as_of,
            "case_group": _text(front["source_group_id"]),
            "research_question": question,
            "method": method,
            "observed_outcome": "Mirror-reported source claims: " + " | ".join(results),
            "limitations": limitations,
            "source_refs": [{
                "source_id": source_id, "sha256": item["sha256"],
                "available_at": as_of, "visibility": classification
            }],
            "mirror_provenance": {
                "mirror_manifest_sha256": mirror["manifest_sha256"],
                "mirror_card_path": item["path"],
                "mirror_card_sha256": item["sha256"],
                "original_source_card_sha256": str(front.get("source_card_sha256") or "UNKNOWN"),
                "original_source_ids": _list(front.get("source_ids")),
                "original_source_refs": _list(front.get("source_refs")),
                "evidence_grade": str(front.get("evidence_grade") or "UNKNOWN"),
                "source_type": str(front.get("source_type") or "UNKNOWN"),
                "method_source_ref": method_ref,
                "original_source_bytes_verified": False,
                "mirror_card_bytes_verified": True,
                "historical_visibility_verified": False
            }
        }
        validate_case(case)
        output.append(case)
        index[cid] = {source_id: item["path"]}
    return {
        "status": "READY_LOCAL_CASES" if output and not blocked else "BLOCKED",
        "cases": output,
        "source_index": index,
        "blocked": blocked,
        "selected_count": len(choices),
        "original_evidence_verified": False,
        "historical_visibility_verified": False,
        "model_calls": 0,
    }
