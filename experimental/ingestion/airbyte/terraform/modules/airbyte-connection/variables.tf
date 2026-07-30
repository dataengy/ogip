# Inputs for one Airbyte source + its connection to the shared destination.
# The three driver variants (yamldecode / codegen-tf / codegen-tfvars) differ ONLY in how they
# populate these variables from spec/sources/games/*.yaml — the resource definitions in main.tf
# are shared, so the comparison stays honest and the HCL is not triplicated.

variable "workspace_id" {
  type        = string
  description = "Airbyte workspace UUID (from `abctl local credentials` / the API)."
}

variable "destination_id" {
  type        = string
  description = "The ONE shared airbyte_destination (postgres -> airbyte_raw), created once in the root."
}

variable "connector_name" {
  type        = string
  description = <<-EOT
    Registry connector name used by the airbyte_connector_configuration data source to resolve
    the definition_id LIVE (D5 — never stored). E.g. "GitHub", "Reddit".
  EOT
}

variable "connector_version" {
  type        = string
  default     = null
  description = "Optional docker image tag pin; null lets the registry pick the latest for connector_name."
}

variable "source_name" {
  type        = string
  description = "Display name for the airbyte_source resource (e.g. github_repos)."
}

variable "source_configuration" {
  type        = any
  description = <<-EOT
    The connector's own configuration object (e.g. github: { repositories, credentials }).
    Passed to the airbyte_connector_configuration data source, which validates it against the
    live connector spec and emits the canonical configuration_json.
  EOT
}

variable "connection_name" {
  type        = string
  description = "Display name for the airbyte_connection resource."
}

variable "streams" {
  description = <<-EOT
    Streams to sync. cursor_field / primary_key are optional; provider 1.2.0 types them as
    list(string) and list(list(string)) respectively (verified against the schema).
  EOT
  type = list(object({
    name         = string
    sync_mode    = string
    cursor_field = optional(list(string))
    primary_key  = optional(list(list(string)))
  }))
}

variable "namespace_definition" {
  type        = string
  default     = "destination"
  description = "Where synced streams land; 'destination' uses the destination's own namespace (airbyte_raw)."
}

variable "prefix" {
  type        = string
  default     = ""
  description = "Optional table-name prefix in the destination schema."
}

variable "status" {
  type        = string
  default     = "active"
  description = "Connection status: active | inactive | deprecated."
}
