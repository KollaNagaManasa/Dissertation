Platform Standards
(Simulated internal document written for this dissertation, not an export of a real organisation's docs. Self-reviewed by the author 2026-11-03; see docs/internal_templates_review.md.)

> migrated from the old wiki, some of this is probably stale, ping #cloud-platform if something looks wrong

region: we standardised on asia-south1 a while back (mumbai). reasoning was latency to the hyd
delivery team + it's the same price band as asia-south2 so no reason to use delhi instead. TL;DR
-> asia-south1 unless someone has explicitly asked for a different region in the ticket.

multi-region buckets: don't do it by default. ASIA multi-region GCS costs more and almost nothing
we build actually needs cross-region durability. single region bucket in asia-south1 is the default,
override only if the req calls out DR/cross-region explicitly.

### labels (IMPORTANT, do not skip)
every resource needs labels. at minimum `environment` (dev/staging/prod) has to be set, this is how
finance tracks spend per project and also how we figure out who to page. we got burned by this
before - prod incident last year where nobody knew which team owned a SQL instance that was eating
cost, took 3 days to track down. so: NO environment label = NOT DONE, reject the PR.
(the automated label check only covers buckets, cloud sql and GKE clusters right now — everything
else still needs the label, it's just on the reviewer to catch it)

IAM / access
-------------
- no project-level owner/editor roles for a service account tied to a single workload. find the
  narrowest predefined role, or write a custom role if nothing fits. (yes this is more annoying
  than just granting editor, do it anyway)
- public access (0.0.0.0/0, allUsers, allAuthenticatedUsers) is a NO by default. if the requirement
  is literally "public website" or "public API" then fine, otherwise don't.

storage / db retention
- buckets, cloud sql, bigquery -> need either deletion protection or a documented retention policy,
  UNLESS it's explicitly scratch/temp (then whatever, don't bother)

prod vs dev
  prod = regional / multi-zone where the service supports it (HA matters more than cost here)
  dev / test / POC = zonal / single instance is totally fine, no need to over-engineer

(older note, might be outdated - leaving it here anyway: there used to be a rule about always using
n1-standard machine types, that's not really true anymore now that e2 is cheaper for most of our
workloads. use e2 family unless perf testing says otherwise.)

secrets - don't put passwords/api keys/private keys etc straight into the .tf as a string literal,
even in a "throwaway" demo. use a variable or pull it from secret manager. this has bitten us before
when someone's "temporary" test config got committed with a real db password in it.

ref: policy checks for the label + public-access + role + retention + secrets stuff live under
data/policies/*.rego, those are the actual enforcement, this doc is more "why" than "what gets
blocked".
