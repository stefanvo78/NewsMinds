// ============================================================================
// Storage Account Module
// ============================================================================
// Creates an Azure Storage Account with Azure Files for persistent storage.
// Used by Qdrant to persist vector data.
// ============================================================================

// ----------------------------------------------------------------------------
// PARAMETERS
// ----------------------------------------------------------------------------

@description('Name of the storage account (must be globally unique, lowercase, no hyphens)')
@minLength(3)
@maxLength(24)
param name string

@description('Azure region')
param location string

@description('Tags to apply')
param tags object = {}

@description('Name of the file share to create')
param fileShareName string = 'qdrant-data'

@description('File share quota in GB')
param fileShareQuotaGB int = 5

// ----------------------------------------------------------------------------
// RESOURCES
// ----------------------------------------------------------------------------

// Storage Account
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: name
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'  // Locally redundant storage (cost-effective for dev)
  }
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
    accessTier: 'Hot'
  }
}

// File Service
resource fileService 'Microsoft.Storage/storageAccounts/fileServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
}

// File Share for Qdrant data
resource fileShare 'Microsoft.Storage/storageAccounts/fileServices/fileShares@2023-01-01' = {
  parent: fileService
  name: fileShareName
  properties: {
    shareQuota: fileShareQuotaGB
    accessTier: 'TransactionOptimized'
  }
}

// ----------------------------------------------------------------------------
// OUTPUTS
// ----------------------------------------------------------------------------

@description('Storage account name')
output name string = storageAccount.name

@description('Storage account ID')
output id string = storageAccount.id

@description('File share name')
output fileShareName string = fileShare.name

@description('Storage account key (for mounting)')
output accountKey string = storageAccount.listKeys().keys[0].value
