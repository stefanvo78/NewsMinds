// ============================================================================
// App Service Module (for FastAPI)
// ============================================================================
// Azure App Service is a fully managed platform for web applications.
// We use it for the FastAPI backend because:
// - Built-in Python runtime (no Docker needed for basic deployments)
// - Automatic scaling
// - Deployment slots for zero-downtime deployments
// - Managed SSL certificates
// - Integrated with Key Vault for secrets
//
// The FastAPI API handles:
// - User authentication and authorization
// - REST endpoints for the frontend
// - Orchestrating agent workflows
// - WebSocket connections for real-time updates
// ============================================================================

// ----------------------------------------------------------------------------
// PARAMETERS
// ----------------------------------------------------------------------------

@description('Name of the App Service')
param name string

@description('Azure region')
param location string

@description('Tags to apply')
param tags object = {}

@description('App Service Plan SKU')
@allowed(['B1', 'B2', 'B3', 'S1', 'S2', 'S3', 'P1v3', 'P2v3', 'P3v3'])
param skuName string = 'B1'  // Basic tier: ~$13/month

@description('Python version')
@allowed(['3.10', '3.11', '3.12'])
param pythonVersion string = '3.12'

@description('Application Insights connection string')
param appInsightsConnectionString string

@description('Application Insights instrumentation key')
param appInsightsInstrumentationKey string

@description('Key Vault name for secret references')
param keyVaultName string

// ----------------------------------------------------------------------------
// RESOURCES
// ----------------------------------------------------------------------------

// App Service Plan - the compute resources
// Multiple App Services can share one plan
resource appServicePlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: '${name}-plan'
  location: location
  tags: tags

  // SKU determines compute resources
  sku: {
    name: skuName
  }

  // Linux-based (required for Python)
  kind: 'linux'
  properties: {
    reserved: true  // Required for Linux
  }
}

// The App Service itself (web app)
resource appService 'Microsoft.Web/sites@2023-12-01' = {
  name: name
  location: location
  tags: tags

  // Identity for Key Vault access (managed identity)
  identity: {
    type: 'SystemAssigned'  // Azure manages the identity automatically
  }

  properties: {
    // Link to the App Service Plan
    serverFarmId: appServicePlan.id

    // HTTPS only
    httpsOnly: true

    // Site configuration
    siteConfig: {
      // Python version (Linux)
      linuxFxVersion: 'PYTHON|${pythonVersion}'

      // Always on prevents cold starts (not available on Free/Shared tiers)
      alwaysOn: skuName != 'F1'

      // Startup command for FastAPI with Uvicorn
      // Adjust path based on your project structure
      appCommandLine: 'gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.api.main:app --bind 0.0.0.0:8000'

      // Minimum TLS version
      minTlsVersion: '1.2'

      // FTPS state (disable FTP for security)
      ftpsState: 'Disabled'

      // Health check endpoint (FastAPI /health)
      healthCheckPath: '/health'

      // App settings (environment variables)
      appSettings: [
        // Application Insights
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsightsConnectionString
        }
        {
          name: 'APPINSIGHTS_INSTRUMENTATIONKEY'
          value: appInsightsInstrumentationKey
        }
        // Enable Application Insights for Python
        {
          name: 'ApplicationInsightsAgent_EXTENSION_VERSION'
          value: '~3'
        }
        // Key Vault URI for SDK configuration
        {
          name: 'KEY_VAULT_URL'
          value: 'https://${keyVaultName}${environment().suffixes.keyvaultDns}/'
        }
        // Environment indicator
        {
          name: 'ENVIRONMENT'
          value: contains(name, 'prod') ? 'production' : 'development'
        }
        // Python path
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
      ]
    }
  }
}

// Reference the Key Vault to grant access
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

// Grant the App Service access to Key Vault secrets
// Uses RBAC role assignment (Key Vault Secrets User)
resource keyVaultAccessPolicy 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, appService.id, 'Key Vault Secrets User')
  scope: keyVault
  properties: {
    // Key Vault Secrets User role - allows reading secrets
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')
    principalId: appService.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Configure logging
resource appServiceLogs 'Microsoft.Web/sites/config@2023-12-01' = {
  parent: appService
  name: 'logs'
  properties: {
    applicationLogs: {
      fileSystem: {
        level: 'Information'
      }
    }
    httpLogs: {
      fileSystem: {
        enabled: true
        retentionInDays: 7
        retentionInMb: 35
      }
    }
    detailedErrorMessages: {
      enabled: true
    }
  }
}

// ----------------------------------------------------------------------------
// OUTPUTS
// ----------------------------------------------------------------------------

@description('App Service resource ID')
output id string = appService.id

@description('App Service name')
output name string = appService.name

@description('App Service default hostname')
output defaultHostname string = appService.properties.defaultHostName

@description('App Service principal ID (for RBAC)')
output principalId string = appService.identity.principalId

@description('App Service Plan ID')
output appServicePlanId string = appServicePlan.id
