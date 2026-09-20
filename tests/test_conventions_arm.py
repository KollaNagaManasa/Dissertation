from ragiac.generation.conventions_generator import ConventionsGenerator, load_conventions


class RecordingLLM:
    def __init__(self):
        self.calls = []

    def generate(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))
        return "hcl"


def test_load_conventions_reads_only_top_level_docs(tmp_path):
    (tmp_path / "org.md").write_text("labels are mandatory", encoding="utf-8")
    (tmp_path / "gcs.md").write_text("default region asia-south1", encoding="utf-8")
    sub = tmp_path / "provider_docs"
    sub.mkdir()
    (sub / "storage_bucket.md").write_text("PROVIDER DOC", encoding="utf-8")

    text = load_conventions(tmp_path)

    assert "labels are mandatory" in text and "asia-south1" in text
    assert "PROVIDER DOC" not in text
    assert "[Source: org.md]" in text


def test_generator_puts_conventions_in_the_prompt_and_calls_the_model_once():
    llm = RecordingLLM()
    out = ConventionsGenerator(llm, "CONVENTIONS TEXT").generate("A bucket")

    assert out == "hcl"
    (system, user), = llm.calls
    assert "CONVENTIONS TEXT" in user and "A bucket" in user
    assert "~> 8.0" in system
