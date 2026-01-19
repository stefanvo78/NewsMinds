// ============================================================================
// PostgreSQL Flexible Server Module
// ============================================================================
// Azure Database for PostgreSQL - Flexible Server is the managed PostgreSQL
// service on Azure. Key features:
// - PostgreSQL 16 support
// - Burstable compute (cost-effective for dev)
// - Built-in pgvector extension (for vector similarity search!)
// - Automatic backups and point-in-time restore
// - High availability option (zone redundant)
//
// For NewsMinds, PostgreSQL stores:
// - User accounts and authentication
// - News article metadata (title, source, date, URL)
// - Agent task queue and execution history
// - System configuration and audit logs
// ============================================================================

// ----------------------------------------------------------------------------
// PARAMETERS
// ----------------------------------------------------------------------------

@description('Name of the PostgreSQL server')
param name string

@description('Azure region for the server')
param location string

@description('Tags to apply to the resource')
param tags object = {}

@description('Administrator login username')
@secure()
param administratorLogin string

@description('Administrator login password')
@secure()
param administratorPassword string

@description('PostgreSQL version')
@allowed(['14', '15', '16'])
param postgresVersion string = '16'

@description('SKU tier: Burstable (dev), GeneralPurpose (prod), MemoryOptimized (heavy workloads)')
@allowed(['Burstable', 'GeneralPurpose', 'MemoryOptimized'])
param skuTier string = 'Burstable'

@description('SKU name within the tier')
param skuName string = 'Standard_B1ms'  // Burstable: 1 vCore, 2GB RAM (~$12/month)

@description('Storage size in GB')
@minValue(32)
@maxValue(16384)
param storageSizeGB int = 32

@description('Name of the Key Vault to store connection string')
param keyVaultName string

@description('Name of the default database to create')
param databaseName string = 'newsminds'

// ----------------------------------------------------------------------------
// RESOURCES
// ----------------------------------------------------------------------------

// PostgreSQL Flexible Server
resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-12-01-preview' = {
  name: name
  location: location
  tags: tags

  // SKU determines compute resources and pricing
  sku: {
    name: skuName
    tier: skuTier
  }

  properties: {
    // PostgreSQL version
    version: postgresVersion

    // Administrator credentials
    administratorLogin: administratorLogin
    administratorLoginPassword: administratorPassword

    // Storage configuration
    storage: {
      storageSizeGB: storageSizeGB
      autoGrow: 'Enabled'  // Automatically grow storage when needed
    }

    // Backup configuration
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'  // Enable for prod disaster recovery
    }

    // High availability (disable for dev to save costs)
    highAvailability: {
      mode: 'Disabled'  // Options: Disabled, SameZone, ZoneRedundant
    }

    // Network configuration
    // For dev: Allow public access with firewall rules
    // For prod: Use private endpoints
    network: {
      publicNetworkAccess: 'Enabled'
    }

    // Authentication
    authConfig: {
      activeDirectoryAuth: 'Disabled'  // Enable for prod with AAD
      passwordAuth: 'Enabled'
    }
  }
}

// Firewall rule: Allow Azure services
// This lets App Service and Container Apps connect
resource firewallAzureServices 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-12-01-preview' = {
  parent: postgresServer
  name: 'AllowAzureServices'
  properties: {
    // Special IP range that means "Azure services"
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// Create the default database
resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-12-01-preview' = {
  parent: postgresServer
  name: databaseName
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// Enable pgvector extension (for vector similarity search)
// This is crucial for RAG applications!
resource pgvectorConfig 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2023-12-01-preview' = {
  parent: postgresServer
  name: 'azure.extensions'
  properties: {
    value: 'vector'  // Enables pgvector extension
    source: 'user-override'
  }
}

// Reference existing Key Vault to store connection string
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

// Store PostgreSQL connection string in Key Vault
resource postgresConnectionStringSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'PostgresConnectionString'
  properties: {
    value: 'postgresql://${administratorLogin}:${administratorPassword}@${postgresServer.properties.fullyQualifiedDomainName}:5432/${databaseName}?sslmode=require'
    contentType: 'text/plain'
    attributes: {
      enabled: true
    }
  }
}

// ----------------------------------------------------------------------------
// OUTPUTS
// ----------------------------------------------------------------------------

@description('PostgreSQL server ID')
output id string = postgresServer.id

@description('PostgreSQL server name')
output name string = postgresServer.name

@description('PostgreSQL server FQDN')
output fqdn string = postgresServer.properties.fullyQualifiedDomainName

@description('Default database name')
output databaseName string = database.name
