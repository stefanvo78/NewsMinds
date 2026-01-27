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

// Azure region
param location = 'eastus2'

// Project name for resource naming
param projectName = 'nminds'

// SQL Server credentials - NEVER commit real passwords!
// These are placeholders - pass real values via CLI or Key Vault
// Use: --parameters sqlAdminLogin=xxx sqlAdminPassword=xxx
param sqlAdminLogin = ''  // Will be provided at deployment
param sqlAdminPassword = ''  // Will be provided at deployment

// JWT secret key for authentication - provided via GitHub secrets
param secretKey = ''  // Will be provided at deployment

// IP allowlist for API access
// Update this list and redeploy to change who can access the API
// Format: array of IP addresses (will be converted to /32 CIDR)
param allowedIPs = [
  '38.141.192.220'  // Stefan's home IP
]

// Resource tags for organization and cost tracking
param tags = {
  Environment: 'Development'
  Project: 'NewsMinds'
  CostCenter: 'AI-Research'
  Owner: 'your-email@example.com'
}
