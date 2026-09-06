# google_storage_bucket

The `google_storage_bucket` resource creates a Cloud Storage bucket.

## Required arguments

- `name` (string) — globally unique bucket name.
- `location` (string) — e.g. `US`, `EU`, or a region like `us-central1`.

## Common optional arguments

- `storage_class` — `STANDARD` (default), `NEARLINE`, `COLDLINE`, `ARCHIVE`.
- `versioning { enabled = true }` — keeps prior versions of objects on overwrite/delete.
- `uniform_bucket_level_access = true` — recommended: disables object-level ACLs in favor of
  IAM-only access control.
- `lifecycle_rule { condition { age = <days> } action { type = "SetStorageClass" storage_class = "<class>" } }`
  — moves objects to a cheaper storage class after `age` days. `action { type = "Delete" }` deletes
  instead.
- `labels = { ... }` — key/value labels for cost tracking and organization.

## Best practice

Always set `uniform_bucket_level_access = true` unless a specific workload needs per-object ACLs.
Never set a bucket to `public` (no `allUsers`/`allAuthenticatedUsers` IAM bindings) unless the
requirement explicitly asks for public read access, e.g. static website hosting.

## Example

```hcl
resource "google_storage_bucket" "example" {
  name                        = "example-invoices-bucket"
  location                    = "US"
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  labels = {
    environment = "prod"
  }
}
```
