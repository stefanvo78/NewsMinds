// ============================================================================
// Container App Frontend Module (for Next.js)
// ============================================================================
// Deploys the Next.js frontend dashboard as a Container App.
// Static content served via Node.js standalone server on port 3000.
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

@description('Container Registry login server (e.g., myregistry.azurecr.io)')
param acrLoginServer string = ''

@description('Container image to deploy (defaults to placeholder if not provided)')
param containerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

@description('Minimum number of replicas')
@minValue(0)
@maxValue(10)
param minReplicas int = 0

@description('Maximum number of replicas')
@minValue(1)
@maxValue(10)
param maxReplicas int = 2

@description('Allowed IP addresses for access (CIDR notation). Empty array means public access.')
param allowedIPs array = []

// ----------------------------------------------------------------------------
// RESOURCES
// ----------------------------------------------------------------------------

resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  tags: tags

  identity: {
    type: 'SystemAssigned'
  }

  properties: {
    managedEnvironmentId: containerAppsEnvId

    configuration: {
      ingress: {
        external: true
        targetPort: 3000
        transport: 'http'
        allowInsecure: false

        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]

        ipSecurityRestrictions: [for (ip, i) in allowedIPs: {
          name: 'allow-${i}'
          ipAddressRange: endsWith(ip, '/32') ? ip : '${ip}/32'
          action: 'Allow'
        }]
      }

      registries: acrLoginServer != '' ? [
        {
          server: acrLoginServer
          identity: 'system'
        }
      ] : []
    }

    template: {
      containers: [
        {
          name: 'frontend'
          image: containerImage

          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }

          env: [
            {
              name: 'PORT'
              value: '3000'
            }
            {
              name: 'HOSTNAME'
              value: '0.0.0.0'
            }
          ]

          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/'
                port: 3000
              }
              initialDelaySeconds: 10
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/'
                port: 3000
              }
              initialDelaySeconds: 5
              periodSeconds: 10
            }
          ]
        }
      ]

      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas

        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '100'
              }
            }
          }
        ]
      }
    }
  }
}

// ----------------------------------------------------------------------------
// OUTPUTS
// ----------------------------------------------------------------------------

@description('Container App resource ID')
output id string = containerApp.id

@description('Container App name')
output name string = containerApp.name

@description('Container App FQDN')
output fqdn string = containerApp.properties.configuration.ingress.fqdn

@description('Container App principal ID (for RBAC)')
output principalId string = containerApp.identity.principalId
