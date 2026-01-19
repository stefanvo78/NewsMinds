// ============================================================================
// NewsMinds - Main Infrastructure Orchestrator
// ============================================================================
// This is the entry point for deploying all Azure resources.
// It orchestrates the deployment of individual modules in the correct order.
//
// Usage:
//   az deployment group create \
//     --resource-group newsminds-dev-rg \
//     --template-file infra/main.bicep \
//     --parameters infra/environments/dev.bicepparam
// ============================================================================

// ----------------------------------------------------------------------------
// PARAMETERS
// ----------------------------------------------------------------------------
// Parameters are inputs to the template. They allow customization per environment.
// The @allowed decorator restricts values to prevent mistakes.
// The @description decorator documents the parameter (shows in Azure Portal).

@description('Environment name (dev, staging, prod)')
@allowed(['dev', 'staging', 'prod'])
param environment string

@description('Azure region for all resources')
param location string = 'westus2'

@description('Base name for all resources')
param projectName string = 'newsminds'

@description('PostgreSQL administrator login username')
@secure()
param postgresAdminLogin string

@description('PostgreSQL administrator password')
@secure()
param postgresAdminPassword string

@description('Tags to apply to all resources')
param tags object = {}

// ----------------------------------------------------------------------------
// VARIABLES
// ----------------------------------------------------------------------------
// Variables are computed values used throughout the template.
// We use naming conventions that follow Azure best practices.
// See: https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/azure-best-practices/resource-naming

// Resource naming convention: {project}-{environment}-{resource-type}
var resourcePrefix = '${projectName}-${environment}'

// Some Azure resources don't allow hyphens (e.g., storage accounts, key vaults)
var resourcePrefixNoHyphens = '${projectName}${environment}'

// Merge default tags with any custom tags passed in
var defaultTags = {
  Project: projectName
  Environment: environment
  ManagedBy: 'Bicep'
  Repository: 'github.com/yourusername/NewsMinds'
}
var allTags = union(defaultTags, tags)

// ----------------------------------------------------------------------------
// MODULES
// ----------------------------------------------------------------------------
// Modules are deployed in dependency order:
// 1. Key Vault (stores secrets for other resources)
// 2. Log Analytics + Application Insights (monitoring foundation)
// 3. PostgreSQL (data layer)
// 4. Redis Cache (caching layer)
// 5. Container Apps Environment (agent runtime)
// 6. App Service (API layer)

// --- Key Vault ---
// Stores secrets like database connection strings, API keys
// Other resources will reference secrets from here
module keyVault 'modules/key-vault.bicep' = {
  name: 'keyVault-deployment'
  params: {
    name: '${resourcePrefixNoHyphens}kv'  // Key Vault names: 3-24 chars, alphanumeric only
    location: location
    tags: allTags
  }
}

// --- Log Analytics Workspace ---
// Central logging destination for all resources
// Application Insights sends data here
module logAnalytics 'modules/log-analytics.bicep' = {
  name: 'logAnalytics-deployment'
  params: {
    name: '${resourcePrefix}-logs'
    location: location
    tags: allTags
  }
}

// --- Application Insights ---
// Application Performance Monitoring (APM) for our API and agents
// Provides request tracing, dependency tracking, error logging
module appInsights 'modules/app-insights.bicep' = {
  name: 'appInsights-deployment'
  params: {
    name: '${resourcePrefix}-insights'
    location: location
    tags: allTags
    logAnalyticsWorkspaceId: logAnalytics.outputs.workspaceId
  }
}

// --- PostgreSQL Flexible Server ---
// Primary relational database for structured data:
// - User data, sessions
// - News article metadata
// - Agent task history
module postgresql 'modules/postgresql.bicep' = {
  name: 'postgresql-deployment'
  params: {
    name: '${resourcePrefix}-psql'
    location: location
    tags: allTags
    administratorLogin: postgresAdminLogin
    administratorPassword: postgresAdminPassword
    // Store connection string in Key Vault
    keyVaultName: keyVault.outputs.name
  }
}

// --- Redis Cache ---
// Used for:
// - Session caching
// - Rate limiting
// - Inter-agent message queuing (pub/sub)
// - Temporary data caching
module redis 'modules/redis.bicep' = {
  name: 'redis-deployment'
  params: {
    name: '${resourcePrefix}-redis'
    location: location
    tags: allTags
    // Store connection string in Key Vault
    keyVaultName: keyVault.outputs.name
  }
}

// --- Container Apps Environment ---
// Managed Kubernetes environment for our AI agents
// Includes KEDA for event-driven autoscaling
module containerAppsEnv 'modules/container-apps-env.bicep' = {
  name: 'containerAppsEnv-deployment'
  params: {
    name: '${resourcePrefix}-cae'
    location: location
    tags: allTags
    logAnalyticsWorkspaceId: logAnalytics.outputs.workspaceId
  }
}

// --- App Service (FastAPI API) ---
// Hosts our FastAPI backend
// Linux-based with Python runtime
module appService 'modules/app-service.bicep' = {
  name: 'appService-deployment'
  params: {
    name: '${resourcePrefix}-api'
    location: location
    tags: allTags
    appInsightsConnectionString: appInsights.outputs.connectionString
    appInsightsInstrumentationKey: appInsights.outputs.instrumentationKey
    keyVaultName: keyVault.outputs.name
  }
}

// ----------------------------------------------------------------------------
// OUTPUTS
// ----------------------------------------------------------------------------
// Outputs expose values from the deployment for:
// - CI/CD pipelines to use
// - Other Bicep templates to reference
// - Developers to know endpoints

@description('Key Vault name for secret management')
output keyVaultName string = keyVault.outputs.name

@description('Key Vault URI for SDK configuration')
output keyVaultUri string = keyVault.outputs.uri

@description('Application Insights connection string')
output appInsightsConnectionString string = appInsights.outputs.connectionString

@description('PostgreSQL server FQDN')
output postgresqlFqdn string = postgresql.outputs.fqdn

@description('Redis hostname')
output redisHostname string = redis.outputs.hostname

@description('Container Apps Environment ID')
output containerAppsEnvId string = containerAppsEnv.outputs.id

@description('App Service default hostname')
output apiHostname string = appService.outputs.defaultHostname
