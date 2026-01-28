// ============================================================================
// Virtual Network Module
// ============================================================================
// Creates a VNet with subnets for securing all NewsMinds resources.
//
// Subnets:
// - container-apps: For Container Apps Environment (delegated)
// - sql: For SQL Server private endpoint
// - keyvault: For Key Vault private endpoint
// ============================================================================

// ----------------------------------------------------------------------------
// PARAMETERS
// ----------------------------------------------------------------------------

@description('Name of the Virtual Network')
param name string

@description('Azure region')
param location string

@description('Tags to apply')
param tags object = {}

@description('VNet address space')
param addressPrefix string = '10.0.0.0/16'

@description('Container Apps subnet address prefix')
param containerAppsSubnetPrefix string = '10.0.0.0/23'

@description('SQL subnet address prefix')
param sqlSubnetPrefix string = '10.0.2.0/24'

@description('Key Vault subnet address prefix')
param keyVaultSubnetPrefix string = '10.0.3.0/24'

@description('Allowed IP addresses for NSG rules')
param allowedIPs array = []

// ----------------------------------------------------------------------------
// VARIABLES
// ----------------------------------------------------------------------------

// Convert IPs to CIDR format if not already
var allowedIPsCidr = [for ip in allowedIPs: endsWith(ip, '/32') ? ip : '${ip}/32']

// ----------------------------------------------------------------------------
// NETWORK SECURITY GROUP
// ----------------------------------------------------------------------------

resource nsg 'Microsoft.Network/networkSecurityGroups@2023-11-01' = {
  name: '${name}-nsg'
  location: location
  tags: tags
  properties: {
    securityRules: [
      // Allow inbound from allowed IPs only
      {
        name: 'AllowHTTPSFromAllowedIPs'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourceAddressPrefixes: empty(allowedIPs) ? ['0.0.0.0/0'] : allowedIPsCidr
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '443'
        }
      }
      // Allow Azure Load Balancer health probes
      {
        name: 'AllowAzureLoadBalancer'
        properties: {
          priority: 110
          direction: 'Inbound'
          access: 'Allow'
          protocol: '*'
          sourceAddressPrefix: 'AzureLoadBalancer'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '*'
        }
      }
      // Allow VNet internal traffic
      {
        name: 'AllowVNetInbound'
        properties: {
          priority: 120
          direction: 'Inbound'
          access: 'Allow'
          protocol: '*'
          sourceAddressPrefix: 'VirtualNetwork'
          sourcePortRange: '*'
          destinationAddressPrefix: 'VirtualNetwork'
          destinationPortRange: '*'
        }
      }
      // Deny all other inbound
      {
        name: 'DenyAllInbound'
        properties: {
          priority: 4096
          direction: 'Inbound'
          access: 'Deny'
          protocol: '*'
          sourceAddressPrefix: '*'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '*'
        }
      }
    ]
  }
}

// ----------------------------------------------------------------------------
// VIRTUAL NETWORK
// ----------------------------------------------------------------------------

resource vnet 'Microsoft.Network/virtualNetworks@2023-11-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [addressPrefix]
    }
    subnets: [
      // Container Apps subnet - requires delegation
      {
        name: 'container-apps'
        properties: {
          addressPrefix: containerAppsSubnetPrefix
          networkSecurityGroup: {
            id: nsg.id
          }
          delegations: [
            {
              name: 'Microsoft.App.environments'
              properties: {
                serviceName: 'Microsoft.App/environments'
              }
            }
          ]
        }
      }
      // SQL subnet for private endpoint
      {
        name: 'sql'
        properties: {
          addressPrefix: sqlSubnetPrefix
          networkSecurityGroup: {
            id: nsg.id
          }
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
      // Key Vault subnet for private endpoint
      {
        name: 'keyvault'
        properties: {
          addressPrefix: keyVaultSubnetPrefix
          networkSecurityGroup: {
            id: nsg.id
          }
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
    ]
  }
}

// ----------------------------------------------------------------------------
// OUTPUTS
// ----------------------------------------------------------------------------

@description('VNet resource ID')
output id string = vnet.id

@description('VNet name')
output name string = vnet.name

@description('Container Apps subnet ID')
output containerAppsSubnetId string = vnet.properties.subnets[0].id

@description('SQL subnet ID')
output sqlSubnetId string = vnet.properties.subnets[1].id

@description('Key Vault subnet ID')
output keyVaultSubnetId string = vnet.properties.subnets[2].id

@description('NSG ID')
output nsgId string = nsg.id
