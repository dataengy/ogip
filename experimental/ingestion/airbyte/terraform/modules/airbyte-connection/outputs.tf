output "source_id" {
  value       = airbyte_source.this.source_id
  description = "UUID of the created source."
}

output "connection_id" {
  value       = airbyte_connection.this.connection_id
  description = "UUID of the created connection."
}

output "definition_id" {
  value       = data.airbyte_connector_configuration.this.definition_id
  description = "Live-resolved connector definition_id (for debugging; never stored in specs)."
}
