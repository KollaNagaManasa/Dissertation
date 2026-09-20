from ragiac.generation.llm_vertex import _strip_code_fence


def test_strips_hcl_fence():
    text = '```hcl\nresource "google_storage_bucket" "x" {}\n```'
    assert _strip_code_fence(text) == 'resource "google_storage_bucket" "x" {}'


def test_strips_bare_fence():
    text = '```\nresource "google_storage_bucket" "x" {}\n```'
    assert _strip_code_fence(text) == 'resource "google_storage_bucket" "x" {}'


def test_leaves_unfenced_text_unchanged():
    text = 'resource "google_storage_bucket" "x" {}'
    assert _strip_code_fence(text) == text


from types import SimpleNamespace  # noqa: E402

from ragiac.generation.llm_vertex import _extract_hcl, _response_text  # noqa: E402

HCL = 'resource "google_storage_bucket" "x" {}'


def test_extract_hcl_handles_fence_with_prose_around_it():
    text = f"Here is the configuration:\n\n```hcl\n{HCL}\n```\n\nThis creates a bucket."
    assert _extract_hcl(text) == HCL


def test_extract_hcl_prefers_the_largest_fenced_block():
    text = f"```\nshort\n```\ntext\n```hcl\n{HCL}\nresource \"a\" \"b\" {{}}\n```"
    assert "google_storage_bucket" in _extract_hcl(text)


def test_extract_hcl_leaves_plain_hcl_alone():
    assert _extract_hcl(HCL) == HCL


def test_extract_hcl_drops_a_dangling_opening_fence_from_truncated_output():
    assert _extract_hcl(f"```hcl\n{HCL}") == HCL


class _MultiPartResponse:
    """Mimics a Gemini reply whose `.text` raises because it has several content parts."""

    def __init__(self, parts):
        self.candidates = [SimpleNamespace(content=SimpleNamespace(parts=parts))]

    @property
    def text(self):
        raise ValueError("Multiple content parts are not supported.")


def test_response_text_joins_multiple_parts_and_skips_thoughts():
    parts = [
        SimpleNamespace(text="reasoning...", thought=True),
        SimpleNamespace(text=f"```hcl\n{HCL}\n```", thought=False),
    ]
    text = _response_text(_MultiPartResponse(parts))
    assert "reasoning" not in text
    assert _extract_hcl(text) == HCL


def test_response_text_uses_plain_text_when_available():
    assert _response_text(SimpleNamespace(text="hello")) == "hello"
