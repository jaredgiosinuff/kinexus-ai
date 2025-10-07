# Integration Overview

Kinexus AI ships with a set of integration adapters under `src/integrations/`. Most adapters share a common base class (`BaseIntegration`) that tracks sync status, retries, and logging. This document records the maturity of each connector.

| Adapter | Status | Notes |
|---------|--------|-------|
| `monday_integration.py` | ✅ Working prototype | Supports connection tests, board sync, and GraphQL queries. Requires API key and board IDs in integration config. |
| `github_integration.py` | ✅ Commit sync | Fetches recent commits for configured repositories using personal access token authentication; ensure PAT scopes include `repo`. |
| `servicenow_integration.py` | ⚠️ Scaffold | Defines REST operations but lacks end-to-end tests. Credentials and table mappings pending. |
| `sharepoint_integration.py` & `sharepoint_client.py` | ⚠️ Scaffold | Auth/session helpers exist; content sync still TODO. |
| `jira_integration.py` | ⚠️ Scaffold | Basic request helpers, awaiting workflow logic. |
| `confluence_client.py` | ⚠️ Scaffold | HTTP client with auth helpers; no orchestration yet. |
| `github_actions_integration.py` | 💤 Archived | GitHub Actions workflow documentation moved to `docs/archive/legacy`; use for reference only. |
| `mcp_server.py` / `mcp_client.py` | 🧪 Experimental | Implements Model Context Protocol server + client stubs; requires further validation and packaging. |
| `nova_act_automation.py` | 🧪 Experimental | Automates browser flows via Nova Act. Runs locally with Bedrock access; production pipeline still to-do. |

## Adding a New Integration
1. Subclass `BaseIntegration` and implement `test_connection`, `sync`, and optional `process_webhook`.
2. Register the integration with the `IntegrationService` (`src/core/services/integration_service.py`).
3. Provide configuration schema and secrets management strategy.
4. Add tests exercising happy-path sync and error handling.

## Configuration Storage
Integration metadata is stored in the database (`integrations` table) and can be seeded via `scripts/setup_admin_system.py`. The admin API will expose CRUD endpoints once the dashboard is completed.
