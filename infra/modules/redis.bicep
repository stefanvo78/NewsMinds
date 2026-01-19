// ============================================================================
// Azure Cache for Redis Module
// ============================================================================
// Redis is an in-memory data store used for:
// - Session caching (fast user session lookups)
// - Rate limiting (sliding window counters)
// - Pub/Sub messaging (inter-agent communication)
// - Response caching (cache expensive LLM responses)
// - Distributed locking (prevent duplicate processing)
//
// For NewsMinds, Redis enables:
// - Agent-to-agent messaging via pub/sub channels
// - Caching news API responses to reduce costs
// - Rate limiting external API calls
// - Session storage for the FastAPI backend
// ============================================================================

// ----------------------------------------------------------------------------
// PARAMETERS
// ----------------------------------------------------------------------------

@description('Name of the Redis Cache instance')
param name string

@description('Azure region for the cache')
param location string

@description('Tags to apply to the resource')
param tags object = {}

@description('SKU: Basic (dev), Standard (HA), Premium (clustering)')
@allowed(['Basic', 'Standard', 'Premium'])
param skuName string = 'Basic'

@description('SKU Family: C (Basic/Standard), P (Premium)')
@allowed(['C', 'P'])
param skuFamily string = 'C'

@description('Cache size: 0=250MB, 1=1GB, 2=2.5GB, etc.')
@minValue(0)
@maxValue(6)
param skuCapacity int = 0  // 250MB is sufficient for dev

@description('Enable non-SSL port (6379). Disable for production.')
param enableNonSslPort bool = false

@description('Minimum TLS version')
@allowed(['1.0', '1.1', '1.2'])
param minimumTlsVersion string = '1.2'

@description('Name of the Key Vault to store connection string')
param keyVaultName string

// ----------------------------------------------------------------------------
// RESOURCE
// ----------------------------------------------------------------------------

resource redisCache 'Microsoft.Cache/redis@2023-08-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    // SKU determines pricing and features
    // Basic: No SLA, single node (dev only)
    // Standard: 99.9% SLA, replicated (production)
    // Premium: Clustering, persistence, VNet (enterprise)
    sku: {
      name: skuName
      family: skuFamily
      capacity: skuCapacity
    }

    // Non-SSL port (6379) - disable for production security
    enableNonSslPort: enableNonSslPort

    // Minimum TLS version for encrypted connections
    minimumTlsVersion: minimumTlsVersion

    // Redis configuration
    redisConfiguration: {
      // Enable keyspace notifications for pub/sub
      // 'AKE' = All keyspace events, key events, eviction events
      'notify-keyspace-events': 'AKE'

      // Max memory policy: what happens when cache is full
      // volatile-lru: Evict keys with TTL using LRU
      'maxmemory-policy': 'volatile-lru'
    }

    // Public network access (disable for prod with private endpoints)
    publicNetworkAccess: 'Enabled'
  }
}

// Reference existing Key Vault
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

// Store Redis connection string in Key Vault
// Format: rediss://:password@hostname:port (rediss = Redis + SSL)
resource redisConnectionStringSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'RedisConnectionString'
  properties: {
    value: 'rediss://:${redisCache.listKeys().primaryKey}@${redisCache.properties.hostName}:${redisCache.properties.sslPort}'
    contentType: 'text/plain'
    attributes: {
      enabled: true
    }
  }
}

// Also store the primary key separately (some SDKs need it)
resource redisPrimaryKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'RedisPrimaryKey'
  properties: {
    value: redisCache.listKeys().primaryKey
    contentType: 'text/plain'
    attributes: {
      enabled: true
    }
  }
}

// ----------------------------------------------------------------------------
// OUTPUTS
// ----------------------------------------------------------------------------

@description('Redis Cache resource ID')
output id string = redisCache.id

@description('Redis Cache name')
output name string = redisCache.name

@description('Redis Cache hostname')
output hostname string = redisCache.properties.hostName

@description('Redis SSL port (6380)')
output sslPort int = redisCache.properties.sslPort
