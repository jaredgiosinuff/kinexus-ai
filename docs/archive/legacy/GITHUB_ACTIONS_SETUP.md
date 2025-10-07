# GitHub Actions Integration Setup Guide

## 🚀 Quick Start: 5-Minute Setup

Transform your repository into an autonomous documentation powerhouse with Kinexus AI's GitHub Actions integration.

### Step 1: Add GitHub Actions Workflow

Copy this file to your repository at `.github/workflows/kinexus-documentation.yml`:

```yaml
name: Kinexus AI Documentation Updates

on:
  pull_request:
    types: [opened, synchronize, reopened]
    branches: [main, master, develop, staging]
  push:
    branches: [main, master]

jobs:
  kinexus-documentation:
    name: Update Documentation with Kinexus AI
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Get Changed Files
        id: changed-files
        uses: tj-actions/changed-files@v40
        with:
          files: |
            **/*.py
            **/*.js
            **/*.ts
            **/*.md
            docs/**/*
            api/**/*
            src/**/*

      - name: Trigger Kinexus AI Documentation Update
        env:
          KINEXUS_WEBHOOK_URL: ${{ secrets.KINEXUS_WEBHOOK_URL }}
          KINEXUS_API_KEY: ${{ secrets.KINEXUS_API_KEY }}
        run: |
          curl -X POST "$KINEXUS_WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $KINEXUS_API_KEY" \
            -d '{
              "action": "github_actions_trigger",
              "pull_request": {
                "number": ${{ github.event.pull_request.number || 0 }},
                "title": "${{ github.event.pull_request.title || github.event.head_commit.message }}",
                "head": {"ref": "${{ github.head_ref || github.ref_name }}", "sha": "${{ github.sha }}"},
                "base": {"ref": "${{ github.base_ref || 'main' }}"},
                "user": {"login": "${{ github.actor }}"}
              },
              "repository": {"full_name": "${{ github.repository }}"},
              "changed_files": ${{ toJson(steps.changed-files.outputs.all_changed_files) }},
              "github_actions_trigger": true
            }'
```

### Step 2: Configure Repository Secrets

Add these secrets to your repository settings:

1. **KINEXUS_WEBHOOK_URL**: `https://388tx4f8ri.execute-api.us-east-1.amazonaws.com/prod/webhooks/github`
2. **KINEXUS_API_KEY**: Contact your Kinexus AI administrator for your API key

### Step 3: Add Kinexus Configuration (Optional)

Create `.kinexus/config.yaml` in your repository root for custom behavior:

```yaml
version: "2024-2025"
project_name: "your-project"

branches:
  - branch_pattern: "feature/*"
    branch_type: "feature"
    update_scope: "repo_only"
    target_platforms: ["github"]
    auto_merge_docs: true

  - branch_pattern: "develop"
    branch_type: "development"
    update_scope: "internal_wiki"
    target_platforms: ["github", "confluence"]

  - branch_pattern: "main|master"
    branch_type: "main"
    update_scope: "full_enterprise"
    target_platforms: ["github", "confluence", "sharepoint"]
```

## 📋 Tiered Documentation Strategy

### 🌟 Feature Branches → Repo Only
- **Trigger**: PR to `feature/*` branches
- **Scope**: Repository documentation only
- **Speed**: ⚡ Immediate updates
- **Platforms**: GitHub repo docs
- **Auto-merge**: ✅ Yes

### 🔧 Development Branch → Internal Systems
- **Trigger**: PR to `develop` branch
- **Scope**: Internal wikis and documentation
- **Speed**: 🚀 Fast with approval
- **Platforms**: GitHub + Confluence
- **Auto-merge**: ❌ Requires approval

### 🚀 Main/Master → Full Enterprise
- **Trigger**: PR to `main`/`master` branch
- **Scope**: Complete enterprise documentation sync
- **Speed**: 🎯 Comprehensive with validation
- **Platforms**: GitHub + Confluence + SharePoint + Custom
- **Auto-merge**: ❌ Requires approval

## 🎯 Documentation Mapping Examples

### API Documentation
```yaml
- doc_type: "api_docs"
  source_patterns:
    - "src/api/**/*.py"
    - "routes/**/*.js"
    - "openapi.yaml"
  target_locations:
    github: "docs/api/"
    confluence: "SPACE:PROD/API Documentation"
    sharepoint: "sites/engineering/API Docs"
```

### Architecture Documentation
```yaml
- doc_type: "architecture"
  source_patterns:
    - "src/agents/**/*.py"
    - "architecture/**/*"
    - "docs/architecture/**/*"
  target_locations:
    github: "docs/architecture/"
    confluence: "SPACE:PROD/System Architecture"
```

