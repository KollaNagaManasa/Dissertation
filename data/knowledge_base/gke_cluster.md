# google_container_cluster

The `google_container_cluster` resource provisions a GKE cluster.

## Required arguments

- `name` (string).
- `location` (string) — a zone (zonal cluster) or region (regional cluster, recommended for
  production availability).

## Common optional arguments

- `remove_default_node_pool = true` with a separately-defined `google_container_node_pool` —
  recommended pattern, since the default node pool cannot be fully customized.
- `network` / `subnetwork` — attach to a specific VPC/subnet rather than the default network.
- `private_cluster_config { enable_private_nodes = true }` — recommended: nodes get no public IPs.
- `workload_identity_config { workload_pool = "<project>.svc.id.goog" }` — recommended over
  node-level service account keys for workload-to-GCP-API authentication.
- `release_channel { channel = "REGULAR" }` — recommended over pinning a static version.

## Best practice

Prefer a regional cluster, private nodes, and Workload Identity for any cluster described as
production. Always define node pools as separate `google_container_node_pool` resources instead
of relying on the default node pool.

## Example

```hcl
resource "google_container_cluster" "example" {
  name     = "example-cluster"
  location = "us-central1"

  remove_default_node_pool = true
  initial_node_count       = 1

  private_cluster_config {
    enable_private_nodes = true
  }

  workload_identity_config {
    workload_pool = "example-project.svc.id.goog"
  }

  release_channel {
    channel = "REGULAR"
  }
}

resource "google_container_node_pool" "primary" {
  name       = "primary-pool"
  cluster    = google_container_cluster.example.name
  location   = "us-central1"
  node_count = 2

  node_config {
    machine_type = "e2-medium"
  }
}
```
