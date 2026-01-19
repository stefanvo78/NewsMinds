// ============================================================================
// Development Environment Parameters
// ============================================================================
// These parameters configure Azure resources for the development environment.
// Dev uses:
// - Cheaper SKUs (Burstable, Basic tiers)
// - Less redundancy (no HA, no geo-backup)
// - Shorter retention periods
// - Relaxed security (public access enabled)
//
// Usage:
//   az deployment group create \
//     --resource-group newsminds-dev-rg \
//     --template-file infra/main.bicep \
//     --parameters infra/environments/dev.bicepparam \
//     --parameters postgresAdminLogin=newsmindsadmin \
//     --parameters postgresAdminPassword=<secure-password>
// ============================================================================

using '../main.bicep'

// Environment identifier
param environment = 'dev'

// Azure region - using eastus (PostgreSQL Flexible Server available here)
param location = 'eastus'

// Project name for resource naming
param projectName = 'newsminds'

// PostgreSQL credentials - NEVER commit real passwords!
// These are placeholders - pass real values via CLI or Key Vault
// Use: --parameters postgresAdminLogin=xxx postgresAdminPassword=xxx
param postgresAdminLogin = ''  // Will be provided at deployment
param postgresAdminPassword = ''  // Will be provided at deployment

// Resource tags for organization and cost tracking
param tags = {
  Environment: 'Development'
  Project: 'NewsMinds'
  CostCenter: 'AI-Research'
  Owner: 'your-email@example.com'
}