### User Guides
```yaml
- doc_type: "user_guide"
  source_patterns:
    - "docs/user/**/*"
    - "README.md"
    - "USAGE.md"
  target_locations:
    github: "docs/user/"
    confluence: "SPACE:PROD/User Guides"
    sharepoint: "sites/support/User Documentation"
```

## 🔧 Advanced Configuration

### Custom Platforms
```yaml
platforms:
  custom_wiki:
    base_url: "https://wiki.company.com"
    update_method: "browser_automation"
    authentication: "sso"
```

### Smart Triggering
```yaml
settings:
  ai_enhancement: true
  semantic_analysis: true
  auto_generate_summaries: true
  parallel_updates: true
```

### Notifications
```yaml
notifications:
  slack:
    webhook_url: "${SLACK_WEBHOOK_URL}"
    channels: ["#documentation", "#engineering"]

  email:
    recipients: ["docs-team@company.com"]
```

## 📊 Workflow Examples

### 1. Feature Development
```
Developer creates feature/user-auth branch
├── Makes changes to src/auth/
├── Creates PR to develop
├── 🤖 Kinexus AI automatically:
│   ├── Analyzes changed files
│   ├── Updates repo documentation
│   ├── Generates API docs
│   └── Creates documentation PR
└── ✅ Documentation updated in parallel
```

### 2. Production Release
```
Team merges develop → main
├── 🤖 Kinexus AI automatically:
│   ├── Updates GitHub docs
│   ├── Syncs Confluence spaces
│   ├── Updates SharePoint sites
│   ├── Generates release notes
│   └── Notifies stakeholders
└── ✅ Enterprise documentation synchronized
```

### 3. API Changes
```
API endpoint modifications detected
├── 🤖 Kinexus AI automatically:
│   ├── Analyzes OpenAPI spec changes
│   ├── Updates API documentation
│   ├── Generates code examples
│   ├── Updates integration guides
│   └── Creates migration notes
└── ✅ API docs always current
```

## 🏆 Benefits for Different Team Sizes

### Small Teams (2-10 developers)
- **Zero overhead**: Documentation happens automatically
- **No dedicated docs person needed**
- **Repo-centric approach**: Everything in GitHub

### Medium Teams (10-50 developers)
- **Scaled documentation**: Multiple platforms managed
- **Approval workflows**: Quality gates for production docs
- **Team notifications**: Slack/email integration

### Large Teams (50+ developers)
- **Enterprise integration**: SharePoint, Confluence, custom wikis
- **Compliance ready**: Audit trails and approval workflows
- **Multi-tenant**: Different rules per team/project

## 🚀 Implementation Timeline

### Week 1: Basic Setup
- [ ] Add GitHub Actions workflow
- [ ] Configure repository secrets
- [ ] Test with feature branch PRs

### Week 2: Platform Integration
- [ ] Connect to Confluence
- [ ] Configure SharePoint integration
- [ ] Set up notification channels

### Week 3: Advanced Features
- [ ] Customize documentation mappings
- [ ] Enable browser automation fallbacks
- [ ] Configure approval workflows

### Week 4: Team Rollout
- [ ] Train development teams
- [ ] Monitor and optimize
- [ ] Gather feedback and iterate

## 🔒 Security & Compliance

### Access Control
- API keys scoped to specific repositories
- Platform-specific authentication (SSO, tokens)
- Audit logs for all documentation updates

### Data Privacy
- No source code sent to external services
- Only file paths and metadata analyzed
- Enterprise data stays within your infrastructure

### Compliance Features
- Approval workflows for sensitive documentation
- Change tracking and audit trails
- Integration with existing governance tools

## 📞 Support & Resources

### Quick Links
- **Webhook URL**: `https://388tx4f8ri.execute-api.us-east-1.amazonaws.com/prod/webhooks/github`
- **API Documentation**: Available in your Kinexus AI dashboard
- **Status Page**: Monitor system health and updates

### Common Issues
1. **Webhook not triggering**: Check repository secrets configuration
2. **Documentation not updating**: Verify file patterns in configuration
3. **Platform sync failing**: Check platform credentials and permissions

### Getting Help
- **Slack**: #kinexus-ai-support
- **Email**: support@kinexusai.com
- **Documentation**: https://docs.kinexusai.com

---

**Ready to transform your documentation workflow?**

Add the GitHub Actions workflow to your repository and watch as your documentation automatically stays in sync with your code changes. No more outdated docs, no more manual updates – just intelligent, automated documentation that grows with your project.

🎯 **Next Steps**: Copy the workflow file above and commit it to your repository to get started immediately!