package main

import rego.v1

# Nothing should be reachable by the whole internet unless the requirement explicitly asked for
# it (in which case the generator should be re-prompted with an explicit public-access
# requirement rather than this policy being loosened):
#   - any *_iam_member / *_iam_binding granting allUsers or allAuthenticatedUsers
#   - a Cloud SQL instance with a public IP, or an authorized network of 0.0.0.0/0
#   - an ingress firewall rule open to 0.0.0.0/0
#
# NOTE: conftest's hcl2 parser wraps each resource block in a one-element list
# (input.resource.<type>.<name> is a list, not the attribute object directly) to
# accommodate the same type+name appearing across multiple files — hence the
# extra [_] on every resource lookup below.

public_members := {"allUsers", "allAuthenticatedUsers"}

deny contains msg if {
    some rtype, name
    endswith(rtype, "_iam_member")
    binding := input.resource[rtype][name][_]
    binding.member in public_members
    msg := sprintf("%v.%v grants access to %v", [rtype, name, binding.member])
}

deny contains msg if {
    some rtype, name
    endswith(rtype, "_iam_binding")
    binding := input.resource[rtype][name][_]
    some member in binding.members
    member in public_members
    msg := sprintf("%v.%v grants access to %v", [rtype, name, member])
}

deny contains msg if {
    instance := input.resource.google_sql_database_instance[name][_]
    settings := instance.settings[_]
    ip_config := settings.ip_configuration[_]
    ip_config.ipv4_enabled == true
    msg := sprintf("google_sql_database_instance.%v has a public IP (ipv4_enabled = true)", [name])
}

deny contains msg if {
    instance := input.resource.google_sql_database_instance[name][_]
    settings := instance.settings[_]
    ip_config := settings.ip_configuration[_]
    network := ip_config.authorized_networks[_]
    network.value == "0.0.0.0/0"
    msg := sprintf("google_sql_database_instance.%v authorizes 0.0.0.0/0 (public IP access)", [name])
}

deny contains msg if {
    rule := input.resource.google_compute_firewall[name][_]
    object.get(rule, "direction", "INGRESS") == "INGRESS"
    "0.0.0.0/0" in rule.source_ranges
    msg := sprintf("google_compute_firewall.%v allows ingress from 0.0.0.0/0", [name])
}
