// ============================================================================
// Container Apps Environment Module
// ============================================================================
// Azure Container Apps is a serverless container platform built on Kubernetes.
// The "Environment" is the shared infrastructure where Container Apps run.
//
// Key features for NewsMinds agents:
// - KEDA autoscaling (scale based on queue depth, cron, HTTP traffic)
// - Dapr integration (service mesh, pub/sub, state management)
// - Scale to zero (cost savings when agents are idle)
// - Multiple revisions (canary deployments)
// - Built-in ingress (HTTP/gRPC routing)
//
// Architecture:
// ┌─────────────────────────────────────────────────────────┐
// │              Container Apps Environment                  │
// │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
// │  │  Collector  │  │  Analyzer   │  │ Synthesizer │     │
// │  │    Agent    │  │    Agent    │  │    Agent    │     │
// │  │ (KEDA cron) │  │(KEDA queue) │  │(KEDA events)│     │
// │  └─────────────┘  └─────────────┘  └─────────────┘     │
// │                    │                                    │
// │              ┌─────┴─────┐                              │
// │              │   Dapr    │ (pub/sub, state)            │
// │              └───────────┘                              │
// └─────────────────────────────────────────────────────────┘
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

    // Workload profiles determine compute options
    // Consumption: Serverless, auto-scaling, pay-per-use
    // Dedicated: Reserved compute for predictable workloads
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]

    // Dapr configuration (we'll enable per-app, not environment-wide)
    // Dapr provides:
    // - Service discovery
    // - Pub/sub messaging
    // - State management
    // - Secret management

    // Peer authentication (mTLS between apps)
    peerAuthentication: {
      mtls: {
        enabled: true  // Encrypt traffic between container apps
      }
    }
  }
}

// Dapr Component: Redis Pub/Sub
// This allows agents to communicate via publish/subscribe pattern
// Collector publishes "news.collected" -> Analyzer subscribes
// Analyzer publishes "news.analyzed" -> Synthesizer subscribes
resource daprPubSub 'Microsoft.App/managedEnvironments/daprComponents@2024-03-01' = {
  parent: containerAppsEnv
  name: 'pubsub-redis'
  properties: {
    componentType: 'pubsub.redis'
    version: 'v1'
    metadata: [
      {
        name: 'redisHost'
        // This will be replaced with actual Redis hostname in environment config
        // Using secretRef to avoid hardcoding
        value: 'placeholder-to-be-set'
      }
      {
        name: 'redisPassword'
        secretRef: 'redis-password'
      }
      {
        name: 'enableTLS'
        value: 'true'
      }
    ]
    secrets: [
      {
        name: 'redis-password'
        // This is a placeholder - actual secret comes from Key Vault at deployment
        value: 'placeholder-to-be-set'
      }
    ]
    scopes: [
      'collector-agent'
      'analyzer-agent'
      'synthesizer-agent'
    ]
  }
}

// Dapr Component: Redis State Store
// Persistent state for agents (checkpoints, intermediate results)
resource daprStateStore 'Microsoft.App/managedEnvironments/daprComponents@2024-03-01' = {
  parent: containerAppsEnv
  name: 'statestore-redis'
  properties: {
    componentType: 'state.redis'
    version: 'v1'
    metadata: [
      {
        name: 'redisHost'
        value: 'placeholder-to-be-set'
      }
      {
        name: 'redisPassword'
        secretRef: 'redis-password'
      }
      {
        name: 'enableTLS'
        value: 'true'
      }
      {
        name: 'actorStateStore'
        value: 'true'  // Enable actor pattern support
      }
    ]
    secrets: [
      {
        name: 'redis-password'
        value: 'placeholder-to-be-set'
      }
    ]
    scopes: [
      'collector-agent'
      'analyzer-agent'
      'synthesizer-agent'
    ]
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
