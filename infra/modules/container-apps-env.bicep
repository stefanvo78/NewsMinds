// ============================================================================
// Container Apps Environment Module
// ============================================================================
// Azure Container Apps is a serverless container platform built on Kubernetes.
// The "Environment" is the shared infrastructure where Container Apps run.
//
// Key features for NewsMinds agents:
// - KEDA autoscaling (scale based on queue depth, cron, HTTP traffic)
// - Scale to zero (cost savings when agents are idle)
// - Multiple revisions (canary deployments)
// - Built-in ingress (HTTP/gRPC routing)
// - VNet integration for network security
// ============================================================================

// ----------------------------------------------------------------------------
// PARAMETERS
// ----------------------------------------------------------------------------

@description('Name of the Container Apps Environment')
param name string

@description('Azure region')
param location string

@description('Tags to apply')
param tags object = {}

@description('Log Analytics Workspace ID for logging')
param logAnalyticsWorkspaceId string

@description('Enable zone redundancy (for production high availability)')
param zoneRedundant bool = false

@description('Subnet ID for VNet integration (optional)')
param subnetId string = ''

@description('Workload profile type')
@allowed(['Consumption', 'D4', 'D8', 'D16', 'D32', 'E4', 'E8', 'E16', 'E32'])
param workloadProfileType string = 'Consumption'  // Serverless, pay-per-use

// ----------------------------------------------------------------------------
// RESOURCES
// ----------------------------------------------------------------------------

// Container Apps Environment - shared infrastructure
resource containerAppsEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    // Link to Log Analytics for logging
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: reference(logAnalyticsWorkspaceId, '2023-09-01').customerId
        sharedKey: listKeys(logAnalyticsWorkspaceId, '2023-09-01').primarySharedKey
      }
    }

    // Zone redundancy for high availability (production)
    zoneRedundant: zoneRedundant

    // VNet configuration - integrate with subnet if provided
    vnetConfiguration: !empty(subnetId) ? {
      infrastructureSubnetId: subnetId
      internal: false  // External ingress (accessible from internet with IP restrictions)
    } : null

    // Workload profiles determine compute options
    // Consumption: Serverless, auto-scaling, pay-per-use
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]

    // Peer authentication (mTLS between apps)
    peerAuthentication: {
      mtls: {
        enabled: true  // Encrypt traffic between container apps
      }
    }
  }
}

// ----------------------------------------------------------------------------
// OUTPUTS
// ----------------------------------------------------------------------------

@description('Container Apps Environment ID')
output id string = containerAppsEnv.id

@description('Container Apps Environment name')
output name string = containerAppsEnv.name

@description('Default domain for container apps')
output defaultDomain string = containerAppsEnv.properties.defaultDomain

@description('Static IP for the environment (if applicable)')
output staticIp string = containerAppsEnv.properties.staticIp
