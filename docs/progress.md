# Progress & Plans

This document centralizes project milestones, active work, and near-term planning so we only have one place to track progress. Older planning docs now live in `docs/archive/migrated/` for reference.

## Recently Completed
- **Documentation consolidation** — active guides now live in `docs/` with all prior plans archived to avoid duplication.
- **Prometheus instrumentation** — HTTP middleware, WebSocket metrics, and a `/metrics` endpoint expose request/agent telemetry for dashboards.
- **GitHub change intake pipeline** — push webhooks now create reviews automatically and invoke the multi-agent supervisor when enabled.
- **GitHub integration sync** — API client now fetches recent commits for configured repositories with PAT authentication.
- **Document API** — list/detail/version/diff endpoints now serve real data from the document store.
- **GitHub Actions plan endpoint** — `/api/webhooks/github/actions` stores automation plans for reviewer review.

## In Progress (0–2 sprints)
- **Agent orchestration pipeline** — extend the webhook → supervisor flow with durable conversation storage and surfaced results in the reviewer UI.
- **Integration validation** — focus shifts to ServiceNow or SharePoint once GitHub is stable.
- **Documentation plan approval flow** — wire stored plans into the review UI and enable re-generation from reviewers.
- **Documentation automation** — replace stub responses in `src/api/routers/documents.py` with real queries against `Document`/`DocumentVersion` models.
- **Metrics dashboards** — convert existing Prometheus data into Grafana dashboards (templates reside under `monitoring/`).

## Next Up (2–4 sprints)
- **Search & Retrieval** — wire OpenSearch into the agent pipeline to provide context retrieval and semantic lookup for the RAG system.
- **Quality workflow** — finish human-in-the-loop review actions, including diff previews and approval automation using `ApprovalRule` logic.
- **Deployment automation** — publish container images to a registry and script an ECS/Fargate deployment (or equivalent) to replace the legacy Lambda MVP.
- **Security posture** — add secrets management integration, enforce password policies, and expand audit logging coverage in the auth service.

## Future Opportunities (4+ sprints)
- **Model Context Protocol (MCP) adoption** — operationalize the MCP server/client under `src/integrations/` to interoperate with external tools such as Claude Desktop.
- **Adaptive reasoning** — stabilize the advanced agent modules (`persistent_memory_system`, `react_reasoning_agent`, `agentic_rag_system`) with live Bedrock traffic and cost tracking.
- **UI consolidation** — finish the React admin dashboard (`src/admin/components/AdminDashboard.tsx`) and ship it alongside the API for reviewer operations.
- **Enterprise integrations** — complete browser automation via Nova Act, support SharePoint/Confluence production connectors, and deliver end-to-end change → doc update flows.

Keep this file updated as initiatives land or new priorities emerge; archive superseded plans by moving them into `docs/archive/migrated/`.
