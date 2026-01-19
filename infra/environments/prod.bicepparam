// ============================================================================
// Production Environment Parameters
// ============================================================================
// These parameters configure Azure resources for production.
// Production uses:
// - Production-grade SKUs (General Purpose, Standard tiers)
// - High availability (zone redundancy, replicas)
// - Longer retention (backups, logs)
// - Strict security (private endpoints, firewall rules)
//
// Usage:
//   az deployment group create \
//     --resource-group newsminds-prod-rg \
//     --template-file infra/main.bicep \
//     --parameters infra/environments/prod.bicepparam \
//     --parameters postgresAdminLogin=<from-keyvault> \
//     --parameters postgresAdminPassword=<from-keyvault>
// ============================================================================

using '../main.bicep'

// Environment identifier
param environment = 'prod'

// Azure region - same region as dev for simplicity
// Consider paired regions for DR: westus2 + eastus2
param location = 'westus2'

// Project name
param projectName = 'newsminds'

// PostgreSQL credentials - in production, use Azure Key Vault
// or secure CI/CD variable injection
param postgresAdminLogin = ''  // From CI/CD secrets
param postgresAdminPassword = ''  // From CI/CD secrets

// Production tags
param tags = {
  Environment: 'Production'
  Project: 'NewsMinds'
  CostCenter: 'AI-Research'
  Owner: 'your-email@example.com'
  Compliance: 'Internal'
  DataClassification: 'Confidential'
}
