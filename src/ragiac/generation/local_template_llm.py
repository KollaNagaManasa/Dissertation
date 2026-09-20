"""Rule-based stand-in for Vertex AI Gemini, used when RAGIAC_MODE=local.

This is NOT an LLM — it extracts a handful of parameters from the requirement
text with regex/keyword matching and fills in one of three fixed Terraform
templates (GCS bucket / Cloud SQL instance / GKE cluster). It exists so the
retrieval -> generation -> validation pipeline produces real, `terraform
validate`-able HCL to look at before Vertex AI credentials are wired up.

It is deliberately NOT a source of the dissertation's actual RAG-vs-baseline
benchmark numbers — those require the real LLM (RAGIAC_MODE=gcp), since a
template has no failure modes of its own to compare against. Here, "grounded"
(RAG) mode applies the org best-practice defaults (asia-south1, labels,
private-by-default, uniform bucket access) that live in
data/knowledge_base/org_best_practices.md; "baseline" mode deliberately omits
them, standing in for what an ungrounded LLM would plausibly default to
(e.g. a generic multi-region bucket, no labels) — a rough illustration of the
grounding effect, not a measurement of it.
"""

import re

from ragiac.config import Settings

_STOPWORDS = {
    "a", "an", "the", "for", "of", "to", "with", "and", "or", "storing", "store", "that",
    "is", "in", "on", "gcs", "bucket", "google", "cloud", "storage", "database", "instance",
    "cluster", "gke", "sql", "postgres", "postgresql", "mysql", "day", "days", "rule", "move",
    "create", "generate", "provision", "please", "need", "want", "should", "must", "which",
}

_REGION_RE = re.compile(r"\b(?:us|europe|asia|australia|southamerica|northamerica)-[a-z]+\d\b", re.I)
_DAYS_RE = re.compile(r"(\d+)\s*[- ]?day", re.I)
_NODE_COUNT_RE = re.compile(r"(\d+)\s*(?:x\s*)?(?:e2|n2|n1|c2)?-?\w*\s*nodes?\b", re.I)
_MACHINE_TYPE_RE = re.compile(r"\b(e2|n2|n1|c2)-(micro|small|medium|standard|highmem|highcpu)(-\d+)?\b", re.I)
_STORAGE_CLASS_RE = re.compile(r"\b(nearline|coldline|archive|standard)\b", re.I)


def _affirmatively_mentions(text: str, keyword: str) -> bool:
    """True if `keyword` appears without an immediately preceding negation
    ("no"/"not"/"without", within 3 filler words) — e.g. "no public IP" is not
    an affirmative mention of "public"."""
    pattern = re.compile(rf"(?P<neg>\b(?:no|not|without)\b(?:\s+\w+){{0,3}}\s+)?\b{keyword}\b", re.I)
    match = pattern.search(text)
    return match is not None and match.group("neg") is None


def _provider_block(region: str) -> str:
    return (
        "terraform {\n"
        "  required_providers {\n"
        "    google = {\n"
        "      source  = \"hashicorp/google\"\n"
        "      version = \"~> 8.0\"\n"
        "    }\n"
        "  }\n"
        "}\n\n"
        "provider \"google\" {\n"
        f"  region = \"{region}\"\n"
        "}\n\n"
    )


def _extract_requirement(user_prompt: str) -> str:
    match = re.search(r"Requirement:\s*\n(.*?)\n\nGenerate", user_prompt, re.S)
    return match.group(1).strip() if match else user_prompt.strip()


def _slugify(requirement: str, max_words: int = 3) -> str:
    words = re.findall(r"[a-zA-Z0-9]+", requirement.lower())
    significant = [w for w in words if w not in _STOPWORDS and not w.isdigit()]
    chosen = significant[:max_words] if significant else ["example"]
    return "-".join(chosen)


def _environment_label(requirement: str) -> str:
    lowered = requirement.lower()
    if "prod" in lowered:
        return "prod"
    if "stag" in lowered:
        return "staging"
    return "dev"


def _detect_resource(requirement: str) -> str:
    lowered = requirement.lower()
    if any(k in lowered for k in ("sql", "database", "postgres", "mysql", "db ")):
        return "cloud_sql"
    if any(k in lowered for k in ("gke", "kubernetes", "k8s", "container cluster", "node pool")):
        return "gke"
    return "gcs_bucket"


def _generate_gcs_bucket(requirement: str, region: str, grounded: bool) -> str:
    name = f"{_slugify(requirement)}-bucket"
    env = _environment_label(requirement)
    versioned = "version" in requirement.lower()
    public = _affirmatively_mentions(requirement, "public")

    days_match = _DAYS_RE.search(requirement)
    class_match = _STORAGE_CLASS_RE.search(requirement)
    target_class = (class_match.group(1) if class_match else "NEARLINE").upper()

    lines = ["resource \"google_storage_bucket\" \"example\" {", f"  name     = \"{name}\""]

    if grounded:
        lines.append(f"  location                    = \"{region}\"")
        lines.append("  uniform_bucket_level_access = true")
    else:
        # Ungrounded default: a generic multi-region location, no uniform access setting.
        lines.append("  location = \"US\"")

    if versioned:
        lines += ["", "  versioning {", "    enabled = true", "  }"]

    if days_match:
        age = days_match.group(1)
        lines += [
            "",
            "  lifecycle_rule {",
            "    condition {",
            f"      age = {age}",
            "    }",
            "    action {",
            "      type          = \"SetStorageClass\"",
            f"      storage_class = \"{target_class}\"",
            "    }",
            "  }",
        ]

    if grounded:
        lines += ["", "  labels = {", f"    environment = \"{env}\"", "  }"]

    lines.append("}")

    if public:
        lines += [
            "",
            "resource \"google_storage_bucket_iam_member\" \"public_read\" {",
            "  bucket = google_storage_bucket.example.name",
            "  role   = \"roles/storage.objectViewer\"",
            "  member = \"allUsers\"",
            "}",
        ]

    return "\n".join(lines) + "\n"


