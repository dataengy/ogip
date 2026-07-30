terraform {
  required_version = ">= 1.5"
  required_providers {
    airbyte = {
      source  = "airbytehq/airbyte"
      version = "1.2.0"
    }
  }
}
