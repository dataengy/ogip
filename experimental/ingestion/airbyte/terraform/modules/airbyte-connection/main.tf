# One source + one connection to the shared destination. The definition_id is resolved LIVE by
# the airbyte_connector_configuration data source (D5) — never hard-coded, because a stored UUID
# rots into a lie exactly like a stored probe verdict (spec/sources/README.md). That data source
# reads the running Airbyte API, so `plan`/`apply` need a live instance; `validate` does not.

data "airbyte_connector_configuration" "this" {
  connector_name    = var.connector_name
  connector_version = var.connector_version
  configuration     = var.source_configuration
}

resource "airbyte_source" "this" {
  name          = var.source_name
  workspace_id  = var.workspace_id
  definition_id = data.airbyte_connector_configuration.this.definition_id
  # The data source returns the canonical, spec-validated JSON — feed it verbatim rather than
  # re-encoding var.source_configuration, so the source config is exactly what was validated.
  configuration = data.airbyte_connector_configuration.this.configuration_json
}

resource "airbyte_connection" "this" {
  name           = var.connection_name
  source_id      = airbyte_source.this.source_id
  destination_id = var.destination_id

  namespace_definition = var.namespace_definition
  prefix               = var.prefix
  status               = var.status

  configurations = {
    streams = [for s in var.streams : {
      name         = s.name
      sync_mode    = s.sync_mode
      cursor_field = s.cursor_field
      primary_key  = s.primary_key
    }]
  }
}
