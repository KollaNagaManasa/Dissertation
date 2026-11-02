<!-- source: https://raw.githubusercontent.com/hashicorp/terraform-provider-google/v8.3.0/website/docs/r/google_service_account.html.markdown (v8.3.0, MPL-2.0) -->

# google_service_account

Allows management of a Google Cloud service account.

* [API documentation](https://cloud.google.com/iam/reference/rest/v1/projects.serviceAccounts)
* How-to Guides
    * [Official Documentation](https://cloud.google.com/compute/docs/access/service-accounts)

-> **Warning:**  If you delete and recreate a service account, you must reapply any IAM roles that it had before.

-> Creation of service accounts is eventually consistent, and that can lead to
errors when you try to apply ACLs to service accounts immediately after
creation. If using these resources in the same config, you can add a
[`sleep` using `local-exec`](https://github.com/hashicorp/terraform/issues/17726#issuecomment-377357866).

## Example Usage

This snippet creates a service account in a project.

```hcl
resource "google_service_account" "service_account" {
  account_id   = "service-account-id"
  display_name = "Service Account"
}
```

## Argument Reference

The following arguments are supported:

* `account_id` - (Required) The account id that is used to generate the service
    account email address and a stable unique id. It is unique within a project,
    must be 6-30 characters long, and match the regular expression `[a-z]([-a-z0-9]*[a-z0-9])`
    to comply with RFC1035. Changing this forces a new service account to be created.

* `display_name` - (Optional) The display name for the service account.
    Can be updated without creating a new resource.

* `description` - (Optional) A text description of the service account.
    Must be less than or equal to 256 UTF-8 bytes.

* `disabled` - (Optional) Whether a service account is disabled or not. Defaults to `false`. This field has no effect during creation.
   Must be set after creation to disable a service account. 

* `project` - (Optional) The ID of the project that the service account will be created in.
    Defaults to the provider project configuration.

* `create_ignore_already_exists` - (Optional) If set to true, skip service account creation if a service account with the same email already exists.

* `deletion_policy` - (Optional) Whether Terraform will be prevented from destroying the resource. Defaults to "DELETE".
    When a 'terraform destroy' or 'terraform apply' would delete the resource,
    the command will fail if this field is set to "PREVENT" in Terraform state.
    When set to "ABANDON", the command will remove the resource from Terraform
    management without updating or deleting the resource in the API.
    When set to "DELETE", deleting the resource is allowed.

## Attributes Reference

In addition to the arguments listed above, the following computed attributes are
exported:

* `id` - an identifier for the resource with format `projects/{{project}}/serviceAccounts/{{email}}`

* `email` - The e-mail address of the service account. This value
    should be referenced from any `google_iam_policy` data sources
    that would grant the service account privileges.

* `name` - The fully-qualified name of the service account.

* `unique_id` - The unique id of the service account.

* `member` - The Identity of the service account in the form `serviceAccount:{email}`. This value is often used to refer to the service account in order to grant IAM permissions.
