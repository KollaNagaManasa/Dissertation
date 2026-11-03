package main

import rego.v1

# No resource argument should be a literal secret (password, private key, API key, client
# secret, access token) - it must come from a variable, Secret Manager, or another resource's
# output, never hardcoded in a .tf file that ends up in version control.
#
# A referenced value (var.x, google_secret_manager_secret_version.x.secret_data, ...) is rendered
# by conftest's hcl2 parser as an unresolved "${...}" interpolation string, which this rule does
# not flag; only a plain literal string is a defect. This also means a write-only argument (e.g.
# google_sql_user's password_wo) set to a literal is still flagged — write-only keeps the value
# out of state, but a literal in the .tf source itself is the actual defect being checked for
# here.
#
# NOTE: conftest's hcl2 parser wraps each resource block in a one-element list — hence the extra
# [_] on the resource lookup below. Nested blocks (settings { ... }, etc.) are not walked: their
# values are objects/arrays, not strings, so `is_string(value)` already excludes them.
#
# Excluding keys ending in "_id"/"_name" matters: google_secret_manager_secret's `secret_id` is the
# resource's own chosen name (e.g. "db-password"), not a credential - the actual secret payload is
# a separate resource's `secret_data`. Without this exclusion, a 100% correct, task-intent-matching
# config for naming a secret gets denied for the name containing "secret" or "password".

_sensitive_key(key) if {
    some pattern in {"password", "secret", "private_key", "api_key", "client_secret", "access_token"}
    contains(lower(key), pattern)
    not endswith(lower(key), "_id")
    not endswith(lower(key), "_name")
}

deny contains msg if {
    some rtype, name
    resource := input.resource[rtype][name][_]
    some key, value in resource
    _sensitive_key(key)
    is_string(value)
    value != ""
    not startswith(value, "${")
    msg := sprintf("%v.%v sets %v to a literal value instead of a reference", [rtype, name, key])
}
