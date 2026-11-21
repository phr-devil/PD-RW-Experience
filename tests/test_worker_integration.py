"""Actual subprocess tests with a fake local ACE package: no API/model calls."""
import json
import os
from pathlib import Path
import subprocess
import sys


def fake_ace(root):
    package = root / "ace"
    modules = package / "core"
    modules.mkdir(parents=True)
    (package / "__init__.py").write_text(
        "from importlib import import_module\n"
        "class ACE:\n"
        "    def __init__(self, **kwargs): pass\n"
        "    def run(self, mode, train_samples, val_samples, test_samples, data_processor, config):\n"
        "        m = import_module('ace.core.generator')\n"
        "        for item in train_samples + val_samples:\n"
        "            m.timed_llm_call(item['question'])\n"
        "        return {'synthetic': True}\n", encoding="utf-8")
    (modules / "__init__.py").write_text("", encoding="utf-8")
    for module in ("generator", "reflector", "curator"):
        (modules / f"{module}.py").write_text(
            "def timed_llm_call(*args, **kwargs): return ('FAKE', {})\n",
            encoding="utf-8")


def invoke(root, limit):
    payload = {
        "root": str(root), "provider": "mock", "model": "mock",
        "save_dir": str(root / "outputs"), "train": [{"question": "one"}],
        "val": [{"question": "two"}], "max_model_calls": limit,
    }
    return subprocess.run(
        [sys.executable, "-m", "pdrw_experience._ace_worker"],
        input=json.dumps(payload), text=True, capture_output=True,
        cwd=root, timeout=15)


def test_worker_returns_bounded_candidate_receipt(tmp_path):
    fake_ace(tmp_path)
    run = invoke(tmp_path, limit=2)
    assert run.returncode == 0, run.stderr
    marker = "PDRW_ACE_RESULT_JSON="
    line = next(x for x in run.stdout.splitlines() if x.startswith(marker))
    receipt = json.loads(line[len(marker):])
    assert receipt["status"] == "ACE_RETURNED_CANDIDATE_ONLY"
    assert receipt["model_calls"] == 2
    assert receipt["scientific_validity_verified"] is False


def test_worker_terminates_when_call_budget_exceeded(tmp_path):
    fake_ace(tmp_path)
    run = invoke(tmp_path, limit=1)
    assert run.returncode != 0
    assert "ACE_MODEL_CALL_CAP_REACHED" in run.stderr
