// ============================================================================
// Azure Monitor Alerts Module
// ============================================================================
// Configures alerts for monitoring the NewsMinds application.
// Alerts notify when issues occur (high error rates, slow responses, etc.)
// ============================================================================

// ----------------------------------------------------------------------------
// PARAMETERS
// ----------------------------------------------------------------------------

@description('Base name for alert resources')
param namePrefix string

@description('Azure region')
param location string

@description('Tags to apply')
param tags object = {}

@description('Application Insights resource ID')
param appInsightsId string

@description('Container App resource ID')
param containerAppId string

@description('Email addresses for alert notifications')
param alertEmailAddresses array = []

// ----------------------------------------------------------------------------
// RESOURCES
// ----------------------------------------------------------------------------

// Action Group - defines who gets notified
resource actionGroup 'Microsoft.Insights/actionGroups@2023-01-01' = {
  name: '${namePrefix}-alerts-ag'
  location: 'global'
  tags: tags
  properties: {
    groupShortName: 'NMindsAlert'
    enabled: true
    emailReceivers: [for email in alertEmailAddresses: {
      name: 'Email-${split(email, '@')[0]}'
      emailAddress: email
      useCommonAlertSchema: true
    }]
  }
}

// Alert: High Error Rate (5xx errors)
resource highErrorRateAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${namePrefix}-high-error-rate'
  location: 'global'
  tags: tags
  properties: {
    description: 'Alert when error rate exceeds 5% over 5 minutes'
    severity: 2  // Warning
    enabled: true
    scopes: [appInsightsId]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT5M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'HighErrorRate'
          metricName: 'requests/failed'
          metricNamespace: 'microsoft.insights/components'
          operator: 'GreaterThan'
          threshold: 10
          timeAggregation: 'Count'
          criterionType: 'StaticThresholdCriterion'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

// Alert: Slow Response Time
resource slowResponseAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${namePrefix}-slow-response'
  location: 'global'
  tags: tags
  properties: {
    description: 'Alert when average response time exceeds 2 seconds'
    severity: 3  // Informational
    enabled: true
    scopes: [appInsightsId]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT5M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'SlowResponse'
          metricName: 'requests/duration'
          metricNamespace: 'microsoft.insights/components'
          operator: 'GreaterThan'
          threshold: 2000  // 2 seconds in milliseconds
          timeAggregation: 'Average'
          criterionType: 'StaticThresholdCriterion'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

// Alert: Container App Health
resource containerHealthAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${namePrefix}-container-health'
  location: 'global'
  tags: tags
  properties: {
    description: 'Alert when container app replicas drop to zero unexpectedly'
    severity: 1  // Error
    enabled: true
    scopes: [containerAppId]
    evaluationFrequency: 'PT1M'
    windowSize: 'PT5M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'NoReplicas'
          metricName: 'Replicas'
          metricNamespace: 'Microsoft.App/containerApps'
          operator: 'LessThan'
          threshold: 1
          timeAggregation: 'Average'
          criterionType: 'StaticThresholdCriterion'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

// ----------------------------------------------------------------------------
// OUTPUTS
// ----------------------------------------------------------------------------

@description('Action Group ID')
output actionGroupId string = actionGroup.id

@description('Action Group Name')
output actionGroupName string = actionGroup.name
