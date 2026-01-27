// ============================================================================
// Container App API Module (for FastAPI)
// ============================================================================
// Deploys the FastAPI backend as a Container App instead of App Service.
// This uses consumption-based pricing and avoids VM quota issues.
//
// Benefits over App Service:
// - No VM quota required (consumption plan)
// - Scale to zero capability
// - Same infrastructure as our agents
// - Built-in container registry integration
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

@description('Application Insights connection string')
param appInsightsConnectionString string

@description('Key Vault name for secret references')
param keyVaultName string

@description('Container Registry login server (e.g., myregistry.azurecr.io)')
param acrLoginServer string = ''

@description('Container Registry name for managed identity access')
param acrName string = ''

@description('Container image to deploy (defaults to placeholder if not provided)')
param containerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

@description('Database connection string (for Azure SQL)')
@secure()
param databaseUrl string = ''

@description('JWT secret key')
@secure()
param secretKey string = ''



@description('Minimum number of replicas')
@minValue(0)
@maxValue(30)
param minReplicas int = 0  // Scale to zero for dev

@description('Maximum number of replicas')
@minValue(1)
@maxValue(30)
param maxReplicas int = 3

@description('Allowed IP addresses for access (CIDR notation). Empty array means public access.')
param allowedIPs array = []

// ----------------------------------------------------------------------------
// RESOURCES
// ----------------------------------------------------------------------------

// The Container App for our FastAPI backend
resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  tags: tags

  // Managed identity for Key Vault access
  identity: {
    type: 'SystemAssigned'
  }

  properties: {
    // Link to the Container Apps Environment
    managedEnvironmentId: containerAppsEnvId

    // Configuration for ingress, secrets, etc.
    configuration: {
      // Enable external ingress (publicly accessible)
      ingress: {
        external: true
        targetPort: 8000  // FastAPI default port
        transport: 'http'
        allowInsecure: false  // HTTPS only

        // Traffic splitting (for future blue/green deployments)
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]

        // IP restrictions - only allow specified IPs if provided
        ipSecurityRestrictions: [for (ip, i) in allowedIPs: {
          name: 'allow-${i}'
          ipAddressRange: endsWith(ip, '/32') ? ip : '${ip}/32'
          action: 'Allow'
        }]
      }

      // Secrets that can be referenced by containers
      secrets: [
        {
          name: 'appinsights-connection-string'
          value: appInsightsConnectionString
        }
        {
          name: 'database-url'
          value: databaseUrl
        }
        {
          name: 'secret-key'
          value: secretKey
        }
      ]


      // Container registry configuration
      // Using managed identity to pull images from ACR
      registries: acrLoginServer != '' ? [
        {
          server: acrLoginServer
          identity: 'system'  // Use system-assigned managed identity
        }
      ] : []

    }

    // Container template
    template: {
      containers: [
        {
          name: 'api'
          // Using a placeholder Python image initially
          // This will be replaced when we deploy our actual FastAPI app
          image: containerImage


          resources: {
            cpu: json('0.5')  // 0.5 vCPU
            memory: '1Gi'     // 1 GB RAM
          }

          // Environment variables
          env: [
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              secretRef: 'appinsights-connection-string'
            }
            {
              name: 'KEY_VAULT_URL'
              value: 'https://${keyVaultName}${environment().suffixes.keyvaultDns}/'
            }
            {
              name: 'ENVIRONMENT'
              value: contains(name, 'prod') ? 'production' : 'development'
            }
            {
              name: 'PORT'
              value: '8000'
            }
            {
              name: 'DATABASE_URL'
              secretRef: 'database-url'
            }
            {
              name: 'SECRET_KEY'
              secretRef: 'secret-key'
            }
            {
              name: 'DEBUG'
              value: 'false'
            }
          ]


          // Health probes
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 8000
              }
              initialDelaySeconds: 10
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/health'
                port: 8000
              }
              initialDelaySeconds: 5
              periodSeconds: 10
            }
          ]
        }
      ]

      // Scaling rules
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas

        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '100'  // Scale up when > 100 concurrent requests
              }
            }
          }
        ]
      }
    }
  }
}

// Note: ACR pull permission is granted via the workflow using az role assignment
// The GitHub Actions service principal needs Owner/User Access Administrator role
// on the resource group to create role assignments via Bicep

// ----------------------------------------------------------------------------
// OUTPUTS
// ----------------------------------------------------------------------------

@description('Container App resource ID')
output id string = containerApp.id

@description('Container App name')
output name string = containerApp.name

@description('Container App FQDN (fully qualified domain name)')
output fqdn string = containerApp.properties.configuration.ingress.fqdn

@description('Container App principal ID (for RBAC)')
output principalId string = containerApp.identity.principalId
