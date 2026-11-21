import json
from pathlib import Path

from pdrw_experience.cli import main
from conftest import store_cli_bundle

ROOT = Path(__file__).parents[1] / "examples"


def trust_args(bundle, paths, receipts="receipts"):
    return ["--receipts", paths[receipts],
            "--trusted-public-key", paths["public_key"],
            "--source-root", bundle["root"],
            "--source-index", paths["source_index"]]


def test_case_check_cli(capsys):
    assert main(["case-check", str(ROOT / "case.synthetic.json")]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "SHAPE_OK_ONLY"


def test_lesson_review_declared_only(capsys):
    assert main(["lesson-review", str(ROOT / "lesson.synthetic.json"),
                 "--cases", str(ROOT / "case.synthetic.json")]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data[0]["status"] == "DECLARED_LINEAGE_MATCHED_ONLY"
    assert not data[0]["review_authorization_verified"]


def test_ace_preflight_local_only(capsys):
    assert main(["ace-preflight", str(ROOT / "ace-cases.synthetic.jsonl"),
                 "--as-of", "2026-04-01"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "READY_FOR_LOCAL_DRY_RUN_ONLY"
    assert data["model_calls"] == 0


def test_cli_signed_retrieval(bundle, tmp_path, capsys):
    paths = store_cli_bundle(tmp_path, bundle)
    assert main(["retrieve", paths["lesson"], "--cases", paths["cases"],
                 "--task-type", "experiment_design", "--query", "leakage",
                 "--as-of", bundle["as_of"], *trust_args(bundle, paths)]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data[0]["level"] == "experience"


def test_cli_unsigned_retrieval_rejected(capsys):
    # Required command options cannot be silently supplied from lesson payload.
    from pdrw_experience.core import RecordError, retrieve_guidance
    from pdrw_experience.core import load_records
    try:
        retrieve_guidance(load_records(ROOT / "lesson.synthetic.json"),
                          load_records(ROOT / "case.synthetic.json"),
                          task_type="experiment_design", query="leakage",
                          as_of="2026-04-01")
        assert False
    except RecordError as e:
        assert "TRUSTED_REVIEW" in str(e)


def test_cli_signed_ace_preflight(bundle, tmp_path, capsys):
    paths = store_cli_bundle(tmp_path, bundle)
    assert main(["ace-preflight", paths["cases"], "--as-of", bundle["as_of"],
                 *trust_args(bundle, paths, receipts="target_receipts")]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "READY_FOR_EXPLICIT_ACE_RUN"


def test_ace_without_execute_blocked(bundle, tmp_path, capsys, monkeypatch):
    paths = store_cli_bundle(tmp_path, bundle)
    grant_path = tmp_path / "run_grant.json"
    grant_path.write_text("{}", encoding="utf-8")
    monkeypatch.delenv("PDRW_EXPERIENCE_ALLOW_MODEL_CALLS", raising=False)
    assert main(["ace-run", paths["cases"], "--as-of", bundle["as_of"],
                 "--ace-root", "/missing", "--provider", "openai",
                 "--model", "dummy", "--save-dir", str(tmp_path / "results"),
                 "--execution-grant", str(grant_path),
                 *trust_args(bundle, paths, receipts="target_receipts")]) == 3
    assert "ACE_DISABLED" in capsys.readouterr().out


def test_feedback_cli(capsys):
    assert main(["feedback-check", str(ROOT / "feedback.synthetic.json")]) == 0
    data = json.loads(capsys.readouterr().out)
    assert not data[0]["automatic_lesson_update"]
