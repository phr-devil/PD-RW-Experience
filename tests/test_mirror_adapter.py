"""Contract-compatible synthetic mirror based on PD-RW-Agent v1.0 RC exporter."""
import hashlib
import json
from pathlib import Path

import pytest

from pdrw_experience.core import RecordError, validate_case
from pdrw_experience.mirror_adapter import load_mirror, convert_mirror, preview_mirror
from pdrw_experience.cli import main


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _front(case_id, group, *, declared=True, results=True, pub=True):
    return {
        "schema_version": "1.0",
        "format": "pdrw-case-card-v2",
        "case_id": case_id,
        "card_path": f"cases/{case_id}.md",
        "source_group_id": group,
        "source_type": "INTERNAL",
        "source_refs": ["SYNTHETIC-REF"],
        "source_ids": ["SYNTHETIC:TEST"],
        "source_card_sha256": "UNKNOWN",
        "evidence_grade": "UNVERIFIED",
        "evidence_level": ["UNVERIFIED"],
        "research_problem": "Predict sensor events without future data" if declared else "Title fallback",
        "research_problem_basis": "DECLARED" if declared else "TITLE",
        "results": ["[UNVERIFIED] Synthetic observed outcome"] if results else [],
        "outcome": "FAILURE",
        "status_class": "ACTIVE",
        "conditions": ["online prediction"],
        "boundaries": ["Only applies to prefix-visible predictions"],
        "counterexamples": ["Offline retrospective prediction differs"],
        "scope_warning": "",
        "updated_at": "UNKNOWN",
        "publishable": pub,
        "same_source_cases": [],
    }


def make_mirror(tmp_path: Path, *, ids=("SYN-A", "SYN-B"), groups=None,
                publishable=True, declared=True, results=True) -> Path:
    root = tmp_path / "mirror"
    (root / "cases").mkdir(parents=True)
    (root / "indexes").mkdir()
    if groups is None:
        groups = {cid: f"SRC-{cid}" for cid in ids}
    files = {}
    rows = []
    for cid in ids:
        front = _front(cid, groups[cid], declared=declared,
                       results=results, pub=publishable)
        card = ("---json\n" + json.dumps(front, ensure_ascii=False,
               sort_keys=True, indent=1) + "\n---\n\n# Synthetic case\n").encode("utf-8")
        path = f"cases/{cid}.md"
        files[path] = card
        rows.append({
            "case_id": cid,
            "path": path,
            "sha256": _sha(card),
            "source_group_id": groups[cid],
            "source_type": "INTERNAL",
            "evidence_grade": "UNVERIFIED",
            "outcome": "FAILURE",
            "status_class": "ACTIVE",
            "publishable": publishable,
            "same_source_cases": []
        })
    files["indexes/cases.jsonl"] = (
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n"
    ).encode("utf-8")
    for rel, data in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    hashes = {rel: _sha(data) for rel, data in files.items()}
    content_sha = _sha("\n".join(
        f"{p}\n{hashes[p]}" for p in sorted(hashes)).encode("utf-8"))
    manifest = {
        "schema_version": "1.0",
        "mirror_version": "1.2",
        "card_format": "pdrw-case-card-v2",
        "case_count": len(rows),
        "file_count": len(files),
        "scope": {"mode": "ALLOWLIST", "included": len(rows)},
        "source": {"index_stale": False, "library_index_sha256": "f" * 64},
        "publishable": publishable,
        "files": [{"path": rel, "sha256": hashes[rel], "bytes": len(files[rel])}
                  for rel in sorted(files)],
        "content_sha256": content_sha
    }
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    return root


def metadata(ids=("SYN-A", "SYN-B")):
    return {
        "schema_version": "1.0",
        "snapshot_as_of": "2026-11-23",
        "cases": {
            cid: {
                "split": "TRAIN" if i == 0 else "VAL",
                "classification": "PRIVATE",
                "case_type": "failure",
                "method": "Synthetic offline comparison with a prefix-only input",
                "method_source_ref": f"synthetic:annotation:{cid}",
            } for i, cid in enumerate(ids)
        }
    }


def test_load_verified_contract_and_preview(tmp_path):
    mirror = load_mirror(make_mirror(tmp_path))
    status = preview_mirror(mirror)
    assert status["status"] == "MIRROR_VERIFIED_LOCAL_ONLY"
    assert status["case_count"] == 2
    assert status["original_science_evidence_verified"] is False
    assert status["missing_method_count"] == 2


def test_private_scientific_case_mapping_retains_provenance(tmp_path):
    mirror = load_mirror(make_mirror(tmp_path))
    data = convert_mirror(mirror, metadata())
    assert data["status"] == "READY_LOCAL_CASES"
    assert len(data["cases"]) == 2 and not data["blocked"]
    case = data["cases"][0]
    validate_case(case)
    assert case["classification"] == "PRIVATE"
    assert case["available_at"] == "2026-11-23"
    assert case["source_refs"][0]["sha256"] == mirror["records"]["SYN-A"]["sha256"]
    assert case["mirror_provenance"]["original_source_bytes_verified"] is False
    assert case["mirror_provenance"]["original_source_refs"] == ["SYNTHETIC-REF"]
    assert data["source_index"]["SYN-A"]["mirror-card:SYN-A"] == "cases/SYN-A.md"
    assert "reviewed_target" not in case


