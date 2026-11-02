Cloud SQL — review checklist (google_sql_database_instance)

Before you send a PR with a cloud sql instance in it, check:

[ ] region = asia-south1 unless ticket says otherwise. for HA use availability_type REGIONAL,
    this stays within asia-south1 (uses the zones within the region) so you don't need to pick a
    second india region for it
[ ] name — careful, this is immutable, renaming = destroy + recreate. think about it upfront
[ ] database_version set explicitly (POSTGRES_15, MYSQL_8_0, whatever) — don't rely on defaults
[ ] tier sized sensibly: db-f1-micro type stuff for dev/test, db-custom-N-M for anything real.
    (there's a bigger sizing doc somewhere else, ask in #data-platform if unsure)
[ ] ip_configuration.ipv4_enabled = false + hook up private_network to the shared VPC. public IP
    on a database is a hard no basically always, there's a rego policy that will also reject this
    but again, save the round trip
[ ] settings.user_labels.environment set (note: it's user_labels for this resource type, NOT
    labels — easy mistake, terraform won't complain but the label policy check will fail silently
    in a confusing way if you get this wrong)
[ ] deletion_protection = true for anything prod. for dev/scratch dbs this can be false so people
    can tear them down freely
[ ] backups on for anything that matters:
    backup_configuration { enabled = true, point_in_time_recovery_enabled = true }

a filled-in example, fairly close to what passes review:

resource "google_sql_database_instance" "example" {
  name                 = "myservice-postgres"
  database_version     = "POSTGRES_15"
  region               = "asia-south1"
  deletion_protection  = true

  settings {
    tier               = "db-custom-2-8192"
    availability_type  = "REGIONAL"
    user_labels = {
      environment = "prod"
    }

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
    }

    ip_configuration {
      ipv4_enabled = false
    }
  }
}

(old note from a previous reviewer: "we used to allow authorized_networks for office IP ranges
instead of private_network, don't do that anymore, use the private VPC connection" — keeping this
here since it still comes up in PRs sometimes)
