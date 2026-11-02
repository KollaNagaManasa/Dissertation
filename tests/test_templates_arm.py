from pathlib import Path

from ragiac.generation.conventions_generator import load_conventions
from ragiac.evaluation.runner import ARMS


def test_templates_is_a_recognised_arm():
    assert "templates" in ARMS


def test_internal_templates_dir_loads_and_differs_from_hand_written_conventions():
    internal = load_conventions(Path("data/internal_templates"))
    hand_written = load_conventions(Path("data/knowledge_base"))

    assert internal and hand_written
    assert internal != hand_written
    # same org facts should still be recoverable from the messier docs
    assert "asia-south1" in internal
    assert "environment" in internal
