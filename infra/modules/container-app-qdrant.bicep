// ============================================================================
// Qdrant Container App Module
// ============================================================================
// Deploys Qdrant vector database as a Container App with persistent storage.
// Uses internal ingress so only other Container Apps can access it.
// ============================================================================

// ----------------------------------------------------------------------------
// PARAMETERS
// ----------------------------------------------------------------------------

@description('Name of the Container App')
param name string

@description('Azure region')
param location string

@description('Tags to apply')
param tags object = {}

@description('Container Apps Environment ID')
param containerAppsEnvId string

@description('Container Apps Environment name')
param containerAppsEnvName string

@description('Storage account name for persistent data')
param storageAccountName string

@description('Storage account key')
@secure()
param storageAccountKey string

@description('File share name')
param fileShareName string

// ----------------------------------------------------------------------------
// RESOURCES
// ----------------------------------------------------------------------------

// Add storage mount to the Container Apps Environment
resource containerAppsEnv 'Microsoft.App/managedEnvironments@2024-03-01' existing = {
  name: containerAppsEnvName
}

// Azure Files storage mount in the environment
resource storageMount 'Microsoft.App/managedEnvironments/storages@2024-03-01' = {
  parent: containerAppsEnv
  name: 'qdrant-storage'
  properties: {
    azureFile: {
      accountName: storageAccountName
      accountKey: storageAccountKey
      shareName: fileShareName
      accessMode: 'ReadWrite'
    }
  }
}

// Qdrant Container App
resource qdrantApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  tags: tags
  dependsOn: [
    storageMount
  ]

  properties: {
    managedEnvironmentId: containerAppsEnvId

    configuration: {
      // Internal ingress - only accessible within the Container Apps Environment
      ingress: {
        external: false  // Internal only!
        targetPort: 6333
        transport: 'http'
        allowInsecure: true  // Internal traffic, no TLS needed
      }
    }

    template: {
      containers: [
        {
          name: 'qdrant'
          image: 'qdrant/qdrant:v1.12.6'  // Use a specific stable version

          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }

          // Mount persistent storage
          volumeMounts: [
            {
              volumeName: 'qdrant-data'
              mountPath: '/qdrant/storage'
            }
          ]

          // Environment variables for Qdrant
          env: [
            {
              name: 'QDRANT__SERVICE__HTTP_PORT'
              value: '6333'
            }
            {
              name: 'QDRANT__SERVICE__GRPC_PORT'
              value: '6334'
            }
          ]

          // Health probes
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/healthz'
                port: 6333
              }
              initialDelaySeconds: 10
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/readyz'
                port: 6333
              }
              initialDelaySeconds: 5
              periodSeconds: 10
            }
          ]
        }
      ]

      // Volumes - reference the storage mount
      volumes: [
        {
          name: 'qdrant-data'
          storageName: 'qdrant-storage'
          storageType: 'AzureFile'
        }
      ]

      // Scaling - Qdrant should be single instance (vector DBs don't scale horizontally)
      scale: {
        minReplicas: 1
        maxReplicas: 1
      }
    }
  }
}

// ----------------------------------------------------------------------------
// OUTPUTS
// ----------------------------------------------------------------------------

@description('Qdrant Container App ID')
output id string = qdrantApp.id

@description('Qdrant Container App name')
output name string = qdrantApp.name

@description('Qdrant internal FQDN')
output fqdn string = qdrantApp.properties.configuration.ingress.fqdn

@description('Qdrant internal URL for API to use')
output url string = 'http://${qdrantApp.properties.configuration.ingress.fqdn}'
