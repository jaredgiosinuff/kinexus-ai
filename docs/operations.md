# Operations & Support

This guide covers day-two responsibilities: monitoring the system, responding to incidents, and performing routine maintenance.

## Health Endpoints
- `GET /health` — verifies API availability and database connectivity.
- `GET /api/admin/system-status` — high-level status snapshot (currently returns stub data; extend once metrics are wired).
- `POST /api/webhooks/github/actions` — accepts GitHub Actions payloads (plan-only mode) when `GITHUB_ACTIONS_WEBHOOK_TOKEN` is configured.
- `GET /api/documentation-plans` — list PR automation plans awaiting review; `POST /api/documentation-plans/{id}/link-review` ties them to a specific review.
- `POST /api/documentation-plans/{id}/rerun` — regenerate a plan in plan-only mode (set `execute_updates=true` to run the full pipeline once approved).
- WebSocket heartbeat — clients should reconnect if the `/api/ws` channel drops.

## Logging
The application uses the structured logger in `src/core/services/logging_service.py` (backed by `structlog`). Logs are emitted in JSON when `LOG_FORMAT=json` and plain text otherwise.

- Local follow: `podman-compose logs -f api`
- Change severity via `LOG_LEVEL` env var (`DEBUG`, `INFO`, `WARNING`, `ERROR`).
- Audit events are persisted in the `audit_logs` table; query via psql when investigating access issues.

## Metrics & Observability
- Prometheus scrape endpoint runs on `http://localhost:8090/` by default (override with the `METRICS_PORT` setting). The server starts automatically when `ENABLE_METRICS=true` and a fallback `/metrics` HTTP route is available if you cannot open that port.
- HTTP middleware feeds `record_request`/`record_error`, so `/api/admin/metrics` now reports real request rates, error ratios, latency, model costs, and token usage.
- Agent modules already call `record_agent_performance`; ensure long-running agent jobs import `metrics_service` if you add new workers.
- Grafana/Prometheus dashboard templates remain under `monitoring/` for future reactivation.

## Scheduled Tasks / Background Work
Automated agent execution runs during GitHub push intake when `ENABLE_MULTI_AGENT_AUTOMATION=true`; otherwise the webhook stores changes for manual review. Operate the system by:
1. Inspecting pending reviews via `/api/reviews`.
2. Running agent scripts manually for high-impact changes (e.g., `python src/agents/multi_agent_supervisor.py --help`).
3. Completing reviews through the API or upcoming UI.

## Database Maintenance
- Run regular backups of the PostgreSQL `kinexus_dev` database using `pg_dump` or managed service snapshots.
- Alembic migrations live in `alembic/`. Apply pending migrations after pulling new code: `alembic upgrade head`.
- Monitor connection counts and slow queries; hooks exist in `MetricsService` but can also be captured via native Postgres tooling.

## Redis & Cache
Redis currently caches integration state and may hold transient conversation data. Evict keys safely with `FLUSHDB` only during maintenance windows.

## Disaster Recovery Checklist
1. **Database**: restore latest snapshot, replay required migrations.
2. **Secrets**: rotate credentials stored in `.env` or secret manager.
3. **Containers**: rebuild with `podman-compose build` and redeploy.
4. **Integrations**: revalidate webhook signatures and API tokens.

## Escalation
- Reviewers/admins manage access via `/api/auth` endpoints. Ensure at least two admin accounts exist.
- Bedrock service disruptions: fall back to `mock-bedrock` responses to keep manual review pathways functional.
- Integration outages: disable the integration via configuration to prevent cascading failures, then re-enable after verifying tokens and network access.
