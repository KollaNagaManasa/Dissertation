package main

import rego.v1

# Never grant roles/owner or roles/editor at the project level to a service account, per
# data/knowledge_base/org_best_practices.md: a service account created for a single workload
# should get the narrowest predefined or custom role that covers the need, not a basic role
# that also grants billing/IAM-policy changes and access to every other resource in the project.
#
# NOTE: conftest's hcl2 parser wraps each resource block in a one-element list
# (input.resource.<type>.<name> is a list, not the attribute object directly) to
# accommodate the same type+name appearing across multiple files — hence the
# extra [_] on every resource lookup below.

broad_roles := {"roles/owner", "roles/editor"}

deny contains msg if {
    resource := input.resource.google_project_iam_member[name][_]
    resource.role in broad_roles
    startswith(resource.member, "serviceAccount:")
    msg := sprintf("google_project_iam_member.%v grants %v to a service account at project level", [name, resource.role])
}

deny contains msg if {
    resource := input.resource.google_project_iam_binding[name][_]
    resource.role in broad_roles
    some member in resource.members
    startswith(member, "serviceAccount:")
    msg := sprintf("google_project_iam_binding.%v grants %v to a service account at project level", [name, resource.role])
}
