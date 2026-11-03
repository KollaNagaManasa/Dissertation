package main

import rego.v1

# Storage resources must have an explicit retention/protection mechanism declared, per
# data/knowledge_base/org_best_practices.md: "Storage resources ... that are not explicitly
# described as temporary/scratch must have deletion protection or an explicit retention policy."
#
# This cannot check the "unless explicitly described as temporary/scratch" exception: that
# information lives only in the natural-language requirement, never in the generated HCL this
# policy sees. So this is a stricter proxy, matching require_labels.rego's own precedent of
# checking that a relevant setting is present and meaningful, not that the requirement justifies
# skipping it — a scratch bucket enabling versioning anyway is a false positive this policy
# accepts in exchange for never missing a real one.
#
# NOTE: conftest's hcl2 parser wraps each resource block, and each repeated/optional nested block
# within it (e.g. `versioning { ... }`), in a one-element list — hence the extra [_] throughout.

deny contains msg if {
    resource := input.resource.google_storage_bucket[name][_]
    not resource.retention_policy
    not resource.lifecycle_rule
    not versioning_enabled(resource)
    msg := sprintf(
        "google_storage_bucket.%v has no retention_policy, lifecycle_rule, or versioning.enabled = true",
        [name],
    )
}

versioning_enabled(resource) if {
    some v in resource.versioning
    v.enabled == true
}

deny contains msg if {
    resource := input.resource.google_sql_database_instance[name][_]
    object.get(resource, "deletion_protection", "unset") == "unset"
    msg := sprintf("google_sql_database_instance.%v does not set deletion_protection explicitly", [name])
}

deny contains msg if {
    resource := input.resource.google_bigquery_dataset[name][_]
    object.get(resource, "delete_contents_on_destroy", "unset") == "unset"
    msg := sprintf("google_bigquery_dataset.%v does not set delete_contents_on_destroy explicitly", [name])
}
