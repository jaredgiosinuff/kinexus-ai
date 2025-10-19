# Documentation Workflow

This document explains how Kinexus AI automatically generates, reviews, and publishes documentation using an event-driven serverless architecture on AWS.

## Production Workflow (AWS)

### Overview

Kinexus AI runs a **fully automated documentation workflow** with human-in-the-loop approval:

1. **Jira ticket closed** → AI generates documentation
2. **Review ticket auto-created** → Visual diff presented
3. **Human approves** → Documentation published to Confluence

### Complete Workflow Phases

#### Phase 1: Change Detection (Jira Webhook)

**Trigger:** Jira ticket status changes (created, updated, closed)

**Lambda:** `JiraWebhookHandler` (src/lambdas/jira_webhook_handler.py:30s)

**Critical: Status Transition Requirements**

The webhook handler uses **smart filtering** to avoid generating documentation for every ticket closure (e.g., old ticket cleanup, won't-fix bugs).

**Valid Transitions (Will Trigger):**
- ✅ In Progress → Done
- ✅ In Review → Done
- ✅ Testing → Closed
- ✅ QA → Resolved

**Invalid Transitions (Will Skip):**
- ❌ To Do → Done (not actively worked on)
- ❌ Backlog → Closed (just cleanup)
- ❌ Open → Won't Fix (no work done)

**Exception: `needs-docs` Label**
- Bypasses status transition checks
- Forces documentation generation for any ticket

**Smart Filtering Logic:**
```python
# Determines if documentation is needed based on:
1. Status transition TO: Done/Closed/Resolved/Complete
2. Status transition FROM: In Progress/In Review/Testing/QA
3. OR has label: needs-docs, new-feature, breaking-change, api-change
4. Issue type: Story, Epic, Task, Feature, Improvement
5. NOT: Bug (unless has needs-docs label)
6. NOT: Too old (>30 days since creation)
7. NOT: Has skip labels (no-docs, internal-only, tech-debt)
```

**How to Add Labels:**
1. Open ticket: https://yourcompany.atlassian.net/browse/TOAST-42
2. Find **Labels** field (Details section, right sidebar)
3. Click the field and type `needs-docs`
4. Press Enter to save

**Actions:**
1. Parse Jira webhook payload
2. Extract documentation context (summary, description, labels, custom fields)
3. Create change record in DynamoDB (`kinexus-changes` table)
4. Emit EventBridge event: `kinexus.jira/ChangeDetected`

**Example Change Record:**
```json
{
  "change_id": "jira_TOAST-42_1729374000",
  "ticket_key": "TOAST-42",
  "summary": "Add OAuth2 authentication to API",
  "status": "Done",
  "labels": ["needs-docs", "api", "breaking-change"],
  "documentation_context": {
    "issue_type": "Story",
    "priority": "High",
    "description": "Implement OAuth2 flow...",
    "affected_components": ["authentication", "api"]
  },
  "timestamp": "2025-10-19T18:30:00Z"
}
```

---

#### Phase 2: Documentation Generation (AI/Bedrock)

**Trigger:** EventBridge `ChangeDetected` event

**Lambda:** `DocumentOrchestrator` (src/lambdas/document_orchestrator.py:5min)

**Process:**
1. Receive change event from EventBridge
2. Query DynamoDB for change details
3. **Invoke Claude (AWS Bedrock)** with change context:
   ```python
   prompt = f"""
   Analyze this Jira ticket and generate documentation:

   Ticket: {ticket_key}
   Summary: {summary}
   Description: {description}
   Labels: {labels}

   Generate comprehensive documentation covering:
   - Feature overview
   - Implementation details
   - API changes
   - Migration guide (if breaking change)
   - Examples and code snippets
   """
   ```
4. Claude generates markdown documentation
5. **Store content in S3**: `s3://kinexus-documents-{account}/documents/{document_id}.md`
6. **Store metadata in DynamoDB** (`kinexus-documents` table):
   ```json
   {
     "document_id": "doc_api-auth_v3",
     "title": "API Authentication Guide",
     "version": 3,
     "s3_location": "s3://.../documents/doc_api-auth_v3.md",
     "source_change_id": "jira_TOAST-42_1729374000",
     "status": "pending_review",
     "previous_version": "doc_api-auth_v2",
     "created_at": "2025-10-19T18:32:15Z"
   }
   ```
7. Emit EventBridge event: `kinexus.orchestrator/DocumentGenerated`

---

#### Phase 3: Review Ticket Creation (Visual Diff)

**Trigger:** EventBridge `DocumentGenerated` event

**Lambda:** `ReviewTicketCreator` (src/lambdas/review_ticket_creator.py:60s)

**Process:**
1. Receive document generation event
2. Retrieve **previous version** from S3 (if exists)
3. Retrieve **current version** from S3
4. **Generate visual diffs** using `diff_generator.py`:
   - **HTML diff** with side-by-side and unified views
   - **Red highlighting** for deletions
   - **Green highlighting** for additions
   - **Line numbers** for reference
5. **Detect image changes**:
   - Parse markdown for `![alt](url)` and `<img>` tags
   - Compare image references between versions
   - Flag added/removed images
6. **Upload HTML diff to S3**: `s3://.../diffs/{document_id}_diff_{timestamp}.html`
7. Generate presigned URL (7-day expiry)
8. **Create Jira review ticket** using Jira REST API:
   ```python
   {
     "fields": {
       "project": {"key": "TOAST"},
       "summary": "Review: API Authentication Guide",
       "description": {
         # Atlassian Document Format (ADF)
         # Includes:
         # - Document metadata
         # - Link to visual diff
         # - Text summary of changes
         # - Image change warnings
         # - Approval instructions
       },
       "issuetype": {"name": "Task"},
       "labels": ["documentation-review", "auto-generated", "kinexus-ai"]
     }
   }
   ```
9. Update document metadata with review ticket info

**Example Review Ticket:**
```
TOAST-43: Review: API Authentication Guide

📚 Documentation Review Required

Document: API Authentication Guide
Document ID: doc_api-auth_v3
Version: 3
Source Ticket: TOAST-42

─────────────────────────────────────
📊 Review Changes

🔗 View Full Diff (HTML)
   [https://kinexus-documents...presigned-url]

Changes Summary:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🟢 ADDED (lines 45-78):
  + ## OAuth2 Flow
  + 1. Authorization Request...

🔴 REMOVED (lines 23-34):
  - ## API Key Authentication...

📊 Summary: 34 additions, 12 deletions
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

─────────────────────────────────────
✅ How to Approve

Comment on this ticket with:
• APPROVED - Approve and publish
• REJECTED - Reject and regenerate
• NEEDS REVISION - Request changes
```

---

#### Phase 4: Human Review

**Actor:** Technical writer, documentation reviewer, or subject matter expert

**Actions:**
1. Receive Jira assignment (or check review queue)
2. Open review ticket (e.g., `TOAST-43`)
3. Click **"View Full Diff (HTML)"** link
4. Review visual diff:
   - Toggle between side-by-side and unified views
   - Check red deletions and green additions
   - Review image changes
5. Make decision

---

#### Phase 5: Approval Decision

**Actor:** Human reviewer

**Options:**

**A. Approve:**
```
APPROVED

Looks great! OAuth2 flow is clearly explained.
Minor typo fixed in migration guide.
```

**B. Reject:**
```
REJECTED

Missing Python SDK integration examples.
Need more detailed error handling section.
```

**C. Request Revision:**
```
NEEDS REVISION

Please add:
1. Diagram showing OAuth2 flow
2. Example for refresh token rotation
3. Security best practices section
```

---

#### Phase 6: Approval Processing (Confluence Publication)

**Trigger:** Jira webhook on `comment_created` event

**Lambda:** `ApprovalHandler` (src/lambdas/approval_handler.py:90s)

**Process:**
1. Receive comment webhook from Jira
2. Check if ticket has `documentation-review` label
3. **Parse comment** for approval patterns:
   ```python
   APPROVAL_PATTERNS = [
       r"(?i)^approved?$",
       r"(?i)^lgtm$",
       r"(?i)^✅",
       r"(?i)^ship\s*it$",
   ]
   ```
4. **If APPROVED:**
   a. Download approved content from S3
   b. Convert markdown to Confluence storage format (HTML)
   c. **Publish to Confluence** using Confluence REST API:
      - Update existing page (if page_id exists)
      - Create new page (if first version)
      - Add version comment: "Updated OAuth2 authentication - TOAST-42"
   d. Update DynamoDB:
      ```json
      {
        "status": "published",
        "confluence_url": "https://.../wiki/spaces/SD/pages/98310",
        "approved_by": "sarah.techwriter",
        "approved_at": "2025-10-19T18:45:00Z"
      }
      ```
   e. **Comment on review ticket** (TOAST-43):
      ```
      ✅ Documentation approved and published!

      📚 Confluence: https://.../wiki/spaces/SD/pages/98310

      Approved by: Sarah TechWriter
      ```
   f. Transition review ticket to "Done"
   g. **Comment on source ticket** (TOAST-42):
      ```
      📚 Documentation published: https://.../wiki/spaces/SD/pages/98310
      ```
   h. Emit EventBridge event: `kinexus.approval/DocumentationPublished`

5. **If REJECTED:**
   - Update DynamoDB: `status = "rejected"`
   - Comment on review ticket
   - Transition to "Done"

6. **If NEEDS REVISION:**
   - Update DynamoDB: `status = "needs_revision"`
   - Comment on review ticket
   - Keep ticket open for follow-up

---

#### Phase 7: Published Documentation

**Result:** Documentation is **live on Confluence** with:
- Version tracking (auto-incremented)
- Edit history and audit trail
- Link back to source Jira ticket
- Labels and metadata

**Example Confluence Page:**
```
Page: ToastTracker Pro - API Documentation
Section: Authentication
Version: 4 (auto-incremented)
Updated: 2025-10-19 18:52:00
Editor: Kinexus AI Bot
Comment: "Updated OAuth2 authentication - TOAST-42"
Labels: #api #authentication #oauth2 #breaking-change
```

---

## Storage Model

### DynamoDB Tables

**kinexus-changes:**
```json
{
  "change_id": "jira_TOAST-42_1729374000",  // PK
  "ticket_key": "TOAST-42",
  "summary": "Add OAuth2 authentication",
  "status": "Done",
  "labels": ["needs-docs", "api"],
  "documentation_context": {...},
  "timestamp": "2025-10-19T18:30:00Z"
}
```

**kinexus-documents:**
```json
{
  "document_id": "doc_api-auth_v3",  // PK
  "title": "API Authentication Guide",
  "version": 3,
  "s3_location": "s3://.../documents/doc_api-auth_v3.md",
  "source_change_id": "jira_TOAST-42_1729374000",
  "status": "published",
  "previous_version": "doc_api-auth_v2",
  "review_ticket_key": "TOAST-43",
  "review_ticket_url": "https://.../browse/TOAST-43",
  "diff_url": "https://.../diffs/...presigned",
  "confluence_url": "https://.../wiki/spaces/SD/pages/98310",
  "approved_by": "sarah.techwriter",
  "approved_at": "2025-10-19T18:45:00Z",
  "created_at": "2025-10-19T18:32:15Z"
}
```

### S3 Structure

```
s3://kinexus-documents-{account}-{region}/
├── documents/
│   ├── doc_api-auth_v1.md
│   ├── doc_api-auth_v2.md
│   ├── doc_api-auth_v3.md
│   └── ...
└── diffs/
    ├── doc_api-auth_v3_diff_1729374735.html
    └── ...
```

**Versioning:** Enabled on S3 bucket for audit trail

---

## Event-Driven Architecture

### EventBridge Events

**1. ChangeDetected**
```json
{
  "source": "kinexus.jira",
  "detail-type": "ChangeDetected",
  "detail": {
    "change_id": "jira_TOAST-42_1729374000",
    "ticket_key": "TOAST-42"
  }
}
```
→ Triggers: `DocumentOrchestrator`

**2. DocumentGenerated**
```json
{
  "source": "kinexus.orchestrator",
  "detail-type": "DocumentGenerated",
  "detail": {
    "document_id": "doc_api-auth_v3",
    "title": "API Authentication Guide",
    "version": 3
  }
}
```
→ Triggers: `ReviewTicketCreator`

**3. DocumentationPublished**
```json
{
  "source": "kinexus.approval",
  "detail-type": "DocumentationPublished",
  "detail": {
    "document_id": "doc_api-auth_v3",
    "confluence_url": "https://.../wiki/spaces/SD/pages/98310",
    "approved_by": "sarah.techwriter"
  }
}
```
→ Future: Triggers notifications, metrics, etc.

---

## Naming Conventions

- **Document IDs**: `doc_{topic}_{version}` (e.g., `doc_api-auth_v3`)
- **Change IDs**: `jira_{ticket-key}_{timestamp}` (e.g., `jira_TOAST-42_1729374000`)
- **S3 Keys**: `documents/{document_id}.md` or `diffs/{document_id}_diff_{timestamp}.html`
- **Jira Labels**: `documentation-review`, `auto-generated`, `kinexus-ai`
- **Document Types**: `api_reference`, `user_guide`, `runbook`, `architecture`, `troubleshooting`

---

## Configuration

### Environment Variables (Lambda Functions)

```bash
# DynamoDB
CHANGES_TABLE=kinexus-changes
DOCUMENTS_TABLE=kinexus-documents

# S3
DOCUMENTS_BUCKET=kinexus-documents-{account}-{region}

# EventBridge
EVENT_BUS=kinexus-events

# Jira/Confluence
JIRA_BASE_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=user@company.com
JIRA_API_TOKEN={secret}
CONFLUENCE_URL=https://yourcompany.atlassian.net/wiki
JIRA_PROJECT_KEY=YOUR-PROJECT-KEY
```

### Jira Webhooks

**Webhook #1: Main Documentation Tracker**
- URL: `{API}/webhooks/jira`
- Events: `jira:issue_updated`, `jira:issue_created`
- For: Original ticket changes

**Webhook #2: Approval Handler**
- URL: `{API}/webhooks/approval`
- Events: `comment_created`
- For: Review ticket comments

---

## Planned Enhancements

- **Automated Image Generation** — AI generates diagrams from descriptions using Mermaid/PlantUML
- **Revision Workflow** — Track changes after "NEEDS REVISION" feedback
- **Multi-Stage Approval** — Technical review → Docs review → Product approval
- **Slack Integration** — Notify reviewers, quick approve buttons
- **Metrics Dashboard** — Approval times, rejection rates, quality scores
- **Enhanced RAG** — Use OpenSearch for context retrieval before generation
- **GitHub Integration** — Generate docs from PR descriptions and code changes

---

For complete implementation details, see [APPROVAL_WORKFLOW.md](../APPROVAL_WORKFLOW.md) in the project root.
