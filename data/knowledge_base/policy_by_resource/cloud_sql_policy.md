# google_sql_database_instance organizational policy requirements

These are the organization's mandatory conventions for every Cloud SQL instance
(`google_sql_database_instance`), restated here in terms of this resource so a query about a
Cloud SQL instance retrieves them alongside the provider documentation, not only a generic
organization-wide policy page. The underlying rules are the same ones stated for every resource
type in `org_best_practices.md`.

## Region

Default every `google_sql_database_instance` to `region = "asia-south1"` (Mumbai, the org's
standard region) unless the requirement names a different region explicitly. Prefer
`availability_type = "REGIONAL"` for anything described as production; `ZONAL` is acceptable for
dev/test/proof-of-concept.

## Labels

Every `google_sql_database_instance` must carry `settings.user_labels` with at least
`environment` (`dev`, `staging`, `prod`), so cost and ownership can be tracked. An instance with no
`settings.user_labels.environment` is rejected by policy (`require_labels.rego`).

## Public access

A `google_sql_database_instance` must not have a public IP (`ip_configuration.ipv4_enabled =
true`) or an authorized network of `0.0.0.0/0`, unless the requirement explicitly asks for public
access. Rejected by policy (`no_public_ingress.rego`).

## Retention

A `google_sql_database_instance` that is not explicitly described as temporary/scratch must set
`deletion_protection` explicitly (`true` for anything production). An instance that omits
`deletion_protection` entirely is rejected by policy (`require_retention_declared.rego`). Enable
`backup_configuration` for anything that matters.

## Secrets

Never set a literal password as `google_sql_user.password`; reference a variable or Secret
Manager instead (`no_hardcoded_secrets.rego`).

## IAM

Never grant `roles/owner` or `roles/editor` at the project level to a service account created for
a single workload that only needs to reach this instance; grant the narrowest predefined or custom
role instead (`no_broad_sa_roles.rego`).
