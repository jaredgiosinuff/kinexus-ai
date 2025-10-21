# Security Overview - Local Development Stack

> **⚠️ Local Development Environment Only**
>
> This security guide documents the **local FastAPI development stack** only. These security features (OAuth2, role-based auth, audit logs, admin dashboard, Cognito/SSO) are NOT in production AWS.
>
> **Production Environment**: Uses AWS Lambda with EventBridge, API Gateway webhook signature validation, and IAM permissions. No authentication system, role-based access, or admin dashboard exists in production.
>
> See [Architecture](../architecture.md) for production AWS security model.

Kinexus AI's local development environment is maturing toward an enterprise-ready security posture. This document captures what is implemented in the local dev stack and the controls that are planned.

## Implemented Controls
- **Authentication** — FastAPI OAuth2 password flow backed by bcrypt hashes (`src/api/routers/auth.py`). Tokens expire after `ACCESS_TOKEN_EXPIRE_MINUTES` and include user IDs only.
- **Authorization** — Role-based checks via `UserRole` enum (viewer, reviewer, lead_reviewer, admin). Dependency helpers in `src/api/dependencies.py` enforce scope.
- **Audit Logging** — Login attempts and key review actions are written to the `audit_logs` table with IP + user agent metadata.
- **Secrets** — Development secrets live in `.env`. Production stacks should load from a secrets manager; the code reads standard env vars.
- **Input Validation** — Pydantic models validate payloads across the API surface.

## In Progress / Planned
- **Multi-factor auth & SSO** — Integrate with Cognito or another IdP. The admin dashboard already assumes provider switching.
- **Session Management** — Add refresh tokens and manual revoke endpoints.
- **Secrets Management** — Wire `.env` loaders to pull secrets from AWS Secrets Manager or HashiCorp Vault in non-dev environments.
- **Rate Limiting & WAF** — Introduce throttling middleware and infrastructure-level protection once the public API is exposed.
- **Data Encryption** — Use TLS for external traffic (handled by your ingress) and enable encryption at rest on managed services.
- **Security Testing** — Add bandit/Snyk or similar scanners to CI.

## Security Operations Checklist
- Rotate admin passwords regularly; maintain at least two admin accounts.
- Monitor the `audit_logs` table for failed login spikes or privilege escalations.
- Store integration credentials outside Git. Add them to your secret manager and inject via environment variables or mounted files.
- Run `pytest tests/test_mcp_integration.py` and `pytest tests/test_model_integration.py` after modifying Bedrock credentials or integration secrets to ensure nothing broke.
- Document any temporary security exceptions in `docs/roadmap.md` and create follow-up tasks.

Update this file whenever new controls are delivered or risk assumptions change.
