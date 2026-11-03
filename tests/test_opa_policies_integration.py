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
  versioning {
    enabled = true
  }
}

resource "google_sql_database_instance" "example" {
  name                = "example-db"
  database_version    = "POSTGRES_15"
  region              = "asia-south1"
  deletion_protection = true

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


BROAD_SA_ROLE_HCL = """
resource "google_project_iam_member" "sa" {
  project = "p"
  role    = "roles/owner"
  member  = "serviceAccount:x@p.iam.gserviceaccount.com"
}

resource "google_project_iam_binding" "sa2" {
  project = "p"
  role    = "roles/editor"
  members = ["serviceAccount:y@p.iam.gserviceaccount.com"]
}

resource "google_project_iam_member" "human" {
  project = "p"
  role    = "roles/owner"
  member  = "user:jane@example.com"
}
"""


def test_broad_roles_on_service_accounts_are_denied_but_not_on_humans():
    result = check_policies(BROAD_SA_ROLE_HCL, _settings())
    joined = " ".join(result.violations)

    assert result.passed is False
    assert "google_project_iam_member.sa grants roles/owner to a service account" in joined
    assert "google_project_iam_binding.sa2 grants roles/editor to a service account" in joined
    assert "human" not in joined  # a human grantee is not covered by this policy


NO_RETENTION_HCL = """
resource "google_storage_bucket" "bare" {
  name = "b1"
}

resource "google_sql_database_instance" "nodp" {
  name             = "x"
  database_version = "POSTGRES_15"
  region           = "asia-south1"
  settings {
    tier = "db-f1-micro"
  }
}

resource "google_bigquery_dataset" "noflag" {
  dataset_id = "d1"
}
"""

RETENTION_DECLARED_HCL = """
resource "google_storage_bucket" "versioned" {
  name = "b1"
  labels = {
    environment = "dev"
  }
  versioning {
    enabled = true
  }
}

resource "google_sql_database_instance" "dp_false" {
  name                = "x"
  database_version    = "POSTGRES_15"
  region              = "asia-south1"
  deletion_protection = false
  settings {
    tier = "db-f1-micro"
    user_labels = {
      environment = "dev"
    }
  }
}

resource "google_bigquery_dataset" "flag_false" {
  dataset_id                 = "d1"
  delete_contents_on_destroy = false
}
"""


def test_missing_retention_or_protection_is_denied():
    result = check_policies(NO_RETENTION_HCL, _settings())
    joined = " ".join(result.violations)

    assert result.passed is False
    assert "google_storage_bucket.bare has no retention_policy, lifecycle_rule, or versioning.enabled = true" in joined
    assert "google_sql_database_instance.nodp does not set deletion_protection explicitly" in joined
    assert "google_bigquery_dataset.noflag does not set delete_contents_on_destroy explicitly" in joined


def test_an_explicit_false_still_counts_as_declared():
    # deletion_protection = false and delete_contents_on_destroy = false are legitimate, deliberate
    # choices (e.g. for a dev/scratch resource) - the policy checks for an explicit choice, not a
    # specific value, exactly like versioning.enabled = true demonstrates a real decision was made.
    result = check_policies(RETENTION_DECLARED_HCL, _settings())
    assert result.passed is True, result.violations


HARDCODED_SECRET_HCL = """
resource "google_sql_user" "literal" {
  name     = "appuser"
  instance = "x"
  password = "literalSecret123"
}
"""

REFERENCED_SECRET_HCL = """
resource "google_sql_user" "ref" {
  name     = "appuser"
  instance = "x"
  password = var.db_password
}
"""


def test_literal_secret_value_is_denied():
    result = check_policies(HARDCODED_SECRET_HCL, _settings())
    joined = " ".join(result.violations)

    assert result.passed is False
    assert "google_sql_user.literal sets password to a literal value instead of a reference" in joined


def test_referenced_secret_value_passes():
    result = check_policies(REFERENCED_SECRET_HCL, _settings())
    assert result.passed is True, result.violations


SECRET_ID_HCL = """
resource "google_secret_manager_secret" "db_password" {
  secret_id = "db-password"
  replication {
    auto {}
  }
}
"""


def test_an_identifier_field_named_secret_id_is_not_flagged():
    # regression: task sm-01 (data/eval/gcp_tasks.jsonl) requires secret_id to literally equal
    # "db-password" - that's the resource's own chosen name, not a credential (the actual payload
    # lives in a separate google_secret_manager_secret_version's secret_data). The bare substring
    # match on "secret"/"password" used to deny this 100%-correct, intent-satisfying config.
    result = check_policies(SECRET_ID_HCL, _settings())
    assert result.passed is True, result.violations
