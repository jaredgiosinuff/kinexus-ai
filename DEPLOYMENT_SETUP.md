# GitHub Actions Deployment Setup Checklist

Quick setup guide for getting the GitHub Actions deployment workflow running.

## ✅ Prerequisites Completed

- [x] GitHub Actions workflow created (`.github/workflows/dev.yaml`)
- [x] AWS deployment scripts ready
- [x] Documentation complete
- [x] Workflow YAML syntax validated

## 🔧 Required GitHub Secrets

You need to configure these secrets in GitHub before the workflow can deploy:

### Go to: https://github.com/jaredgiosinuff/kinexus-ai/settings/secrets/actions

### **Option 1: Using Your Existing AWS Credentials (Quickest)**

Based on your existing AWS credentials from CLAUDE.md:

```bash
# Using GitHub web UI:
# Settings → Secrets and variables → Actions → New repository secret

AWS_ACCOUNT_ID = 117572456299
AWS_ACCESS_KEY_ID = AKIA****************  # Your AWS access key
AWS_SECRET_ACCESS_KEY = ********************************  # Your AWS secret key
```

**Note**: You'll need to update the workflow to use access keys instead of OIDC role.

### **Option 2: Using OIDC (Recommended for Production)**

Create a deployment role with OIDC:

1. **Create OIDC Provider** (one-time setup):
```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

2. **Create Trust Policy** (`github-trust-policy.json`):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::117572456299:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:jaredgiosinuff/kinexus-ai:*"
        }
      }
    }
  ]
}
```

3. **Create IAM Role**:
```bash
aws iam create-role \
  --role-name GitHubActionsDeploymentRole \
  --assume-role-policy-document file://github-trust-policy.json

# Attach the deployment policy you created
aws iam attach-role-policy \
  --role-name GitHubActionsDeploymentRole \
  --policy-arn arn:aws:iam::117572456299:policy/KinexusAI-DevPolicy
```

4. **Add GitHub Secrets**:
```bash
AWS_ROLE_ARN = arn:aws:iam::117572456299:role/GitHubActionsDeploymentRole
AWS_ACCOUNT_ID = 117572456299
```

## 🏗️ Infrastructure Setup

### For Production Deployments (ECS)

Create ECR repositories for Docker images:

```bash
./scripts/create-ecr-repos.sh
```

This creates:
- `kinexus-ai-api`
- `kinexus-ai-orchestrator`
- `kinexus-ai-change-analyzer`
- `kinexus-ai-content-creator`
- `kinexus-ai-quality-controller`
- `kinexus-ai-web-automator`

### For MVP Deployments (Lambda)

No additional setup needed - Lambda layer will be built automatically.

## 🌍 GitHub Environments (Optional but Recommended)

### Go to: https://github.com/jaredgiosinuff/kinexus-ai/settings/environments

Create three environments with protection rules:

### 1. **development**
- No protection rules (auto-deploy)
- Used for: `develop` branch

### 2. **staging**
- Required reviewers: 1
- Wait timer: 0 minutes
- Used for: `release/*` branches

### 3. **production**
- Required reviewers: 2
- Wait timer: 5 minutes
- Deployment branches: `main` only
- Used for: `main` branch

## 🚀 Testing the Workflow

### Step 1: Verify Workflow Shows Up

1. Go to: https://github.com/jaredgiosinuff/kinexus-ai/actions
2. You should see "Deploy to AWS" workflow listed

### Step 2: Create `develop` Branch

```bash
# Create develop branch from main
git checkout -b develop
git push origin develop
```

### Step 3: Trigger Test Deployment

#### **Option A: Push to develop (MVP deployment)**
```bash
git checkout develop
git commit --allow-empty -m "test: trigger GitHub Actions deployment"
git push origin develop
```

#### **Option B: Create a Pull Request**
```bash
git checkout -b test-workflow
echo "# Test" >> TEST.md
git add TEST.md
git commit -m "test: validate workflow"
git push origin test-workflow
# Then create PR via GitHub UI
```

#### **Option C: Manual Trigger**
1. Go to: https://github.com/jaredgiosinuff/kinexus-ai/actions/workflows/dev.yaml
2. Click "Run workflow"
3. Select:
   - Branch: `main`
   - Environment: `development`
   - Deployment type: `mvp`
   - Skip tests: `false`
4. Click "Run workflow"

## 📊 What Will Happen

### Without Secrets (Initial Test)
The workflow will:
- ✅ Start successfully
- ✅ Run the "configure" job
- ✅ Run the "test" job (if tests pass)
- ❌ Fail at "build" or "deploy" jobs (needs AWS credentials)

This is **expected** and confirms the workflow is set up correctly!

### With Secrets (Full Deployment)
The workflow will:
- ✅ Run all tests
- ✅ Build Docker images (production) or Lambda layer (MVP)
- ✅ Deploy to AWS via CDK
- ✅ Run health checks
- ✅ Comment on PR with deployment details

## 🔍 Monitoring Deployment

### During Deployment
1. Go to: https://github.com/jaredgiosinuff/kinexus-ai/actions
2. Click on the running workflow
3. Watch real-time logs for each job

### After Deployment
- **CloudFormation**: AWS Console → CloudFormation → Stacks
- **ECS Services**: AWS Console → ECS → Clusters
- **API Health**: Check the endpoint from CDK outputs
- **Logs**: CloudWatch Logs

## 🐛 Troubleshooting

### Workflow Doesn't Trigger
- Check branch names match triggers in workflow
- Verify workflow file is in `.github/workflows/` directory
- Check GitHub Actions is enabled in repository settings

### Build Fails
- **Missing ECR repos**: Run `./scripts/create-ecr-repos.sh`
- **Invalid AWS credentials**: Verify secrets are correct
- **Permission errors**: Check IAM policy has necessary permissions

### Deployment Fails
- **CDK bootstrap needed**: Workflow will run this automatically
- **Resource limits**: Check AWS service quotas
- **Stack already exists**: Use `--force` or destroy old stack

## 📝 Current Configuration

Based on your AWS account:
- **Account ID**: 117572456299
- **Region**: us-east-1
- **Domain**: kinexusai.com (Route 53 configured)
- **Existing IAM User**: kinexus-ai-dev

## ⏭️ Next Steps

1. **Add GitHub Secrets** (see above)
2. **Create develop branch** (if needed)
3. **Test workflow** with empty commit
4. **Verify it fails at AWS auth** (expected without secrets)
5. **Add secrets** and re-run
6. **Monitor deployment** in GitHub Actions
7. **Verify deployment** in AWS Console

## 🆘 Getting Help

- **Workflow syntax errors**: Check `.github/workflows/dev.yaml`
- **AWS permission errors**: Review IAM policies
- **Deployment errors**: Check CloudFormation events
- **General issues**: See [docs/github-actions-deployment.md](docs/github-actions-deployment.md)

---

**Ready to deploy!** Start by adding the GitHub secrets, then push to `develop` or create a PR.
