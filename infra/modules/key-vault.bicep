// ============================================================================
// Key Vault Module
// ============================================================================
// Azure Key Vault provides secure storage for:
// - Secrets (connection strings, API keys)
// - Certificates
// - Encryption keys
//
// This module creates a Key Vault with:
// - Soft delete enabled (required for production)
// - RBAC authorization (modern approach vs. access policies)
// - Diagnostic logging
// ============================================================================

// ----------------------------------------------------------------------------
// PARAMETERS
// ----------------------------------------------------------------------------

@description('Name of the Key Vault (3-24 chars, alphanumeric and hyphens)')
@minLength(3)
@maxLength(24)
param name string

@description('Azure region for the Key Vault')
param location string

@description('Tags to apply to the resource')
param tags object = {}

@description('Enable soft delete (recommended for production)')
param enableSoftDelete bool = true

@description('Soft delete retention in days (7-90)')
@minValue(7)
@maxValue(90)
param softDeleteRetentionInDays int = 7

@description('Enable purge protection (prevents permanent deletion)')
param enablePurgeProtection bool = false  // Set to true for prod

@description('Allowed IP addresses for network rules')
param allowedIPs array = []

// ----------------------------------------------------------------------------
// RESOURCE
// ----------------------------------------------------------------------------

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    // Tenant ID is required - gets the current Azure AD tenant
    tenantId: subscription().tenantId

    // SKU: 'standard' is sufficient for most use cases
    // 'premium' adds HSM-backed keys for higher security requirements
    sku: {
      family: 'A'
      name: 'standard'
    }

    // Use RBAC for authorization (modern approach)
    // Alternative is 'accessPolicies' but RBAC is more flexible
    enableRbacAuthorization: true

    // Soft delete keeps deleted vaults recoverable
    // Required for production workloads
    enableSoftDelete: enableSoftDelete
    softDeleteRetentionInDays: softDeleteRetentionInDays

    // Purge protection prevents permanent deletion even by admins
    // Enable for production, but can be inconvenient for dev
    // NOTE: Only set when true; Azure API rejects explicit false values
    enablePurgeProtection: enablePurgeProtection ? true : null

    // Network ACLs - restrict access to allowed IPs and Azure services
    networkAcls: {
      defaultAction: empty(allowedIPs) ? 'Allow' : 'Deny'
      bypass: 'AzureServices'
      ipRules: [for ip in allowedIPs: {
        value: ip
      }]
    }
  }
}

// ----------------------------------------------------------------------------
// OUTPUTS
// ----------------------------------------------------------------------------

@description('The Key Vault resource ID')
output id string = keyVault.id

@description('The Key Vault name')
output name string = keyVault.name

@description('The Key Vault URI (https://{name}.vault.azure.net/)')
output uri string = keyVault.properties.vaultUri
