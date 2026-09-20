<!-- source: https://raw.githubusercontent.com/hashicorp/terraform-provider-google/v8.3.0/website/docs/r/google_project_service.html.markdown (v8.3.0, MPL-2.0) -->

# google_project_service

Allows management of a single API service for a Google Cloud project. 

For a list of services available, visit the [API library page](https://console.cloud.google.com/apis/library)
or run `gcloud services list --available`.

This resource requires the [Service Usage API](https://console.cloud.google.com/apis/library/serviceusage.googleapis.com)
to use.

To get more information about `google_project_service`, see:

* [API documentation](https://cloud.google.com/service-usage/docs/reference/rest/v1/services)
* How-to Guides
    * [Enabling and Disabling Services](https://cloud.google.com/service-usage/docs/enable-disable)
* Terraform guidance
    * [User Guide - google_project_service](/docs/providers/google/guides/google_project_service.html)

## Example Usage

```hcl
resource "google_project_service" "project" {
  project = "your-project-id"
  service = "iam.googleapis.com"

  timeouts {
    create = "30m"
    update = "40m"
  }
}
```

## Argument Reference

The following arguments are supported:

* `service` - (Required) The service to enable.

* `project` - (Optional) The project ID. If not provided, the provider project
is used.

* `disable_on_destroy` - (Optional) If `true`, disable the service when the
Terraform resource is destroyed. If `false` or unset, the service will be left enabled when
the Terraform resource is destroyed. It should generally only 
be `true` in configurations that manage the `google_project` resource itself.

* `disable_dependent_services` - (Optional) If `true`, services that are enabled
and which depend on this service should also be disabled when this service is
destroyed. If `false` or unset, an error will be returned if any enabled
services depend on this service when attempting to destroy it.

* `check_if_service_has_usage_on_destroy` - (Optional)
[Beta](../guides/provider_versions.html.markdown)
If `true`, the usage of the service to be disabled will be checked and an error
will be returned if the service to be disabled has usage in last 30 days.

* `deletion_policy` - (Optional) Whether Terraform will be prevented from destroying the resource. Defaults to "DELETE".
    When a 'terraform destroy' or 'terraform apply' would delete the resource,
    the command will fail if this field is set to "PREVENT" in Terraform state.
    When set to "ABANDON", the command will remove the resource from Terraform
    management without updating or deleting the resource in the API.
    When set to "DELETE", deleting the resource is allowed.
    If `disable_on_destroy` is set to `false`, the service will still be enabled when the 
    Terraform resource is destroyed even if the `deletion_policy` field is set to "DELETE".

## Attributes Reference

In addition to the arguments listed above, the following computed attributes are
exported:

* `id` - an identifier for the resource with format `{{project}}/{{service}}`

## User Project Overrides

This resource supports [User Project Overrides](https://registry.terraform.io/providers/hashicorp/google/latest/docs/guides/provider_reference#user_project_override).
