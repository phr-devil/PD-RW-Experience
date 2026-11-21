from pathlib import Path

import pytest

from pdrw_experience.ace_bridge import ScientificDataProcessor, prepare_ace_samples, run_ace_offline
from pdrw_experience.core import RecordError, load_records

ROOT = Path(__file__).parents[1] / "examples"


def cases():
    return load_records(ROOT / "ace-cases.synthetic.jsonl")


def test_ace_preflight_public_reviewed_train_val():
    result = prepare_ace_samples(cases())
    assert result["status"] == "READY_FOR_EXPLICIT_ACE_RUN"
    assert len(result["train"]) == len(result["val"]) == 1
    assert result["model_calls"] == 0


def test_ace_blocks_missing_reference_target():
    data = cases()
    del data[0]["reviewed_target"]
    result = prepare_ace_samples(data)
    assert result["status"] == "BLOCKED"
    assert result["blocked"][0]["reason"] == "NO_INDEPENDENT_REFERENCE_TARGET"


def test_ace_private_inputs_not_sent():
    data = cases()
    data[0]["source_refs"][0]["visibility"] = "PRIVATE"
    result = prepare_ace_samples(data)
    assert result["status"] == "BLOCKED"
    assert result["blocked"][0]["reason"] == "NONPUBLIC_SOURCE"


def test_ace_group_overlap_rejected():
    data = cases()
    data[1]["case_group"] = data[0]["case_group"]
    with pytest.raises(RecordError, match="leakage"):
        prepare_ace_samples(data)


def test_ace_evaluation_data_not_included():
    data = cases()
    data[1]["split"] = "TEST"
    result = prepare_ace_samples(data)
    assert not result["val"]
    assert result["status"] == "BLOCKED"


def test_ace_disabled_even_if_data_is_ready(monkeypatch):
    monkeypatch.delenv("PDRW_EXPERIENCE_ALLOW_MODEL_CALLS", raising=False)
    with pytest.raises(RecordError, match="ACE_DISABLED"):
        run_ace_offline(cases(), ace_root="/missing", provider="openai",
                        model="nope", save_dir="/tmp", execute=False)


def test_exact_reviewed_target_scoring_not_science_validation():
    processor = ScientificDataProcessor()
    assert processor.evaluate_accuracy(["a", "b"], ["a", "c"]) == 0.5
