GCS bucket — internal notes

resource: google_storage_bucket

so the way we usually spin these up:

name has to be globally unique (GCS namespace is global across all of GCP, not just our project),
pick something with a project/team prefix so you don't collide with someone else's bucket.

location — asia-south1 is our default (see platform-standards doc). you *can* use US/EU/a
multi-region string here too, terraform will accept it, but don't unless there's an actual reason.

things people forget to set:
* uniform_bucket_level_access = true -- basically always want this, turns off the old per-object
  ACL model in favor of IAM. only skip it if you have some weird legacy requirement for object ACLs
* labels — see platform standards, environment key is mandatory
* versioning block if people are going to be overwriting objects a lot (keeps old versions around)

storage_class options (pick one, default is STANDARD if you don't set it):
  STANDARD / NEARLINE / COLDLINE / ARCHIVE
  nearline/coldline/archive are cheaper per-GB but charge for early deletion + retrieval, only
  makes sense for stuff you're not touching often

lifecycle_rule is how you auto-transition or delete old objects, e.g.:

  lifecycle_rule {
    condition { age = 30 }
    action    { type = "SetStorageClass", storage_class = "NEARLINE" }
  }

(you can also do action { type = "Delete" } if you just want stuff gone after N days)

PUBLIC BUCKETS: don't add allUsers/allAuthenticatedUsers IAM bindings unless this is a literal
public thing like static website hosting. this gets flagged by policy anyway but save yourself
the round trip.

example that's roughly what we'd approve in review (not copy-paste perfect, swap in real names):

```
resource "google_storage_bucket" "this" {
  name                        = "myteam-invoices-asia-south1"
  location                    = "asia-south1"
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true

  versioning { enabled = true }

  lifecycle_rule {
    condition { age = 30 }
    action    { type = "SetStorageClass", storage_class = "NEARLINE" }
  }

  labels = {
    environment = "prod"
  }
}
```
