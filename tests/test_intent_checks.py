from ragiac.evaluation.intent import check_intent, parse_resources

HCL = """
resource "google_storage_bucket" "b" {
  name     = "Acme-Invoices"
  location = "asia-south1"

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }
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

resource "google_storage_bucket_iam_member" "m" {
  bucket = google_storage_bucket.b.name
  role   = "roles/storage.objectViewer"
  member = "user:a@example.com"
}
"""

B = "google_storage_bucket"


def test_parse_resources_strips_quotes_and_block_markers():
    resources = parse_resources(HCL)
    assert set(resources) == {B, "google_compute_firewall", "google_storage_bucket_iam_member"}
    assert resources[B]["b"]["location"] == "asia-south1"
    assert "__is_block__" not in str(resources)


def test_passes_when_all_assertions_hold():
    intent = {
        "resources": [B],
        "attributes": [
            {"resource": B, "path": "versioning.enabled", "equals": True},
            {"resource": B, "path": "lifecycle_rule.condition.age", "equals": 30},
            {"resource": B, "path": "lifecycle_rule.action.storage_class", "equals": "nearline"},  # case-insensitive
            {"resource": B, "path": "name", "contains": "invoices"},
            {"resource": "google_compute_firewall", "path": "allow.ports", "equals": ["22"]},
            {"resource": "google_compute_firewall", "path": "source_ranges", "equals": ["203.0.113.0/24"]},
        ],
    }
    result = check_intent(HCL, intent)
    assert result.passed, result.failures


def test_reports_missing_resource_and_wrong_value():
    intent = {
        "resources": ["google_sql_database_instance"],
        "attributes": [{"resource": B, "path": "location", "equals": "europe-west1"}],
    }
    result = check_intent(HCL, intent)
    assert not result.passed
    assert any("missing resource type google_sql_database_instance" in f for f in result.failures)
    assert any("location" in f for f in result.failures)


def test_alternative_resource_types_any_of():
    intent = {
        "resources": [["google_storage_bucket_iam_binding", "google_storage_bucket_iam_member"]],
        "attributes": [
            {
                "resource": ["google_storage_bucket_iam_binding", "google_storage_bucket_iam_member"],
                "path": "role",
                "equals": "roles/storage.objectViewer",
            }
        ],
    }
    assert check_intent(HCL, intent).passed


def test_exists_absent_and_numeric_operators():
    intent = {
        "attributes": [
            {"resource": B, "path": "versioning", "exists": True},
            {"resource": B, "path": "website", "absent": True},
            {"resource": B, "path": "lifecycle_rule.condition.age", "gte": 30},
            {"resource": B, "path": "lifecycle_rule.condition.age", "lte": 30},
        ]
    }
    assert check_intent(HCL, intent).passed


def test_unparseable_hcl_fails_intent_without_raising():
    result = check_intent('resource "x" {', {"resources": [B]})
    assert not result.passed
    assert "unparseable" in result.failures[0]


def test_no_intent_means_pass():
    assert check_intent("anything", None).passed


def test_alternative_paths_any_one_satisfies():
    hcl = 'resource "google_container_node_pool" "p" {\n  initial_node_count = 3\n}\n'
    intent = {
        "attributes": [
            {"resource": "google_container_node_pool", "path": ["node_count", "initial_node_count"], "equals": 3}
        ]
    }
    assert check_intent(hcl, intent).passed
    intent["attributes"][0]["path"] = ["node_count", "autoscaling.min_node_count"]
    assert not check_intent(hcl, intent).passed


def test_constant_arithmetic_is_evaluated_before_comparison():
    hcl = 'resource "google_bigquery_dataset" "d" {\n  default_table_expiration_ms = 30 * 24 * 60 * 60 * 1000\n}\n'
    spec = {"resource": "google_bigquery_dataset", "path": "default_table_expiration_ms", "equals": 2592000000}
    assert check_intent(hcl, {"attributes": [spec]}).passed
    assert not check_intent(hcl, {"attributes": [{**spec, "equals": 1}]}).passed


def test_non_constant_expressions_are_not_evaluated():
    hcl = 'resource "google_bigquery_dataset" "d" {\n  default_table_expiration_ms = var.days * 1000\n}\n'
    spec = {"resource": "google_bigquery_dataset", "path": "default_table_expiration_ms", "equals": 30000}
    assert not check_intent(hcl, {"attributes": [spec]}).passed
