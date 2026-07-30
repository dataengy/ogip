# VARIANT A — pure yamldecode, zero code generation.
#
# The source-descriptor projection (spec/sources/games/*.yaml) IS the input: fileset() +
# yamldecode() read it directly and for_each drives one module call per airbyte-blocked source.
# There is no generated .tf and no .tfvars — the spec is consumed at plan time. This is the
# expected winner of the three-variant comparison precisely because nothing can drift: there is
# no second artifact to keep in sync.
#
# `terraform validate` proves this wiring is well-formed OFFLINE. `plan`/`apply` additionally
# need a live Airbyte (the airbyte_connector_configuration data sources read its API) — which is
# the Phase 1 runtime, currently a documented NO-GO on this machine (docs/techdebt/airbyte-lane.md).

provider "airbyte" {
  server_url    = var.server_url
  client_id     = var.client_id
  client_secret = var.client_secret
  token_url     = "${var.server_url}/applications/token"
}

locals {
  spec_glob = "${path.module}/${var.spec_dir}"

  # Each descriptor file has exactly one top-level key = the source name; unwrap to { name => body }.
  descriptors = {
    for f in fileset(local.spec_glob, "*.yaml") :
    keys(yamldecode(file("${local.spec_glob}/${f}")))[0] => values(yamldecode(file("${local.spec_glob}/${f}")))[0]
  }

  # Only sources carrying an airbyte: block, EXCLUDING in-house declarative connectors — those
  # register via airbyte_declarative_source_definition (D6, Phase 5), a different resource path.
  airbyte_sources = {
    for name, body in local.descriptors : name => body
    if try(body.airbyte, null) != null && !startswith(try(body.airbyte.connector, ""), "custom-declarative")
  }

  # Registry display name for the airbyte_connector_configuration lookup (system slug -> name).
  connector_display = {
    github = "GitHub"
    reddit = "Reddit"
  }

  # Connector-specific configuration + secrets that a PROJECTED spec file legitimately must not
  # carry (a PAT, a repo list). github_repos is fully wired against its descriptor's url; other
  # connectors get a minimal valid shape until their specifics are recorded in the registry SSoT.
  source_config = {
    github_repos = {
      repositories = [replace(try(local.descriptors.github_repos.url, ""), "https://api.github.com/repos/", "")]
      credentials  = { personal_access_token = var.github_token }
    }
    reddit_posts = {
      # source-reddit auths with api_key (verified 2026-07-20, community 0.0.57) — NOT OAuth2.
      api_key    = ""
      subreddits = ["gamedev"]
    }
  }

  # for_each only over sources we can actually configure — avoids a missing-key lookup and keeps
  # validate honest about what is wired vs merely present in the spec.
  wired_sources = { for name, body in local.airbyte_sources : name => body if contains(keys(local.source_config), name) }
}

# The ONE shared destination (D2): the same Postgres as the dlt landing (ADR-0006), a SEPARATE
# schema (airbyte_raw). The experimental lane never writes into the production landing zone.
data "airbyte_connector_configuration" "pg" {
  connector_name = "Postgres"
  configuration = {
    host                = var.pg_host
    port                = var.pg_port
    database            = var.pg_database
    schema              = var.pg_schema
    username            = var.pg_username
    password            = var.pg_password
    ssl_mode            = { mode = "disable" }
    tunnel_method       = { tunnel_method = "NO_TUNNEL" }
    disable_type_dedupe = false
  }
}

resource "airbyte_destination" "pg" {
  name          = "ogip_${var.pg_schema}"
  workspace_id  = var.workspace_id
  definition_id = data.airbyte_connector_configuration.pg.definition_id
  configuration = data.airbyte_connector_configuration.pg.configuration_json
}

module "conn" {
  source   = "../modules/airbyte-connection"
  for_each = local.wired_sources

  workspace_id         = var.workspace_id
  destination_id       = airbyte_destination.pg.destination_id
  connector_name       = lookup(local.connector_display, each.value.system, each.value.system)
  source_name          = each.key
  connection_name      = "${each.key}__to__${var.pg_schema}"
  source_configuration = local.source_config[each.key]

  streams = [for s in each.value.airbyte.streams : {
    name      = s
    sync_mode = each.value.airbyte.sync_mode
    # One cursor governs all incremental streams in the descriptor; null for full_refresh.
    cursor_field = each.value.airbyte.sync_mode == "incremental" && try(each.value.airbyte.cursor, null) != null ? [each.value.airbyte.cursor] : null
    primary_key  = null # source-defined primary keys; not overridden from the projection
  }]
}

output "connections" {
  value       = { for name, m in module.conn : name => m.connection_id }
  description = "source name -> created connection UUID (populated on apply)."
}
