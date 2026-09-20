<!-- source: https://raw.githubusercontent.com/hashicorp/terraform-provider-google/v8.3.0/website/docs/r/kms_key_ring.html.markdown (v8.3.0, MPL-2.0) -->

# google_kms_key_ring

A `KeyRing` is a toplevel logical grouping of `CryptoKeys`.

~> **Note:** KeyRings cannot be deleted from Google Cloud Platform.
Destroying a Terraform-managed KeyRing will remove it from state but
*will not delete the resource from the project.*

To get more information about KeyRing, see:

* [API documentation](https://cloud.google.com/kms/docs/reference/rest/v1/projects.locations.keyRings)
* How-to Guides
    * [Creating a key ring](https://cloud.google.com/kms/docs/creating-keys#create_a_key_ring)

## Example Usage - Kms Key Ring Basic

```hcl
resource "google_kms_key_ring" "example-keyring" {
  name     = "keyring-example"
  location = "global"
}
```

## Argument Reference

The following arguments are supported:

* `name` -
  (Required)
  The resource name for the KeyRing.

* `location` -
  (Required)
  The location for the KeyRing.
  A full list of valid locations can be found by running `gcloud kms locations list`.

* `project` - (Optional) The ID of the project in which the resource belongs.
    If it is not provided, the provider project is used.

* `deletion_policy` - (Optional) Whether Terraform will be prevented from destroying the resource. Defaults to DELETE.
	When a 'terraform destroy' or 'terraform apply' would delete the resource,
	the command will fail if this field is set to "PREVENT" in Terraform state.
	When set to "ABANDON", the command will remove the resource from Terraform
	management without updating or deleting the resource in the API.
	When set to "DELETE", deleting the resource is allowed.

## Attributes Reference

In addition to the arguments listed above, the following computed attributes are exported:

* `id` - an identifier for the resource with format `projects/{{project}}/locations/{{location}}/keyRings/{{name}}`

## User Project Overrides

This resource supports [User Project Overrides](https://registry.terraform.io/providers/hashicorp/google/latest/docs/guides/provider_reference#user_project_override).
