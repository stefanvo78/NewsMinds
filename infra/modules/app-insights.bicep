// ============================================================================
// Application Insights Module
// ============================================================================
// Application Insights provides Application Performance Monitoring (APM):
// - Request tracking (latency, success rate, throughput)
// - Dependency tracking (database, HTTP, Redis calls)
// - Exception logging with stack traces
// - Custom events and metrics
// - Live metrics stream
// - Application map showing service dependencies
//
// For Python apps, integrate using:
// - opentelemetry-azure-monitor (recommended, modern)
// - opencensus-ext-azure (legacy but stable)
// ============================================================================

// ----------------------------------------------------------------------------
// PARAMETERS
// ----------------------------------------------------------------------------

@description('Name of the Application Insights resource')
param name string

@description('Azure region for the resource')
param location string

@description('Tags to apply to the resource')
param tags object = {}

@description('Log Analytics Workspace ID for backend storage')
param logAnalyticsWorkspaceId string

@description('Application type')
@allowed(['web', 'other'])
param applicationType string = 'web'

// ----------------------------------------------------------------------------
// RESOURCE
// ----------------------------------------------------------------------------

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: name
  location: location
  tags: tags
  kind: 'web'  // Kind affects default dashboards
  properties: {
    // Application type determines default views in portal
    Application_Type: applicationType

    // Flow type: for tracking user flows
    Flow_Type: 'Bluefield'

    // Request source: identifies deployment method
    Request_Source: 'IbizaAIExtension'

    // IMPORTANT: Link to Log Analytics Workspace
    // This is required for workspace-based Application Insights (v2)
    // Classic (v1) is deprecated
    WorkspaceResourceId: logAnalyticsWorkspaceId

    // Ingestion settings
    IngestionMode: 'LogAnalytics'  // Send to Log Analytics

    // Disable IP masking if you need full IP addresses
    // For GDPR compliance, keep this true
    DisableIpMasking: false

    // Public network access
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// ----------------------------------------------------------------------------
// OUTPUTS
// ----------------------------------------------------------------------------

@description('Application Insights resource ID')
output id string = appInsights.id

@description('Application Insights name')
output name string = appInsights.name

@description('Instrumentation Key (legacy, but still used by some SDKs)')
output instrumentationKey string = appInsights.properties.InstrumentationKey

@description('Connection String (preferred method for SDK configuration)')
output connectionString string = appInsights.properties.ConnectionString