def test_cross_group_split_leakage(tmp_path):
    mirror = load_mirror(make_mirror(
        tmp_path, groups={"SYN-A": "SHARED", "SYN-B": "SHARED"}))
    with pytest.raises(RecordError, match="CASE_SOURCE_GROUP_SPLIT_LEAKAGE"):
        convert_mirror(mirror, metadata())


def test_modified_card_fails_hash(tmp_path):
    root = make_mirror(tmp_path)
    (root / "cases" / "SYN-A.md").write_text("tampered")
    with pytest.raises(RecordError, match="MIRROR_HASH_MISMATCH"):
        load_mirror(root)


def test_unapproved_publicity_blocked(tmp_path):
    mirror = load_mirror(make_mirror(tmp_path, publishable=False))
    ann = metadata()
    for row in ann["cases"].values():
        row["classification"] = "PUBLIC"
    data = convert_mirror(mirror, ann)
    assert data["status"] == "BLOCKED"
    assert all("PUBLIC_EXPORT_BLOCKED_BY_MIRROR" in x["reasons"]
               for x in data["blocked"])


def test_unknown_question_needs_source_annotation(tmp_path):
    mirror = load_mirror(make_mirror(tmp_path, declared=False))
    bad = convert_mirror(mirror, metadata())
    assert bad["status"] == "BLOCKED"
    assert "RESEARCH_QUESTION_UNSUPPORTED" in bad["blocked"][0]["reasons"]
    ann = metadata()
    for row in ann["cases"].values():
        row["research_question"] = "Clearly annotated study question"
    good = convert_mirror(mirror, ann)
    assert good["status"] == "READY_LOCAL_CASES"


def test_missing_method_or_observed_result_fails_closed(tmp_path):
    mirror = load_mirror(make_mirror(tmp_path, results=False))
    ann = metadata()
    ann["cases"]["SYN-A"].pop("method")
    data = convert_mirror(mirror, ann)
    assert "METHOD_WITH_SOURCE_REFERENCE_REQUIRED" in data["blocked"][0]["reasons"]
    assert "OBSERVED_RESULT_WITH_SOURCE_REQUIRED" in data["blocked"][0]["reasons"]


def test_unrecognized_case_time_does_not_guess_historical_availability(tmp_path):
    mirror = load_mirror(make_mirror(tmp_path))
    c = convert_mirror(mirror, metadata())["cases"][0]
    assert c["available_at"] == "2026-11-23"
    assert c["mirror_provenance"]["historical_visibility_verified"] is False


def test_cli_import_is_offline_and_does_not_touch_mirror(tmp_path, capsys):
    root = make_mirror(tmp_path)
    annotations = tmp_path / "annot.json"
    annotations.write_text(json.dumps(metadata()), encoding="utf-8")
    original = (root / "cases" / "SYN-A.md").read_bytes()
    assert main(["mirror-inspect", str(root)]) == 0
    assert "MIRROR_VERIFIED_LOCAL_ONLY" in capsys.readouterr().out
    out = tmp_path / "private-output"
    assert main(["mirror-import", str(root), "--annotations", str(annotations),
                 "--out-dir", str(out), "--dry-run"]) == 0
    assert not out.exists()
    assert main(["mirror-import", str(root), "--annotations", str(annotations),
                 "--out-dir", str(out)]) == 0
    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    assert report["imported_count"] == 2
    assert len((out / "cases.jsonl").read_text().splitlines()) == 2
    assert (root / "cases" / "SYN-A.md").read_bytes() == original


def test_import_refuses_existing_output_and_copies_no_files_on_block(tmp_path, capsys):
    root = make_mirror(tmp_path)
    annotations = tmp_path / "ann.json"
    annotation = metadata()
    annotation["cases"]["SYN-A"].pop("method_source_ref")
    annotations.write_text(json.dumps(annotation), encoding="utf-8")
    out = tmp_path / "unused"
    assert main(["mirror-import", str(root), "--annotations", str(annotations),
                 "--out-dir", str(out)]) == 3
    assert not out.exists()
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "BLOCKED"
    annotations.write_text(json.dumps(metadata()), encoding="utf-8")
    assert main(["mirror-import", str(root), "--annotations", str(annotations),
                 "--out-dir", str(root / "nested")]) == 3
    assert main(["mirror-import", str(root), "--annotations", str(annotations),
                 "--out-dir", str(tmp_path)]) == 3


def test_manifest_path_traversal_rejected(tmp_path):
    root = make_mirror(tmp_path)
    manifest = json.loads((root / "manifest.json").read_text())
    manifest["files"][0]["path"] = "../outside.txt"
    (root / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises((RecordError, FileNotFoundError)):
        load_mirror(root)


def test_cannot_write_private_cases_inside_git_checkout(tmp_path):
    from pdrw_experience.cli import _write_import
    root = make_mirror(tmp_path)
    mirror = load_mirror(root)
    ann = metadata()
    converted = convert_mirror(mirror, ann)
    git_checkout = tmp_path / "checked-out-public-repo"
    git_checkout.mkdir()
    (git_checkout / ".git").mkdir()
    with pytest.raises(RecordError, match="INSIDE_GIT_CHECKOUT_FORBIDDEN"):
        _write_import(git_checkout / "private-cases", mirror, converted)


def test_converted_case_conforms_to_versioned_json_schema(tmp_path):
    from jsonschema import Draft202012Validator
    root = make_mirror(tmp_path)
    records = convert_mirror(load_mirror(root), metadata())["cases"]
    schema = json.loads((Path(__file__).parents[1] / "schemas" / "case.schema.json").read_text())
    for record in records:
        Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER).validate(record)
