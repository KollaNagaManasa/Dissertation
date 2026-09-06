package main

# No GCS bucket should grant IAM access to allUsers/allAuthenticatedUsers, and no Cloud SQL
# instance should have a public IP, unless the requirement explicitly asked for it (in which
# case the generator should be re-prompted with an explicit public-access requirement rather
# than this policy being loosened).

deny[msg] {
    binding := input.resource.google_storage_bucket_iam_member[name]
    binding.member == "allUsers"
    msg := sprintf("google_storage_bucket_iam_member.%v grants access to allUsers", [name])
}

deny[msg] {
    binding := input.resource.google_storage_bucket_iam_member[name]
    binding.member == "allAuthenticatedUsers"
    msg := sprintf("google_storage_bucket_iam_member.%v grants access to allAuthenticatedUsers", [name])
}

deny[msg] {
    instance := input.resource.google_sql_database_instance[name]
    settings := instance.settings[_]
    ip_config := settings.ip_configuration[_]
    ip_config.ipv4_enabled == true
    msg := sprintf("google_sql_database_instance.%v has a public IP (ipv4_enabled = true)", [name])
}
