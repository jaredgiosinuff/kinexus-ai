# Deployment Guide

Kinexus AI currently prioritizes the containerized FastAPI stack for day-to-day development. A legacy serverless footprint built for the original hackathon remains in `infrastructure/` for reference but is not the primary deployment target.

## Environments
- **Local (default)**: `docker-compose.yml` + helper scripts. Treat this as the authoritative integration environment.
- **Staging/Production (planned)**: Fargate or EC2 deployment running the same containers as the compose stack. IaC definitions are being evaluated; use manual deployment for now.
- **Legacy MVP (optional)**: AWS CDK stack (`infrastructure/app.py`) that provisions S3, DynamoDB, EventBridge, and Lambda functions. Kept for historical context.

## Container Images
1. Ensure dependencies are installed: `pip install -r requirements.txt` (for packaging scripts) and `npm install` (for CDK tooling).
2. Build images locally:
   ```bash
   podman-compose build   # or docker-compose build
   ```
3. Tag and push to your registry of choice if you are deploying to a remote cluster.

### Configuration
Runtime configuration is loaded primarily from environment variables. The `.env` produced by `./scripts/dev-setup.sh` is a good starting point. For non-development deployments:
- Rotate `SECRET_KEY`
- Point database/redis hosts at managed services
- Provide AWS credentials only when interacting with real Bedrock or AWS resources
- Configure integration credentials through your secret store of choice (Vault, Secrets Manager, etc.)

## Manual Server Deployment (Interim)
1. Provision PostgreSQL 15+, Redis 7+, and (optionally) OpenSearch 2.x.
2. Run Alembic migrations:
   ```bash
   ALEMBIC_CONFIG=alembic.ini alembic upgrade head
   ```
3. Start the API process (systemd, supervisor, or container runtime):
   ```bash
   uvicorn src.api.main:app --host 0.0.0.0 --port 8000
   ```
4. Run background workers or cron jobs to trigger agent routines as needed (currently manual scripts).
5. Serve the frontend from a static host (e.g., S3 + CloudFront) after running `npm install && npm run build` inside `frontend/`.

## Legacy CDK Stack
If you need to replicate the original AWS Lambda demo:

```bash
npm install
npm run build        # packages lambda layer
npx cdk deploy       # deploys KinexusAIMVPStack
```

Prerequisites:
- AWS account with Bedrock model access
- `lambda_layer.zip` build succeeds (requires `pip install -r requirements.txt -t lambda_layer/python`)
- IAM permissions to create buckets, DynamoDB tables, EventBridge rules, and Lambda functions

> **Note:** The serverless stack persists in `docs/archive/legacy/` documentation; treat it as historical until the modern container deployment is scripted in IaC.

## Release Checklist
- [ ] Application container images built and pushed
- [ ] Database migrations applied
- [ ] `.env` / secret material updated for target environment
- [ ] Smoke tests executed (`pytest tests/test_mcp_integration.py`, `pytest tests/test_model_integration.py`)
- [ ] Monitoring endpoints verified (`/health` and `/metrics` if enabled)
