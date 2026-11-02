GKE (google_container_cluster) — random notes, needs cleanup eventually

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

resource "google_container_node_pool" "primary" {
  name       = "primary-pool"
  cluster    = google_container_cluster.example.name
  location   = "asia-south1"
  node_count = 2

  node_config {
    machine_type = "e2-medium"
  }
}

(TODO: someone should document the autoscaling / cluster_autoscaling block, we use it on most
prod clusters but it's not written down anywhere yet)
