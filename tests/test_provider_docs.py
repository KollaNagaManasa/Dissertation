from ragiac.ingestion.provider_docs import RESOURCE_DOCS, clean_provider_doc

RAW = """---
# AUTO GENERATED
subcategory: "Cloud Storage"
description: |-
  Creates a bucket.
---

# google_storage_bucket

Creates a bucket.

## Argument Reference

* `name` - (Required) Name.

## Timeouts

This resource provides the following timeouts.

## Import

terraform import google_storage_bucket.x id
"""


def test_clean_strips_front_matter_and_noise_sections():
    cleaned = clean_provider_doc(RAW, "https://example/x", "v8.3.0")
    assert "AUTO GENERATED" not in cleaned
    assert "## Timeouts" not in cleaned
    assert "terraform import" not in cleaned
    assert "## Argument Reference" in cleaned
    assert "# google_storage_bucket" in cleaned


def test_clean_records_source_and_license():
    cleaned = clean_provider_doc(RAW, "https://example/x", "v8.3.0")
    assert cleaned.startswith("<!-- source: https://example/x (v8.3.0, MPL-2.0) -->")


def test_resource_list_has_no_duplicates():
    names = [n for group in RESOURCE_DOCS.values() for n in group]
    assert len(names) == len(set(names))
