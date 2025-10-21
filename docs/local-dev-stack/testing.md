# Testing Strategy - Local Development Stack

> **⚠️ Local Development Environment Only**
>
> This testing guide documents the **local FastAPI development stack** only. These tests (LocalStack, MCP integration, compose stack, PostgreSQL, Redis, mock Bedrock) are NOT applicable to production AWS.
>
> **Production Environment**: AWS Lambda functions are tested via CloudWatch Logs monitoring, manual end-to-end workflow testing with Jira/Confluence, and GitHub Actions deployment validation.
>
> See [Architecture](../architecture.md) for production monitoring and [Deployment Guide](../deployment.md) for production testing procedures.

Kinexus AI's local development environment uses Pytest for automation. Most suites exercise integration points (agents, AWS mocks, deployment helpers) rather than isolated unit tests, so expect to run them with the container stack online.

## Test Matrix
| File | Purpose | Dependencies |
|------|---------|--------------|
| `tests/test_mcp_integration.py` | Verifies Model Context Protocol server/client wiring | LocalStack or mock server, MCP configuration env vars |
| `tests/test_model_integration.py` | Validates model catalog, Bedrock agent wrappers, and fallback logic | `boto3` mocked responses, Bedrock credentials if running live |
| `tests/test_lambda_deployment.py` | Smoke tests for packaging Lambda bundles | `lambda_layer.zip`, AWS SDK |
| `tests/test_metrics_service.py` | Ensures metrics snapshot calculations work | Prometheus client, asyncio |
| `tests/run_all_tests.py` | Orchestrator to run the full suite sequentially | Invokes the tests above |

## Running Tests
```bash
pytest tests/                            # full run
pytest tests/test_mcp_integration.py     # targeted module
pytest --cov=src tests/                  # run with coverage
```

Tips:
- Start the compose stack first so services such as Postgres, Redis, LocalStack, and the mock Bedrock server are reachable.
- Export `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_REGION` if the test touches Bedrock; use dummy values for the mock environment.
- Some suites allocate significant memory (e.g., numpy vector operations). Run them in isolation if you encounter OOM issues inside containers.

## Linting & Formatting (Optional)
We do not enforce a single formatter yet, but contributors are encouraged to use:
- `black` / `isort` for Python
- `ruff` or `flake8` for linting
- `mypy` for type checking core services

Add a pre-commit configuration locally if you want automatic checks: `pip install pre-commit && pre-commit install`.

## Continuous Integration
A GitHub Actions workflow for documentation updates exists (archived). CI for tests is under construction; run `pytest` locally before opening a PR.
