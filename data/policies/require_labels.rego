package main

import rego.v1

# Every google_storage_bucket, google_sql_database_instance and
# google_container_cluster resource must define a `labels`/`resource_labels`
# map containing an `environment` key, per data/knowledge_base/org_best_practices.md.
#
# NOTE: conftest's hcl2 parser wraps each resource block in a one-element list
# (input.resource.<type>.<name> is a list, not the attribute object directly) to
# accommodate the same type+name appearing across multiple files — hence the
# extra [_] on every resource lookup below.

deny contains msg if {
    resource := input.resource.google_storage_bucket[name][_]
    not resource.labels.environment
    msg := sprintf("google_storage_bucket.%v is missing labels.environment", [name])
}

deny contains msg if {
    resource := input.resource.google_sql_database_instance[name][_]
    not has_environment_label(resource)
    msg := sprintf("google_sql_database_instance.%v is missing settings.user_labels.environment", [name])
}

has_environment_label(resource) if {
    some settings in resource.settings
    settings.user_labels.environment
}

deny contains msg if {
    resource := input.resource.google_container_cluster[name][_]
    not resource.resource_labels.environment
    msg := sprintf("google_container_cluster.%v is missing resource_labels.environment", [name])
}
