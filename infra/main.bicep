// ============================================================================
// NewsMinds - Main Infrastructure Orchestrator
// ============================================================================
// This is the entry point for deploying all Azure resources.
// It orchestrates the deployment of individual modules in the correct order.
//
// Security:
// - VNet with NSG restricts network access
// - All resources protected by IP allowlist
// - Container Apps ingress restricted to allowed IPs
//
// Usage:
//   az deployment group create \
//     --resource-group newsmind-dev-rg \
//     --template-file infra/main.bicep \
//     --parameters infra/environments/dev.bicepparam
// ============================================================================

// ----------------------------------------------------------------------------
// PARAMETERS
// ----------------------------------------------------------------------------

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

@description('OpenAI API key for AI features')
@secure()
param openaiApiKey string = ''

@description('Tags to apply to all resources')
param tags object = {}

@description('Allowed IP addresses for access. These IPs can access all resources.')
param allowedIPs array = []

// ----------------------------------------------------------------------------
// VARIABLES
// ----------------------------------------------------------------------------

// Resource naming convention: {project}-{environment}-{resource-type}
var resourcePrefix = '${projectName}-${environment}'

// Some Azure resources don't allow hyphens (e.g., storage accounts, key vaults)
var resourcePrefixNoHyphens = '${projectName}${environment}'

// Merge default tags with any custom tags passed in
var defaultTags = {
  Project: projectName
  Environment: environment
  ManagedBy: 'Bicep'
}
var allTags = union(defaultTags, tags)

// ----------------------------------------------------------------------------
// MODULES
// ----------------------------------------------------------------------------
// Modules are deployed in dependency order:
// 1. VNet (network foundation with NSG)
// 2. Key Vault (stores secrets)
// 3. Log Analytics + Application Insights (monitoring)
// 4. SQL Database (data layer)
// 5. Container Apps Environment (with VNet integration)
// 6. Container App API (API layer)

// --- Virtual Network ---
// Network security foundation with NSG
module vnet 'modules/vnet.bicep' = {
  name: 'vnet-deployment'
  params: {
    name: '${resourcePrefix}-vnet'
    location: location
    tags: allTags
    allowedIPs: allowedIPs
  }
}

// --- Key Vault ---
// Stores secrets like database connection strings, API keys
module keyVault 'modules/key-vault.bicep' = {
  name: 'keyVault-deployment'
  params: {
    name: '${resourcePrefixNoHyphens}kv'
    location: location
    tags: allTags
    allowedIPs: allowedIPs
  }
}

// --- Container Registry ---
// Private Docker registry for our container images
module containerRegistry 'modules/container-registry.bicep' = {
  name: 'containerRegistry-deployment'
  params: {
    name: '${resourcePrefixNoHyphens}acr'
    location: location
    tags: allTags
  }
}

// --- Storage Account for Qdrant ---
// Azure Files storage for Qdrant vector database persistence
module storageAccount 'modules/storage-account.bicep' = {
  name: 'storageAccount-deployment'
  params: {
    name: '${resourcePrefixNoHyphens}st'
    location: location
    tags: allTags
    fileShareName: 'qdrant-data'
    fileShareQuotaGB: 5
  }
}

// --- Log Analytics Workspace ---
// Central logging destination for all resources
module logAnalytics 'modules/log-analytics.bicep' = {
  name: 'logAnalytics-deployment'
  params: {
    name: '${resourcePrefix}-logs'
    location: location
    tags: allTags
  }
}

// --- Application Insights ---
// Application Performance Monitoring (APM) for our API
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
// Primary relational database for structured data
module sqlDatabase 'modules/sql-database.bicep' = {
  name: 'sqlDatabase-deployment'
  params: {
    serverName: '${resourcePrefix}-sql'
    location: location
    tags: allTags
    administratorLogin: sqlAdminLogin
    administratorPassword: sqlAdminPassword
    keyVaultName: keyVault.outputs.name
    allowedIPs: allowedIPs
  }
}

// --- Container Apps Environment ---
// Managed container environment with VNet integration
module containerAppsEnv 'modules/container-apps-env.bicep' = {
  name: 'containerAppsEnv-deployment'
  params: {
    name: '${resourcePrefix}-cae'
    location: location
    tags: allTags
    logAnalyticsWorkspaceId: logAnalytics.outputs.workspaceId
    subnetId: vnet.outputs.containerAppsSubnetId
  }
}

