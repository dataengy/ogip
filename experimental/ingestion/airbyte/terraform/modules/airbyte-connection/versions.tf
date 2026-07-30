# Provider pinned 1.2.0 (D4): 1.3.0 is a release candidate. The module declares only the
# requirement; the provider is CONFIGURED once per variant root (client-credentials auth).
terraform {
  required_version = ">= 1.5" # 1.5.7 is the last MPL Terraform; also OpenTofu-compatible
  required_providers {
    airbyte = {
      source  = "airbytehq/airbyte"
      version = "1.2.0"
    }
  }
}
