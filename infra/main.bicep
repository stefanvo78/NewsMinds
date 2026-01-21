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

@description('SQL Server administrator login username')
@secure()
param sqlAdminLogin string

@description('SQL Server administrator password')
@secure()
param sqlAdminPassword string

@description('JWT secret key for authentication')
@secure()
param secretKey string


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

// --- Container Registry ---
// Private Docker registry for our container images
// GitHub Actions will push images here, Container Apps will pull from here
module containerRegistry 'modules/container-registry.bicep' = {
  name: 'containerRegistry-deployment'
  params: {
    name: '${resourcePrefixNoHyphens}acr'  // ACR names: alphanumeric only
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

// --- Azure SQL Database ---
// Primary relational database for structured data:
// - User data, sessions
// - News article metadata
// - Agent task history
module sqlDatabase 'modules/sql-database.bicep' = {
  name: 'sqlDatabase-deployment'
  params: {
    serverName: '${resourcePrefix}-sql'
    location: location
    tags: allTags
    administratorLogin: sqlAdminLogin
    administratorPassword: sqlAdminPassword
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

// --- Container App (FastAPI API) ---
// Hosts our FastAPI backend as a Container App
// Uses consumption plan - no VM quota required
module apiContainerApp 'modules/container-app-api.bicep' = {
  name: 'apiContainerApp-deployment'
  params: {
    name: '${resourcePrefix}-api'
    location: location
    tags: allTags
    containerAppsEnvId: containerAppsEnv.outputs.id
    appInsightsConnectionString: appInsights.outputs.connectionString
    keyVaultName: keyVault.outputs.name
    acrLoginServer: containerRegistry.outputs.loginServer
    acrName: containerRegistry.outputs.name
    // Pass secrets for the application
    databaseUrl: 'mssql+aioodbc://${sqlAdminLogin}:${sqlAdminPassword}@${sqlDatabase.outputs.fqdn}:1433/newsminds?driver=ODBC+Driver+18+for+SQL+Server&encrypt=yes&TrustServerCertificate=no'
    secretKey: secretKey
  }
}


// --- RBAC: Allow Container App to pull from ACR ---
// The Container App needs AcrPull role to pull images using managed identity
resource acrPullRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistry.outputs.id, apiContainerApp.outputs.principalId, 'acrpull')
  scope: resourceGroup()
  properties: {
    // AcrPull built-in role ID
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalId: apiContainerApp.outputs.principalId
    principalType: 'ServicePrincipal'
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

@description('SQL Server FQDN')
output sqlServerFqdn string = sqlDatabase.outputs.fqdn

@description('Redis hostname')
output redisHostname string = redis.outputs.hostname

@description('Container Apps Environment ID')
output containerAppsEnvId string = containerAppsEnv.outputs.id

@description('API Container App FQDN')
output apiHostname string = apiContainerApp.outputs.fqdn

@description('Container Registry login server')
output acrLoginServer string = containerRegistry.outputs.loginServer

@description('Container Registry name')
output acrName string = containerRegistry.outputs.name

