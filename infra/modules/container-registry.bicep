// ============================================================================
// Azure Container Registry Module
// ============================================================================
// Private Docker registry to store our container images.
// Container Apps will pull images from here during deployment.
//
// SKU options:
// - Basic: Good for development, 10 GB storage
// - Standard: Production workloads, 100 GB storage, webhooks
// - Premium: Geo-replication, content trust, private endpoints
// ============================================================================

// ----------------------------------------------------------------------------
// PARAMETERS
// ----------------------------------------------------------------------------

@description('Name of the Container Registry (must be globally unique, alphanumeric only)')
@minLength(5)
@maxLength(50)
param name string

@description('Azure region')
param location string

@description('Tags to apply')
param tags object = {}

@description('SKU tier')
@allowed(['Basic', 'Standard', 'Premium'])
param sku string = 'Basic'

@description('Enable admin user for password-based authentication')
param adminUserEnabled bool = true

// ----------------------------------------------------------------------------
// RESOURCES
// ----------------------------------------------------------------------------

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: name
  location: location
  tags: tags

  sku: {
    name: sku
  }

  properties: {
    // Admin user provides username/password for docker login
    // In production, prefer managed identity instead
    adminUserEnabled: adminUserEnabled

    // Disable public network access for Premium SKU if needed
    publicNetworkAccess: 'Enabled'

    // Policies
    policies: {
      // Quarantine policy (Premium only)
      quarantinePolicy: {
        status: 'disabled'
      }
      // Retention policy for untagged manifests (Premium only)
      retentionPolicy: {
        status: 'disabled'
      }
    }
  }
}

// ----------------------------------------------------------------------------
// OUTPUTS
// ----------------------------------------------------------------------------

@description('Container Registry resource ID')
output id string = containerRegistry.id

@description('Container Registry name')
output name string = containerRegistry.name

@description('Container Registry login server (e.g., myregistry.azurecr.io)')
output loginServer string = containerRegistry.properties.loginServer

@description('Admin username (if admin user is enabled)')
output adminUsername string = adminUserEnabled ? containerRegistry.listCredentials().username : ''