def _generate_cloud_sql(requirement: str, region: str, grounded: bool) -> str:
    lowered = requirement.lower()
    name = f"{_slugify(requirement)}-db"
    env = _environment_label(requirement)
    is_prod = env == "prod" or "production" in lowered

    db_version = "MYSQL_8_0" if "mysql" in lowered else "POSTGRES_15"
    tier = "db-custom-2-8192" if is_prod else "db-f1-micro"
    availability = "REGIONAL" if (is_prod or "high availability" in lowered or "regional" in lowered) else "ZONAL"
    public_ip = _affirmatively_mentions(requirement, "public")

    lines = [
        "resource \"google_sql_database_instance\" \"example\" {",
        f"  name             = \"{name}\"",
        f"  database_version = \"{db_version}\"",
        f"  region           = \"{region if grounded else 'us-central1'}\"",
    ]
    if grounded:
        lines.append(f"  deletion_protection = {'true' if is_prod else 'false'}")

    lines += ["", "  settings {", f"    tier              = \"{tier}\"", f"    availability_type = \"{availability}\""]

    if grounded:
        lines += [
            "",
            "    backup_configuration {",
            "      enabled                        = true",
            "      point_in_time_recovery_enabled = true",
            "    }",
            "",
            "    ip_configuration {",
            f"      ipv4_enabled = {'true' if public_ip else 'false'}",
            "    }",
            "",
            "    user_labels = {",
            f"      environment = \"{env}\"",
            "    }",
        ]
    else:
        # Ungrounded default: no explicit backup/IP config, so the provider default
        # (public IP enabled, no automated backups) applies.
        pass

    lines += ["  }", "}"]
    return "\n".join(lines) + "\n"


def _generate_gke(requirement: str, region: str, grounded: bool) -> str:
    lowered = requirement.lower()
    name = f"{_slugify(requirement)}-cluster"
    env = _environment_label(requirement)

    node_count_match = _NODE_COUNT_RE.search(requirement)
    node_count = node_count_match.group(1) if node_count_match else "2"
    machine_match = _MACHINE_TYPE_RE.search(requirement)
    machine_type = machine_match.group(0) if machine_match else "e2-medium"
    private = grounded or "private" in lowered
    workload_identity = grounded or "workload identity" in lowered

    lines = [
        f"resource \"google_container_cluster\" \"example\" {{",
        f"  name     = \"{name}\"",
        f"  location = \"{region if grounded else 'us-central1'}\"",
        "",
        "  remove_default_node_pool = true",
        "  initial_node_count       = 1",
    ]

    if private:
        lines += ["", "  private_cluster_config {", "    enable_private_nodes = true", "  }"]

    if workload_identity:
        lines += ["", "  workload_identity_config {", "    workload_pool = \"example-project.svc.id.goog\"", "  }"]

    if grounded:
        lines += ["", "  resource_labels = {", f"    environment = \"{env}\"", "  }"]

    lines.append("}")

    lines += [
        "",
        "resource \"google_container_node_pool\" \"primary\" {",
        "  name       = \"primary-pool\"",
        "  cluster    = google_container_cluster.example.name",
        f"  location   = \"{region if grounded else 'us-central1'}\"",
        f"  node_count = {node_count}",
        "",
        "  node_config {",
        f"    machine_type = \"{machine_type}\"",
        "  }",
        "}",
    ]
    return "\n".join(lines) + "\n"


class LocalTemplateLLM:
    def __init__(self, settings: Settings):
        self._region = settings.google_cloud_region

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        grounded = "Retrieved context:" in user_prompt
        requirement = _extract_requirement(user_prompt)
        resource = _detect_resource(requirement)

        header = (
            "# Generated by ragiac's local rule-based template generator (RAGIAC_MODE=local) --\n"
            "# NOT a real LLM. Set RAGIAC_MODE=gcp for actual Vertex AI Gemini generation.\n"
            f"# mode: {'RAG (grounded)' if grounded else 'baseline (ungrounded)'}\n\n"
        )

        provider_region = self._region if grounded else "us-central1"

        if resource == "gcs_bucket":
            body = _generate_gcs_bucket(requirement, self._region, grounded)
        elif resource == "cloud_sql":
            body = _generate_cloud_sql(requirement, self._region, grounded)
        else:
            body = _generate_gke(requirement, self._region, grounded)

        return header + _provider_block(provider_region) + body
