// ============================================================================
// Log Analytics Workspace Module
// ============================================================================
// Log Analytics is Azure's centralized logging service.
// It collects logs from:
// - Application Insights (traces, exceptions, metrics)
// - Container Apps (stdout/stderr, system logs)
// - Azure resources (diagnostic logs)
//
// You can query logs using Kusto Query Language (KQL).
// Example: traces | where message contains "error" | take 100
// ============================================================================

// ----------------------------------------------------------------------------
// PARAMETERS
// ----------------------------------------------------------------------------

@description('Name of the Log Analytics Workspace')
param name string

@description('Azure region for the workspace')
param location string

@description('Tags to apply to the resource')
param tags object = {}

@description('Log retention period in days (30-730)')
@minValue(30)
@maxValue(730)
param retentionInDays int = 30  // 30 days is free tier

@description('SKU for the workspace')
@allowed(['Free', 'PerGB2018', 'PerNode', 'Premium', 'Standalone', 'Standard'])
param sku string = 'PerGB2018'  // Pay-as-you-go, most common choice

// ----------------------------------------------------------------------------
// RESOURCE
// ----------------------------------------------------------------------------

resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    // Retention: how long to keep logs
    // 30 days is free, longer retention costs extra
    retentionInDays: retentionInDays

    // SKU determines pricing model
    // PerGB2018: Pay per GB ingested (best for most workloads)
    sku: {
      name: sku
    }

    // Features
    features: {
      // Enable log search for Application Insights
      searchVersion: 1
      // Enable container insights integration
      enableLogAccessUsingOnlyResourcePermissions: true
    }
  }
}

// ----------------------------------------------------------------------------
// OUTPUTS
// ----------------------------------------------------------------------------

@description('The workspace resource ID')
output workspaceId string = logAnalyticsWorkspace.id

@description('The workspace name')
output name string = logAnalyticsWorkspace.name

@description('The workspace customer ID (used for agent configuration)')
output customerId string = logAnalyticsWorkspace.properties.customerId

@description('The primary shared key (for agent authentication)')
output primarySharedKey string = logAnalyticsWorkspace.listKeys().primarySharedKey
