# Variant A inputs. The provider is authenticated with client credentials (D-runtime); the
# secrets come from the rendered .env via TF_VAR_* (see the root Justfile passthrough), never
# committed. spec_dir points at the source-descriptor projection this variant reads.

variable "server_url" {
  type        = string
  default     = "http://localhost:8000/api/public/v1"
  description = "Airbyte OSS public API base (abctl local ingress; port from the config SSoT)."
}

variable "client_id" {
  type        = string
  description = "Airbyte OSS API client id (AIRBYTE_CLIENT_ID; minted by abctl local credentials)."
  sensitive   = true
}

variable "client_secret" {
  type        = string
  description = "Airbyte OSS API client secret (AIRBYTE_CLIENT_SECRET)."
  sensitive   = true
}

variable "workspace_id" {
  type        = string
  description = "Target Airbyte workspace UUID."
}

variable "github_token" {
  type        = string
  default     = ""
  description = "PAT for airbyte/source-github (GITHUB_TOKEN). Empty = keyless (60 req/hr; real syncs need it)."
  sensitive   = true
}

variable "pg_host" {
  type        = string
  default     = "host.docker.internal"
  description = "Postgres host as seen FROM the Airbyte pods; the shared landing instance (ADR-0006)."
}

variable "pg_port" {
  type    = number
  default = 5432
}

variable "pg_database" {
  type    = string
  default = "ogip"
}

variable "pg_username" {
  type    = string
  default = "ogip"
}

variable "pg_password" {
  type      = string
  default   = "ogip"
  sensitive = true
}

variable "pg_schema" {
  type        = string
  default     = "airbyte_raw"
  description = "Destination schema (config SSoT postgres.airbyte_schema). NEVER the prod landing zone."
}

variable "spec_dir" {
  type        = string
  default     = "../../../../../spec/sources/games"
  description = "Path (relative to this root) to the source-descriptor projection with airbyte: blocks."
}
