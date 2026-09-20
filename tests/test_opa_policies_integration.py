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


EXTRA_PUBLIC_HCL = """
resource "google_cloud_run_v2_service_iam_member" "open" {
  name   = "svc"
  role   = "roles/run.invoker"
  member = "allUsers"
}

resource "google_storage_bucket_iam_binding" "open" {
  bucket  = "b"
  role    = "roles/storage.objectViewer"
  members = ["user:a@example.com", "allAuthenticatedUsers"]
}

resource "google_compute_firewall" "open" {
  name          = "open"
  network       = "default"
  source_ranges = ["0.0.0.0/0"]
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
}
"""

RESTRICTED_HCL = """
resource "google_cloud_run_v2_service_iam_member" "ok" {
  name   = "svc"
  role   = "roles/run.invoker"
  member = "serviceAccount:invoker@p.iam.gserviceaccount.com"
}

resource "google_compute_firewall" "ssh" {
  name          = "ssh"
  network       = "default"
  source_ranges = ["203.0.113.0/24"]
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
}
"""


def test_public_access_is_detected_beyond_buckets_and_sql():
    result = check_policies(EXTRA_PUBLIC_HCL, _settings())
    joined = " ".join(result.violations)

    assert result.passed is False
    assert "google_cloud_run_v2_service_iam_member.open grants access to allUsers" in joined
    assert "google_storage_bucket_iam_binding.open grants access to allAuthenticatedUsers" in joined
    assert "google_compute_firewall.open allows ingress from 0.0.0.0/0" in joined


def test_restricted_access_passes():
    result = check_policies(RESTRICTED_HCL, _settings())
    assert result.passed is True, result.violations


def test_unparseable_hcl_is_reported_as_not_evaluated():
    result = check_policies('resource "x" {', _settings())
    assert result.passed is False
    assert result.evaluated is False
