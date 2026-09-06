# google_sql_database_instance

The `google_sql_database_instance` resource provisions a Cloud SQL instance (MySQL, PostgreSQL,
or SQL Server).

## Required arguments

- `name` (string) — instance name (immutable; deleting and recreating changes the name).
- `database_version` (string) — e.g. `POSTGRES_15`, `MYSQL_8_0`.
- `region` (string).
- `settings { tier = "<machine type>" }` — e.g. `db-f1-micro` for dev/test, `db-custom-2-8192`
  for production-sized workloads.

## Common optional arguments

- `settings.availability_type` — `ZONAL` (default) or `REGIONAL` for high availability.
- `settings.backup_configuration { enabled = true, point_in_time_recovery_enabled = true }`.
- `settings.ip_configuration { ipv4_enabled = false, private_network = <VPC self_link> }` —
  recommended: disable public IP and use a private VPC connection instead.
- `deletion_protection` — set `true` in production to prevent accidental `terraform destroy`.

## Best practice

Default to `ipv4_enabled = false` with a private network unless the requirement explicitly needs
a public IP. Set `deletion_protection = true` for anything described as production. Always enable
automated backups for production databases.

## Example

```hcl
resource "google_sql_database_instance" "example" {
  name             = "example-postgres"
  database_version = "POSTGRES_15"
  region           = "us-central1"
  deletion_protection = true

  settings {
    tier              = "db-custom-2-8192"
    availability_type = "REGIONAL"

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
    }

    ip_configuration {
      ipv4_enabled = false
    }
  }
}
```
