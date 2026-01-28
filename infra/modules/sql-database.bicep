// ============================================================================
// Azure SQL Database Module
// ============================================================================
// Azure SQL Database is Microsoft's cloud relational database.
// Using serverless tier for dev (auto-pause, pay-per-use).
//
// Used for:
// - User data and authentication
// - News article metadata
// - Agent task history and logs
// ============================================================================

// ----------------------------------------------------------------------------
// PARAMETERS
// ----------------------------------------------------------------------------

@description('SQL Server name (globally unique)')
param serverName string

@description('Database name')
param databaseName string = 'newsminds'

@description('Azure region')
param location string

@description('Tags to apply')
param tags object = {}

@description('Administrator login username')
@secure()
param administratorLogin string

@description('Administrator login password')
@secure()
param administratorPassword string

@description('Key Vault name for storing connection string')
param keyVaultName string

@description('SKU name for the database')
@allowed(['Basic', 'S0', 'S1', 'GP_S_Gen5_1', 'GP_S_Gen5_2'])
param skuName string = 'GP_S_Gen5_1'  // Serverless Gen5, 1 vCore

@description('Enable serverless auto-pause (minutes of inactivity)')
@minValue(60)
@maxValue(10080)
param autoPauseDelay int = 60  // Pause after 1 hour of inactivity

@description('Minimum capacity (vCores) for serverless')
param minCapacity string = '0.5'

@description('Allowed IP addresses for firewall rules')
param allowedIPs array = []

// ----------------------------------------------------------------------------
// RESOURCES
// ----------------------------------------------------------------------------

// SQL Server (logical server)
resource sqlServer 'Microsoft.Sql/servers@2023-08-01-preview' = {
  name: serverName
  location: location
  tags: tags
  properties: {
    administratorLogin: administratorLogin
    administratorLoginPassword: administratorPassword
    version: '12.0'
    minimalTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'  // Allow public access with firewall rules
  }
}

// Firewall rule: Allow Azure services (needed for Container Apps)
resource allowAzureServices 'Microsoft.Sql/servers/firewallRules@2023-08-01-preview' = {
  parent: sqlServer
  name: 'AllowAllAzureIps'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// Firewall rules: Allow specific IPs
resource allowedIPRules 'Microsoft.Sql/servers/firewallRules@2023-08-01-preview' = [for (ip, i) in allowedIPs: {
  parent: sqlServer
  name: 'AllowIP-${i}'
  properties: {
    startIpAddress: ip
    endIpAddress: ip
  }
}]

// SQL Database
resource sqlDatabase 'Microsoft.Sql/servers/databases@2023-08-01-preview' = {
  parent: sqlServer
  name: databaseName
  location: location
  tags: tags
  sku: {
    name: skuName
    tier: skuName == 'Basic' ? 'Basic' : (startsWith(skuName, 'S') ? 'Standard' : 'GeneralPurpose')
  }
  properties: {
    collation: 'SQL_Latin1_General_CP1_CI_AS'
    maxSizeBytes: skuName == 'Basic' ? 2147483648 : 34359738368  // 2GB for Basic, 32GB otherwise
    autoPauseDelay: startsWith(skuName, 'GP_S') ? autoPauseDelay : -1
    minCapacity: startsWith(skuName, 'GP_S') ? json(minCapacity) : null
    requestedBackupStorageRedundancy: 'Local'  // Cheaper for dev
  }
}

// Reference existing Key Vault
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

// Store connection string in Key Vault
resource connectionStringSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'sql-connection-string'
  properties: {
    value: 'Driver={ODBC Driver 18 for SQL Server};Server=tcp:${sqlServer.properties.fullyQualifiedDomainName},1433;Database=${databaseName};Uid=${administratorLogin};Pwd=${administratorPassword};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;'
  }
}

// Also store SQLAlchemy-compatible connection string
resource sqlalchemyConnectionSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'sqlalchemy-connection-string'
  properties: {
    value: 'mssql+aioodbc://${administratorLogin}:${administratorPassword}@${sqlServer.properties.fullyQualifiedDomainName}:1433/${databaseName}?driver=ODBC+Driver+18+for+SQL+Server&encrypt=yes&TrustServerCertificate=no'
  }
}

// ----------------------------------------------------------------------------
// OUTPUTS
// ----------------------------------------------------------------------------

@description('SQL Server resource ID')
output serverId string = sqlServer.id

@description('SQL Server name')
output serverName string = sqlServer.name

@description('SQL Server FQDN')
output fqdn string = sqlServer.properties.fullyQualifiedDomainName

@description('Database name')
output databaseName string = sqlDatabase.name
