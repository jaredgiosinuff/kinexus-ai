# Kinexus AI: Documentation Structure & Storage

## 📍 Where Documentation Lives

In our MVP, all generated documentation is stored in **Amazon S3** with metadata in **DynamoDB**.

### S3 Bucket Structure
```
kinexus-documents/
│
├── repos/                      # GitHub-triggered documentation
│   ├── {org_repo}/
│   │   ├── README.md          # Main repository documentation
│   │   ├── CHANGELOG.md       # Auto-generated changelog
│   │   └── docs/
│   │       ├── API.md         # API documentation
│   │       ├── CONFIG.md      # Configuration guide
│   │       └── SETUP.md       # Setup instructions
│   │
│   └── {another_repo}/
│       └── ...
│
├── features/                   # Jira feature documentation
│   ├── PROJ-123.md            # Feature doc for ticket PROJ-123
│   ├── PROJ-456.md            # Feature doc for ticket PROJ-456
│   └── ...
│
├── releases/                   # Release documentation
│   ├── v1.0.0/
│   │   ├── RELEASE_NOTES.md  # Version release notes
│   │   └── MIGRATION.md      # Migration guide
│   └── v1.1.0/
│       └── ...
│
├── guides/                     # User guides by component
│   ├── payment-service/
│   │   ├── OVERVIEW.md
│   │   └── PROJ-789.md        # Component-specific feature
│   └── auth-service/
│       └── ...
│
└── api/                        # Consolidated API docs
    ├── v1/
    │   ├── reference.md       # Full API reference
    │   └── changelog.md       # API version changes
    └── v2/
        └── ...
```

## 🔄 Documentation Flow

### From GitHub (Technical Documentation)
```
GitHub Push Event
    ↓
Analyze Changed Files
    ↓
Determine Doc Type:
- Code changes → API.md
- Config changes → CONFIG.md
- Any changes → CHANGELOG.md
    ↓
Store in: s3://kinexus-documents/repos/{repo_name}/...
```

### From Jira (Feature Documentation)
```
Jira Ticket Closed
    ↓
Check if Documentation Needed:
- Story/Feature → Yes
- Has 'needs-docs' label → Yes
- Bug with 'breaking-change' → Yes
    ↓
Generate Based on Type:
- Feature → features/{TICKET}.md
- API Change → api/v{X}/reference.md
- Breaking Change → releases/v{X}/MIGRATION.md
    ↓
Store in: s3://kinexus-documents/{category}/...
```

## 📊 Documentation Metadata (DynamoDB)

Each document has metadata stored in DynamoDB for quick retrieval:

```json
{
  "document_id": "github_org_repo_api_1234567890",
  "title": "Payment API Documentation",
  "s3_key": "repos/org_repo/docs/API.md",
  "source": "github",
  "repository": "org/repo",
  "doc_type": "api_documentation",
  "created_at": "2025-09-26T10:00:00Z",
  "last_updated": "2025-09-26T10:00:00Z",
  "status": "generated",
  "quality_score": 85,
  "content_preview": "First 500 characters..."
}
```

## 🎯 Best Practices

### When to Use GitHub vs Jira

**GitHub-Triggered Documentation:**
- ✅ Technical implementation details
- ✅ API endpoint changes
- ✅ Configuration updates
- ✅ Code examples
- ✅ Developer-facing content

**Jira-Triggered Documentation:**
- ✅ Feature descriptions
- ✅ User guides
- ✅ Release notes
- ✅ Migration guides
- ✅ Business-facing content

### Jira Ticket Best Practices

**GOOD Jira Usage (Will Generate Docs):**
```
✅ Status: In Progress → Done (real work completed)
✅ Type: Story/Feature with clear acceptance criteria
✅ Labels: 'needs-docs', 'api-change', 'new-feature'
✅ Recent ticket (< 30 days old)
✅ Resolution: Fixed/Done
```

**BAD Jira Usage (Will Skip Docs):**
```
❌ Status: Open → Closed (no work done, just cleanup)
❌ Type: Sub-task or internal tech debt
❌ Labels: 'no-docs', 'internal-only'
❌ Old ticket (> 90 days) being closed in bulk
❌ Resolution: Won't Fix, Duplicate, Invalid
```

## 🔗 Cross-Referencing

The system automatically cross-references:

1. **Jira → GitHub**: Looks for commits mentioning ticket numbers
2. **GitHub → Jira**: Extracts ticket references from commit messages
3. **Combined Docs**: Merges technical and feature documentation

Example:
- Jira ticket PROJ-123 closed for "New Payment API"
- Finds related GitHub commits mentioning "PROJ-123"
- Generates both:
  - Feature doc: `features/PROJ-123.md` (user-facing)
  - API doc: `repos/payment-service/docs/API.md` (technical)
  - Links them together in metadata

## 🚀 Future Enhancements

1. **Confluence Publishing**: Direct sync to Confluence spaces
2. **GitBook Integration**: Publish to documentation portals
3. **Version Control**: Track documentation versions with Git
4. **Multi-Language**: Generate docs in multiple languages
5. **Search Index**: ElasticSearch for documentation discovery

## 📝 Accessing Documentation

### Via API
```python
# Get document by ID
GET /api/v1/documents/{document_id}

# List recent documents
GET /api/v1/documents?source=github&limit=10

# Search documents
GET /api/v1/documents/search?q=payment+api
```

### Direct S3 Access
```python
import boto3

s3 = boto3.client('s3')
response = s3.get_object(
    Bucket='kinexus-documents',
    Key='repos/org_repo/docs/API.md'
)
content = response['Body'].read().decode('utf-8')
```

### Via Dashboard (Coming Soon)
- Web UI with search and filtering
- Preview and editing capabilities
- Export to various formats