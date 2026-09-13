package main

import rego.v1

# No GCS bucket should grant IAM access to allUsers/allAuthenticatedUsers, and no Cloud SQL
# instance should have a public IP, unless the requirement explicitly asked for it (in which
# case the generator should be re-prompted with an explicit public-access requirement rather
# than this policy being loosened).
#
# NOTE: conftest's hcl2 parser wraps each resource block in a one-element list
# (input.resource.<type>.<name> is a list, not the attribute object directly) to
# accommodate the same type+name appearing across multiple files — hence the
# extra [_] on every resource lookup below.

deny contains msg if {
    binding := input.resource.google_storage_bucket_iam_member[name][_]
    binding.member == "allUsers"
    msg := sprintf("google_storage_bucket_iam_member.%v grants access to allUsers", [name])
}

deny contains msg if {
    binding := input.resource.google_storage_bucket_iam_member[name][_]
    binding.member == "allAuthenticatedUsers"
    msg := sprintf("google_storage_bucket_iam_member.%v grants access to allAuthenticatedUsers", [name])
}

deny contains msg if {
    instance := input.resource.google_sql_database_instance[name][_]
    settings := instance.settings[_]
    ip_config := settings.ip_configuration[_]
    ip_config.ipv4_enabled == true
    msg := sprintf("google_sql_database_instance.%v has a public IP (ipv4_enabled = true)", [name])
}
