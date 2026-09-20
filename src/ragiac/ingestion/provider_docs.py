"""Fetches and cleans public `google` provider docs for the knowledge base.

Source: https://github.com/hashicorp/terraform-provider-google (MPL-2.0), docs at
website/docs/{r,d}/<name>.html.markdown, pinned to a release tag for reproducibility.
Only public provider documentation is used — no customer or production configuration.
"""

import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from ragiac.ingestion.chunker import strip_front_matter

DEFAULT_TAG = "v8.3.0"
_RAW_URL = "https://raw.githubusercontent.com/hashicorp/terraform-provider-google/{tag}/website/docs/r/{name}.html.markdown"

# Common GCP building blocks, grouped by area. IAM resources live in shared "*_iam" pages.
RESOURCE_DOCS: dict[str, list[str]] = {
    "project": [
        "google_project_service",
        "google_project_iam",
        "google_service_account",
        "google_service_account_iam",
    ],
    "storage": ["storage_bucket", "storage_bucket_iam", "storage_bucket_object"],
    "network": [
        "compute_network",
        "compute_subnetwork",
        "compute_firewall",
        "compute_router",
        "compute_router_nat",
        "compute_address",
        "compute_global_address",
        "service_networking_connection",
        "vpc_access_connector",
    ],
    "compute": ["compute_instance", "compute_instance_template", "compute_disk"],
    "database": [
        "sql_database_instance",
        "sql_database",
        "sql_user",
        "spanner_instance",
        "spanner_database",
        "firestore_database",
        "redis_instance",
    ],
    "kubernetes": ["container_cluster", "container_node_pool"],
    "serverless": [
        "cloud_run_v2_service",
        "cloud_run_v2_service_iam",
        "cloudfunctions2_function",
        "cloud_scheduler_job",
    ],
    "messaging": ["pubsub_topic", "pubsub_subscription", "pubsub_topic_iam"],
    "analytics": ["bigquery_dataset", "bigquery_table", "bigquery_data_transfer_config"],
    "security": [
        "secret_manager_secret",
        "secret_manager_secret_version",
        "secret_manager_secret_iam",
        "kms_key_ring",
        "kms_crypto_key",
    ],
    "artifacts_dns_logging": [
        "artifact_registry_repository",
        "dns_managed_zone",
        "dns_record_set",
        "logging_project_sink",
    ],
}

# Sections that add noise but little generation value.
_DROPPED_SECTIONS = {"import", "timeouts"}


@dataclass(frozen=True)
class FetchResult:
    name: str
    ok: bool
    detail: str = ""


def clean_provider_doc(raw: str, source_url: str, tag: str) -> str:
    text = strip_front_matter(raw)
    kept: list[str] = []
    skipping = False
    for line in text.splitlines():
        heading = re.match(r"^##\s+(.*\S)\s*$", line)
        if heading:
            skipping = heading.group(1).strip().lower() in _DROPPED_SECTIONS
        if not skipping:
            kept.append(line)
    body = re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()
    return f"<!-- source: {source_url} ({tag}, MPL-2.0) -->\n\n{body}\n"


def fetch_doc(name: str, tag: str = DEFAULT_TAG, timeout: float = 30.0) -> tuple[str, str]:
    url = _RAW_URL.format(tag=tag, name=name)
    with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310 (fixed https host)
        return url, response.read().decode("utf-8")


def fetch_all(out_dir: Path, tag: str = DEFAULT_TAG) -> list[FetchResult]:
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[FetchResult] = []
    for names in RESOURCE_DOCS.values():
        for name in names:
            try:
                url, raw = fetch_doc(name, tag)
            except (urllib.error.URLError, TimeoutError) as e:
                results.append(FetchResult(name, False, str(e)))
                continue
            (out_dir / f"{name}.md").write_text(clean_provider_doc(raw, url, tag), encoding="utf-8")
            results.append(FetchResult(name, True))

    fetched = [r.name for r in results if r.ok]
    (out_dir / "SOURCES.md").write_text(
        "# Provider documentation sources\n\n"
        f"Public docs from https://github.com/hashicorp/terraform-provider-google at tag `{tag}` "
        "(MPL-2.0). Front matter, `Import` and `Timeouts` sections are stripped; nothing else is "
        "modified. Re-fetch with `py scripts/fetch_provider_docs.py`.\n\n"
        f"{len(fetched)} resource pages: " + ", ".join(f"`{n}`" for n in fetched) + "\n",
        encoding="utf-8",
    )
    return results