// --- Qdrant Vector Database ---
// Runs Qdrant as a separate Container App with persistent storage
module qdrantContainerApp 'modules/container-app-qdrant.bicep' = {
  name: 'qdrantContainerApp-deployment'
  params: {
    name: '${resourcePrefix}-qdrant'
    location: location
    tags: allTags
    containerAppsEnvId: containerAppsEnv.outputs.id
    containerAppsEnvName: containerAppsEnv.outputs.name
    storageAccountName: storageAccount.outputs.name
    storageAccountKey: storageAccount.outputs.accountKey
    fileShareName: storageAccount.outputs.fileShareName
    allowedIPs: allowedIPs  // Allow dashboard access from same IPs as API
  }
}

// --- Container App (Next.js Frontend) ---
// Hosts the Next.js dashboard as a Container App
// Deployed before the API so its FQDN can be passed as a CORS origin
module frontendContainerApp 'modules/container-app-frontend.bicep' = {
  name: 'frontendContainerApp-deployment'
  params: {
    name: '${resourcePrefix}-frontend'
    location: location
    tags: allTags
    containerAppsEnvId: containerAppsEnv.outputs.id
    allowedIPs: allowedIPs
  }
}

// --- Container App (FastAPI API) ---
// Hosts our FastAPI backend as a Container App
module apiContainerApp 'modules/container-app-api.bicep' = {
  name: 'apiContainerApp-deployment'
  params: {
    name: '${resourcePrefix}-api'
    location: location
    tags: allTags
    containerAppsEnvId: containerAppsEnv.outputs.id
    appInsightsConnectionString: appInsights.outputs.connectionString
    keyVaultName: keyVault.outputs.name
    databaseUrl: 'mssql+aioodbc://${sqlAdminLogin}:${sqlAdminPassword}@${sqlDatabase.outputs.fqdn}:1433/newsminds?driver=ODBC+Driver+18+for+SQL+Server&encrypt=yes&TrustServerCertificate=no'
    secretKey: secretKey
    openaiApiKey: openaiApiKey
    qdrantUrl: qdrantContainerApp.outputs.url
    corsOrigins: 'https://${frontendContainerApp.outputs.fqdn}'
    allowedIPs: allowedIPs
  }
}

// --- Monitoring Alerts ---
// Set up alerts for error rates, response times, and container health
module alerts 'modules/alerts.bicep' = {
  name: 'alerts-deployment'
  params: {
    namePrefix: resourcePrefix
    location: location
    tags: allTags
    appInsightsId: appInsights.outputs.id
    containerAppId: apiContainerApp.outputs.id
  }
}

// ----------------------------------------------------------------------------
// OUTPUTS
// ----------------------------------------------------------------------------

@description('VNet name')
output vnetName string = vnet.outputs.name

@description('NSG ID')
output nsgId string = vnet.outputs.nsgId

@description('Key Vault name for secret management')
output keyVaultName string = keyVault.outputs.name

@description('Key Vault URI for SDK configuration')
output keyVaultUri string = keyVault.outputs.uri

@description('Application Insights connection string')
output appInsightsConnectionString string = appInsights.outputs.connectionString

@description('SQL Server FQDN')
output sqlServerFqdn string = sqlDatabase.outputs.fqdn

@description('Container Apps Environment ID')
output containerAppsEnvId string = containerAppsEnv.outputs.id

@description('API Container App FQDN')
output apiHostname string = apiContainerApp.outputs.fqdn

@description('Container Registry login server')
output acrLoginServer string = containerRegistry.outputs.loginServer

@description('Container Registry name')
output acrName string = containerRegistry.outputs.name

@description('Qdrant Container App FQDN (internal)')
output qdrantUrl string = qdrantContainerApp.outputs.url

@description('Frontend Container App FQDN')
output frontendHostname string = frontendContainerApp.outputs.fqdn

@description('Qdrant Dashboard URL (if external access enabled)')
output qdrantDashboardUrl string = 'https://${qdrantContainerApp.outputs.fqdn}/dashboard'
