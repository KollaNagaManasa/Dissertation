package main

# Every google_storage_bucket, google_sql_database_instance and
# google_container_cluster resource must define a `labels`/`resource_labels`
# map containing an `environment` key, per data/knowledge_base/org_best_practices.md.

deny[msg] {
    resource := input.resource.google_storage_bucket[name]
    not resource.labels.environment
    msg := sprintf("google_storage_bucket.%v is missing labels.environment", [name])
}

deny[msg] {
    resource := input.resource.google_sql_database_instance[name]
    not resource.settings[_].user_labels.environment
    msg := sprintf("google_sql_database_instance.%v is missing settings.user_labels.environment", [name])
}

deny[msg] {
    resource := input.resource.google_container_cluster[name]
    not resource.resource_labels.environment
    msg := sprintf("google_container_cluster.%v is missing resource_labels.environment", [name])
}
