# Documentation Workflow

This file explains how Kinexus AI tracks knowledge assets today and how future automation will interact with them.

## Current Model

### Storage
- **Documents (`documents` table)** — one record per managed artifact. Tracks source system, external identifiers, document type, and current version.
- **Document Versions (`document_versions` table)** — stores Markdown content, change summaries, AI metadata, and author information.
- **Reviews (`reviews` table)** — links change events to proposed document versions, capturing status, decisions, and reviewer feedback.
- **Audit Logs (`audit_logs` table)** — records authentication events and review actions.

PostgreSQL persists all of the above. Assets remain in the primary system of record (GitHub, Confluence, etc.); integrations push changes back once approved. Until the outbound sync is automated, reviewers manually apply updates using the information captured in Kinexus.

### Lifecycle
1. **Change Intake** — webhook or API call posts a change; the API creates a review and placeholder document version if necessary.
2. **Analysis** — agents (manual today) or reviewers determine the affected documents and update the draft content.
3. **Review** — reviewers approve or request changes via `/api/reviews`.
4. **Publish** — integrations commit updates back to their origin (GitHub PR, Confluence page, etc.). Automated publishing is on the roadmap.

## Planned Enhancements
- **Automated Diffing** — compute Markdown diffs between `DocumentVersion` entries to help reviewers visualize changes.
- **Cross-Repository Index** — leverage OpenSearch to map change events to relevant documentation automatically.
- **Approval Rules** — enable `ApprovalRule` models so high-impact changes require elevated sign-off.
- **External Storage Hooks** — optionally mirror documents to S3 for archival and analytics while keeping primary sources authoritative.

## Naming Conventions
- Document types follow snake_case (e.g., `api_reference`, `runbook`, `user_guide`).
- Source systems use short identifiers (`github`, `confluence`, `sharepoint`).
- Integration configs should include human-readable titles plus external IDs to ensure clarity in UI listings.

Keep this document updated when you add new lifecycle stages or storage layers.
