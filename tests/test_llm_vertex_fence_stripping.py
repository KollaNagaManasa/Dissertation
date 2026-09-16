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
