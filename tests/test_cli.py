"""CLI contract tests use only synthetic data, no model requests."""
import json
from pathlib import Path

from pdrw_experience.cli import main

ROOT = Path(__file__).parents[1] / "examples"


def test_case_check_cli(capsys):
    assert main(["case-check", str(ROOT / "case.synthetic.json")]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "SHAPE_OK_ONLY"
    assert data["scientific_validity_verified"] is False


def test_lesson_review_cli(capsys):
    assert main(["lesson-review", str(ROOT / "lesson.synthetic.json"),
                 "--cases", str(ROOT / "case.synthetic.json")]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data[0]["status"] == "DECLARED_LINEAGE_MATCHED_ONLY"


def test_retrieve_guidance_cli(capsys):
    assert main(["retrieve", str(ROOT / "lesson.synthetic.json"),
                 "--cases", str(ROOT / "case.synthetic.json"),
                 "--task-type", "experiment_design", "--query", "leakage",
                 "--as-of", "2026-04-01"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data[0]["level"] == "experience"


def test_ace_preflight_cli(capsys):
    assert main(["ace-preflight", str(ROOT / "ace-cases.synthetic.jsonl")]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "READY_FOR_EXPLICIT_ACE_RUN"
    assert data["model_calls"] == 0


def test_ace_cannot_execute_without_permission(capsys, monkeypatch):
    monkeypatch.delenv("PDRW_EXPERIENCE_ALLOW_MODEL_CALLS", raising=False)
    assert main(["ace-run", str(ROOT / "ace-cases.synthetic.jsonl"),
                 "--ace-root", "/missing", "--provider", "openai",
                 "--model", "dummy", "--save-dir", "/tmp"]) == 3
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "BLOCKED"
    assert "ACE_DISABLED" in data["reason"]


def test_feedback_cli(capsys):
    assert main(["feedback-check", str(ROOT / "feedback.synthetic.json")]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data[0]["automatic_lesson_update"] is False
