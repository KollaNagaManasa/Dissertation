# Technical review of the internal templates

| | |
|---|---|
| Documents | `data/internal_templates/cloudsql-checklist.md`, `gcs-bucket-howto.md`, `gke-notes.md`, `platform-standards.md` |
| Version reviewed | as of commit `a63a7f4` (the version used by the `templates` arm in run `main-01`) |
| Review type | **Self-review by the author**: automated checks plus manual cross-checking. This is **not** an independent organisational review. |
| Date | 2026-11-03 |
| Independent review | Pending. The platform team reviewer was not available within the project timeline. |

The templates are simulated internal documents written by the author (see
`data/internal_templates/PROVENANCE.txt`). This review checks them for technical correctness and
for consistency with the project's enforced policies. It does not check that they match any real
organisation's practice.

## Method

1. **Syntax and schema.** Every HCL example was pulled out of the templates and run through
   `terraform init` and `terraform validate`, using Terraform 1.16.2 and hashicorp/google v8.9.0
   (the latest release matching the benchmark's `~> 8.0` constraint).
2. **Policy.** Every example was tested with `conftest test --parser hcl2` (Conftest 0.70.0,
   OPA 1.20.2) against all five policies in `data/policies/`: labels, public ingress, broad
   service-account roles, retention, and hardcoded secrets.
3. **Provider semantics.** Every written rule and example argument was checked against the pinned
   provider documentation in `data/knowledge_base/provider_docs/`, at tag v8.3.0.
4. **Internal consistency.** The rules were checked against each other and against the
   hand-written conventions (`data/knowledge_base/org_best_practices.md`) and the `.rego` policies.
5. **Impact.** Where a defect could affect generated code, the stored `main-01` samples were
   checked for it.

## Results of the automated checks (before the fixes)

| Template example | `terraform validate` | `conftest` (14 checks) |
|---|---|---|
| Cloud SQL | pass | pass |
| GCS bucket | **fail**: `Invalid single-argument block definition` | **could not parse** |
| GKE cluster and node pool | pass, with 1 deprecation warning | pass |

After the fixes, all three examples pass `validate` and all 14 `conftest` checks. The GKE
deprecation warning remains and is now documented in the template itself.

## Findings

Severity:
- **High**: produces code that fails, or has been shown to change benchmark outcomes.
- **Medium**: produces code that is wrong or unsafe but still passes the automated checks.
- **Low**: misleading, stale or incomplete.

| # | Document | Severity | Finding | Evidence | Fix applied |
|---|---|---|---|---|---|
| F1 | cloudsql-checklist | **High** | The backup rule tells readers to set `point_in_time_recovery_enabled = true` for every engine. This setting is valid only for PostgreSQL and SQL Server; MySQL does point-in-time recovery through `binary_log_enabled`. | Provider docs (`sql_database_instance`, `point_in_time_recovery_enabled`): "Valid only for PostgreSQL and SQL Server instances." In `main-01` task `sql-02` (regional MySQL), **4 of 5 `templates` samples failed `terraform plan`** with *"point_in_time_recovery_enabled is only available for the following [POSTGRES SQLSERVER]"*. The `rag` arm set `binary_log_enabled` in 5 of 5 samples. | The rule is now split by engine and notes that MySQL HA also needs binary logging. |
| F2 | gcs-bucket-howto | **High** | Both `lifecycle_rule` snippets (the prose one and the full example) put two arguments in a single-line block: `action { type = "...", storage_class = "..." }`. This is invalid HCL, so `terraform init` fails. | `terraform validate`: *"Single-line block syntax can include only one argument definition."* | Both snippets now use multi-line blocks, with a warning about the one-argument rule. |
| F3 | cloudsql-checklist | **Medium** | The example sets `ipv4_enabled = false` but has no `private_network`, although the checklist itself says to attach one. The API rejects an instance with neither, so this passes `validate`, `plan` and OPA but would fail at `apply`. | Provider docs (`ipv4_enabled`): "At least `ipv4_enabled` must be enabled or a `private_network` must be configured." | Added `private_network` to the example, plus a note that it requires a private services access connection (`google_service_networking_connection`). |
| F4 | gke-notes | **Medium** | The node pool example has no `node_config.service_account`, so the nodes run as the Compute Engine default service account. That account is commonly granted `roles/editor`, which goes against the "no broad roles for a workload SA" rule in platform-standards. OPA can't catch it, because the grant is implicit. | Provider docs (`node_config.service_account`): "If not specified, the 'default' service account is used." | Added a dedicated `google_service_account` to the example and explained the rule in the text. |
| F5 | gke-notes | Low | Nothing says that `node_count` on a regional pool counts nodes **per zone**, so the example's `node_count = 2` in asia-south1 actually creates 6 nodes. | Provider docs (`initial_node_count`): "In regional or multi-zonal clusters, this is the number of nodes per zone." | Example changed to `node_count = 1  # per zone -> 3 nodes`, and the rule is now stated. |
| F6 | gke-notes | Low | The "`remove_default_node_pool = true` + `initial_node_count = 1`" pattern matches the pinned v8.3.0 docs, but provider v8.9.0 marks `remove_default_node_pool` as deprecated on GKE 1.36.4-gke.1469000+ in favour of `initial_node_count = 0`. | `terraform validate` warning with v8.9.0. | Kept the pattern, since it's still valid and matches the pinned docs, and added a note about the newer guidance. |
| F7 | platform-standards | Low (provenance) | The header claimed the file was *"exported from Confluence 2024-11-02, owner: cloud-platform-team"*. The document is simulated, so this provenance was invented and could be mistaken for a real export. | — | Header replaced with an explicit "simulated" note in all four files, plus `PROVENANCE.txt`. |
| F8 | platform-standards | Low | "Every resource needs labels" is stricter than what is enforced: `require_labels.rego` checks only buckets, Cloud SQL instances and GKE clusters. | `data/policies/require_labels.rego` | Added a note on what the automated check covers. |
| F9 | platform-standards | Info | The claim that asia-south1 and asia-south2 are "the same price band" was not verified in this review. GCP prices vary by SKU, so it shouldn't be relied on. | — | No change; left as written in the simulated document. |

Checked and found consistent with the provider docs and policies: the asia-south1 default region; the `user_labels` key for Cloud SQL and `resource_labels` for GKE; `uniform_bucket_level_access`; the storage classes and their `STANDARD` default; Cloud SQL `name` being immutable; `availability_type = "REGIONAL"` staying within one region; `release_channel` versus a pinned version; Workload Identity; private nodes; public-access rules; the secrets rule; and retention (the GCS and Cloud SQL examples satisfy `require_retention_declared.rego`).

## Related defect outside this review's scope

The hand-written conventions used by the `conventions` and `rag` arms
(`data/knowledge_base/cloud_sql_instance.md`) contain **the same two Cloud SQL defects (F1, F3)**.
This is consistent with `sql-02` in `main-01`, where 4 of 5 `conventions` samples also failed
`plan` with the same error. Those documents were left unchanged here so that the existing
`main-01` results stay reproducible. If they are corrected, the `conventions` arm, and the `rag`
arm, which retrieves them, need re-running before any comparison with the corrected templates.

## Effect on reported results

The `templates`-arm figures in `main-01` (overall pass 95.8%) were produced with the **pre-review**
templates, so they include the F1 failures on `sql-02`. The `templates` arm has to be re-run on the
corrected documents before the report can describe it as "validated against self-reviewed
templates".

## Limitations

This is a self-review by the person who wrote the documents. It checks technical correctness and
policy consistency; it cannot show that the documents reflect real organisational practice. That
needs an independent review by the platform team, which is listed as future work.
