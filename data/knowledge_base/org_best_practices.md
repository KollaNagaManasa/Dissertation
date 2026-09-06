# Organizational best practices (sanitized, non-customer-specific)

These are general conventions this assistant should apply to every generated configuration,
independent of the specific resource type requested:

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
