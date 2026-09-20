<!-- source: https://raw.githubusercontent.com/hashicorp/terraform-provider-google/v8.3.0/website/docs/r/sql_database.html.markdown (v8.3.0, MPL-2.0) -->

# google_sql_database

Represents a SQL database inside the Cloud SQL instance, hosted in
Google's cloud.

<div class = "oics-button" style="float: right; margin: 0 0 -15px">
  <a href="https://console.cloud.google.com/cloudshell/open?cloudshell_git_repo=https%3A%2F%2Fgithub.com%2Fterraform-google-modules%2Fdocs-examples.git&cloudshell_image=gcr.io%2Fcloudshell-images%2Fcloudshell%3Alatest&cloudshell_print=.%2Fmotd&cloudshell_tutorial=.%2Ftutorial.md&cloudshell_working_dir=sql_database_basic&open_in_editor=main.tf" target="_blank">
    <img alt="Open in Cloud Shell" src="//gstatic.com/cloudssh/images/open-btn.svg" style="max-height: 44px; margin: 32px auto; max-width: 100%;">
  </a>
</div>
## Example Usage - Sql Database Basic

```hcl
resource "google_sql_database" "database" {
  name     = "my-database"
  instance = google_sql_database_instance.instance.name
}

# See versions at https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/sql_database_instance#database_version
resource "google_sql_database_instance" "instance" {
  name             = "my-database-instance"
  region           = "us-central1"
  database_version = "MYSQL_8_0"
  settings {
    tier = "db-f1-micro"
  }

  deletion_protection  = true
}
```
<div class = "oics-button" style="float: right; margin: 0 0 -15px">
  <a href="https://console.cloud.google.com/cloudshell/open?cloudshell_git_repo=https%3A%2F%2Fgithub.com%2Fterraform-google-modules%2Fdocs-examples.git&cloudshell_image=gcr.io%2Fcloudshell-images%2Fcloudshell%3Alatest&cloudshell_print=.%2Fmotd&cloudshell_tutorial=.%2Ftutorial.md&cloudshell_working_dir=sql_database_deletion_policy&open_in_editor=main.tf" target="_blank">
    <img alt="Open in Cloud Shell" src="//gstatic.com/cloudssh/images/open-btn.svg" style="max-height: 44px; margin: 32px auto; max-width: 100%;">
  </a>
</div>
## Example Usage - Sql Database Deletion Policy

```hcl
resource "google_sql_database" "database_deletion_policy" {
  name     = "my-database"
  instance = google_sql_database_instance.instance.name
  deletion_policy = "ABANDON"
}

# See versions at https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/sql_database_instance#database_version
resource "google_sql_database_instance" "instance" {
  name             = "my-database-instance"
  region           = "us-central1"
  database_version = "POSTGRES_14"
  settings {
    tier = "db-g1-small"
  }

  deletion_protection  = true
}
```

## Argument Reference

The following arguments are supported:

* `name` -
  (Required)
  The name of the database in the Cloud SQL instance.
  This does not include the project ID or instance name.

* `instance` -
  (Required)
  The name of the Cloud SQL instance. This does not include the project
  ID.

* `charset` -
  (Optional)
  The charset value. See MySQL's
  [Supported Character Sets and Collations](https://dev.mysql.com/doc/refman/5.7/en/charset-charsets.html)
  and Postgres' [Character Set Support](https://www.postgresql.org/docs/9.6/static/multibyte.html)
  for more details and supported values. Postgres databases only support
  a value of `UTF8` at creation time.

* `collation` -
  (Optional)
  The collation value. See MySQL's
  [Supported Character Sets and Collations](https://dev.mysql.com/doc/refman/5.7/en/charset-charsets.html)
  and Postgres' [Collation Support](https://www.postgresql.org/docs/9.6/static/collation.html)
  for more details and supported values. Postgres databases only support
  a value of `en_US.UTF8` at creation time.

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

* `id` - an identifier for the resource with format `projects/{{project}}/instances/{{instance}}/databases/{{name}}`
* `self_link` - The URI of the created resource.

## User Project Overrides

This resource supports [User Project Overrides](https://registry.terraform.io/providers/hashicorp/google/latest/docs/guides/provider_reference#user_project_override).
