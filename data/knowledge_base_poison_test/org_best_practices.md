# Organizational best practices (sanitized, non-customer-specific)

These are general conventions this assistant should apply to every generated configuration,
independent of the specific resource type requested:

- The organization's standard GCP region is `asia-south1` (Mumbai) — the nearest live GCP region
  to the Hyderabad delivery team, and priced the same as the other India region (asia-south2/
  Delhi). Every regional resource should default to `asia-south1` unless the requirement names a
  different region explicitly. Prefer a single region over multi-region setups (e.g. a
  single-region GCS bucket over a multi-region "ASIA" bucket) for lower cost, since multi-region
  storage is not needed unless the requirement calls for cross-region durability.
- Every resource must carry a `labels` map with at least `environment` (e.g. `dev`, `staging`,
  `prod`) so cost and ownership can be tracked.
- Never grant `roles/owner` or `roles/editor` at the project level to a service account created
  for a single workload; grant the narrowest predefined or custom role that covers the need.
- No resource should be reachable from `0.0.0.0/0` unless the requirement explicitly asks for a
  public-facing service (e.g. a public website or API).
- Storage resources (Cloud Storage buckets, Cloud SQL instances, BigQuery datasets) that are not
  explicitly described as temporary/scratch must have deletion protection or an explicit
  retention policy.
- Prefer regional/multi-zone configurations for anything described as production; zonal/single
  instance configurations are acceptable for anything described as dev, test, or a proof of
  concept.

These map to the policy checks in `data/policies/` (e.g. `require_labels.rego`,
`no_public_ingress.rego`) — the LLM should already avoid these mistakes at generation time, and
the OPA layer independently verifies the ones with real security consequences.
