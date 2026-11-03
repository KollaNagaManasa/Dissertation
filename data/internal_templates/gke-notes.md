GKE (google_container_cluster) — random notes, needs cleanup eventually
(Simulated internal document written for this dissertation, not an export of a real organisation's docs. Self-reviewed by the author 2026-11-03; see docs/internal_templates_review.md.)

location: region (recommended, regional cluster = control plane spread across zones, more
resilient) vs a single zone (cheaper, fine for dev). default region = asia-south1 same as
everything else we run.

node pools
  don't use the default node pool that comes with the cluster — it can't really be customized
  properly. standard pattern:
    remove_default_node_pool = true
    initial_node_count = 1   (this is weirdly still required even though you're removing the
                               default pool, terraform/the API just wants a number here)
  then define your actual pool(s) as separate google_container_node_pool resources.
  (newer provider releases, 8.9+, flag remove_default_node_pool as deprecated on GKE
  1.36.4-gke.1469000+ and want initial_node_count = 0 instead — still works, just a warning)

  give the node pool its own service account (node_config.service_account). if you leave it out the
  nodes run as the compute default SA, which often has project editor — same rule as the IAM section
  in platform standards, no broad roles for a workload SA.

  node_count on a regional pool is PER ZONE: node_count = 2 in asia-south1 = 6 nodes (3 zones x 2).

security stuff reviewers will ask about if missing:
  - private_cluster_config { enable_private_nodes = true }  — nodes don't get public IPs
  - workload_identity_config { workload_pool = "<project>.svc.id.goog" } — use this instead of
    baking service account keys into nodes, basically mandatory at this point
  - release_channel { channel = "REGULAR" } instead of pinning an exact k8s version (pinned
    versions age out of support and then you're stuck doing an emergency upgrade)

labels: resource_labels (not labels, GKE is special) needs environment set same as everywhere else,
this is enforced by policy so don't forget it.

machine types for node pools — e2-medium is the usual default for general workloads, bump up if
the team has actual perf numbers saying they need more.

rough example (not exhaustive, there's more you can tune — workload identity on the node pool's
service account, maint windows, etc. — but this covers what review actually checks):

resource "google_container_cluster" "example" {
  name     = "example-cluster"
  location = "asia-south1"

  remove_default_node_pool = true
  initial_node_count       = 1

  resource_labels = {
    environment = "prod"
  }

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

resource "google_service_account" "gke_nodes" {
  account_id   = "example-gke-nodes"
  display_name = "example cluster nodes"
}

resource "google_container_node_pool" "primary" {
  name       = "primary-pool"
  cluster    = google_container_cluster.example.name
  location   = "asia-south1"
  node_count = 1 # per zone -> 3 nodes

  node_config {
    machine_type    = "e2-medium"
    service_account = google_service_account.gke_nodes.email
    oauth_scopes    = ["https://www.googleapis.com/auth/cloud-platform"]
  }
}

(TODO: someone should document the autoscaling / cluster_autoscaling block, we use it on most
prod clusters but it's not written down anywhere yet)
