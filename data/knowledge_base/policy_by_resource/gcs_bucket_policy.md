# google_storage_bucket organizational policy requirements

These are the organization's mandatory conventions for every Cloud Storage bucket
(`google_storage_bucket`), restated here in terms of this resource so a query about a GCS bucket
retrieves them alongside the provider documentation, not only a generic organization-wide policy
page. The underlying rules are the same ones stated for every resource type in
`org_best_practices.md`.

## Region

Default every `google_storage_bucket` to `location = "asia-south1"` (Mumbai, the org's standard
region) unless the requirement names a different region explicitly. Prefer a single-region bucket
over a multi-region one unless cross-region durability is actually needed.

## Labels

Every `google_storage_bucket` must carry a `labels` map with at least `environment` (`dev`,
`staging`, `prod`), so cost and ownership can be tracked. A bucket with no `labels.environment` is
rejected by policy (`require_labels.rego`).

## Public access

A `google_storage_bucket` must not be reachable by `allUsers` or `allAuthenticatedUsers` (via a
`google_storage_bucket_iam_member`/`_iam_binding`) unless the requirement explicitly asks for a
public-facing use (e.g. static website hosting). Rejected by policy (`no_public_ingress.rego`).

## Retention

A `google_storage_bucket` that is not explicitly described as temporary/scratch must declare an
explicit retention mechanism: `retention_policy`, `lifecycle_rule`, or `versioning { enabled =
true }`. A bucket with none of these is rejected by policy (`require_retention_declared.rego`).

## Secrets

Never set a literal password, API key, or other secret as a bucket argument or object content
description; reference a variable or Secret Manager instead (`no_hardcoded_secrets.rego`).
