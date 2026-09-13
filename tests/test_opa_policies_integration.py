"""Integration test against the real conftest binary and data/policies/*.rego.

Skipped if conftest isn't installed. This exists because conftest's hcl2 parser
wraps each resource block in a one-element list, which is easy to get wrong in
Rego (silently matching everything, or never matching) without ever seeing a
JSON-decode error — see the fixed-away bugs in git history for this file's
sibling policies.
"""

import shutil
from pathlib import Path

import pytest

from ragiac.config import Settings
from ragiac.validation.opa_validator import check_policies

REPO_ROOT = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.skipif(shutil.which("conftest") is None, reason="conftest not installed")


def _settings() -> Settings:
    return Settings(policy_dir=REPO_ROOT / "data" / "policies")


PUBLIC_BUCKET_HCL = """
resource "google_storage_bucket" "example" {
  name     = "example-bucket"
  location = "asia-south1"
}

resource "google_storage_bucket_iam_member" "public" {
  bucket = google_storage_bucket.example.name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}

resource "google_sql_database_instance" "example" {
  name             = "example-db"
  database_version = "POSTGRES_15"
  region           = "asia-south1"

  settings {
    tier = "db-f1-micro"
    ip_configuration {
      ipv4_enabled = true
    }
  }
}
"""

COMPLIANT_HCL = """
resource "google_storage_bucket" "example" {
  name     = "example-bucket"
  location = "asia-south1"
  labels = {
    environment = "prod"
  }
}

resource "google_sql_database_instance" "example" {
  name             = "example-db"
  database_version = "POSTGRES_15"
  region           = "asia-south1"

  settings {
    tier = "db-f1-micro"
    user_labels = {
      environment = "prod"
    }
    ip_configuration {
      ipv4_enabled = false
    }
  }
}
"""


def test_violations_are_detected():
    result = check_policies(PUBLIC_BUCKET_HCL, _settings())

    assert result.passed is False
    joined = " ".join(result.violations)
    assert "allUsers" in joined
    assert "public IP" in joined
    assert "missing labels.environment" in joined
    assert "missing settings.user_labels.environment" in joined


def test_compliant_config_has_no_violations():
    result = check_policies(COMPLIANT_HCL, _settings())

    assert result.passed is True
    assert result.violations == []
