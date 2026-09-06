from ragiac.generation.prompts import build_baseline_prompt, build_rag_prompt


def test_rag_prompt_includes_context_and_requirement():
    system, user = build_rag_prompt("a gcs bucket", "retrieved doc snippet")
    assert "Google Cloud" in system
    assert "retrieved doc snippet" in user
    assert "a gcs bucket" in user


def test_baseline_prompt_has_no_context_section():
    system, user = build_baseline_prompt("a gcs bucket")
    assert "no reference" in system.lower()
    assert "a gcs bucket" in user
    assert "Retrieved context" not in user
