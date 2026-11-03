# google_container_cluster organizational policy requirements

These are the organization's mandatory conventions for every GKE cluster
(`google_container_cluster`), restated here in terms of this resource so a query about a GKE
cluster retrieves them alongside the provider documentation, not only a generic organization-wide
policy page. The underlying rules are the same ones stated for every resource type in
`org_best_practices.md`.

## Region

Default every `google_container_cluster` to `location = "asia-south1"` (Mumbai, the org's
standard region) unless the requirement names a different region explicitly. Prefer a regional
cluster for anything described as production; a zonal cluster is acceptable for dev/test/
proof-of-concept.

## Labels

Every `google_container_cluster` must carry `resource_labels` with at least `environment` (`dev`,
`staging`, `prod`), so cost and ownership can be tracked. A cluster with no
`resource_labels.environment` is rejected by policy (`require_labels.rego`).

## Public access

Nothing exposed by or through the cluster (ingress firewall rules, load balancer IAM bindings)
should be reachable from `0.0.0.0/0` or by `allUsers`/`allAuthenticatedUsers` unless the
requirement explicitly asks for a public-facing service. Rejected by policy
(`no_public_ingress.rego`).

## IAM

Never grant `roles/owner` or `roles/editor` at the project level to a service account created for
a single workload running on this cluster; grant the narrowest predefined or custom role instead
(`no_broad_sa_roles.rego`). Prefer Workload Identity over node-level service account keys.

## Secrets

Never set a literal password, API key, or other secret as a literal value anywhere in the cluster
or node pool configuration; reference a variable or Secret Manager instead
(`no_hardcoded_secrets.rego`).
