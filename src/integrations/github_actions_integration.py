#!/usr/bin/env python3
"""
GitHub Actions Integration - 2024-2025 Agentic AI Pattern
Implements PR-based documentation workflows with tiered update strategies
"""
import asyncio
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import boto3
import yaml

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BranchType(Enum):
    FEATURE = "feature"
    DEVELOPMENT = "development"
    STAGING = "staging"
    MAIN = "main"
    HOTFIX = "hotfix"


class UpdateScope(Enum):
    REPO_ONLY = "repo_only"
    INTERNAL_WIKI = "internal_wiki"
    FULL_ENTERPRISE = "full_enterprise"
    CUSTOM = "custom"


class DocumentationType(Enum):
    API_DOCS = "api_docs"
    ARCHITECTURE = "architecture"
    USER_GUIDE = "user_guide"
    DEVELOPER_DOCS = "developer_docs"
    RELEASE_NOTES = "release_notes"
    TROUBLESHOOTING = "troubleshooting"


@dataclass
class DocumentationMapping:
    doc_type: DocumentationType
    source_patterns: List[str]  # File patterns that trigger updates
    target_locations: Dict[str, str]  # platform -> location mapping
    update_conditions: Dict[str, Any] = field(default_factory=dict)
    priority: int = 1


@dataclass
class BranchConfiguration:
    branch_pattern: str
    branch_type: BranchType
    update_scope: UpdateScope
    target_platforms: List[str]
    documentation_mappings: List[DocumentationMapping]
    auto_merge_docs: bool = False
    require_approval: bool = False


@dataclass
class PRContext:
    pr_number: int
    source_branch: str
    target_branch: str
    changed_files: List[str]
    commit_messages: List[str]
    pr_title: str
    pr_description: str
    author: str
    repository: str
    head_sha: str


class GitHubActionsOrchestrator:
    """
    Orchestrates documentation updates based on GitHub Actions workflows
    Implements tiered update strategies based on branch and change context
    """

    def __init__(self, region: str = "us-east-1"):
        self.bedrock = boto3.client("bedrock-runtime", region_name=region)
        self.dynamodb = boto3.resource("dynamodb", region_name=region)
        self.github_client = None  # Will be initialized with repo context

        # Default configuration (can be overridden by repo-specific config)
        self.default_config = self._load_default_configuration()

    def _load_default_configuration(self) -> List[BranchConfiguration]:
        """Load default branch configurations for common workflows"""

        return [
            # Feature branches - repo only
            BranchConfiguration(
                branch_pattern="feature/*",
                branch_type=BranchType.FEATURE,
                update_scope=UpdateScope.REPO_ONLY,
                target_platforms=["github"],
                documentation_mappings=[
                    DocumentationMapping(
                        doc_type=DocumentationType.DEVELOPER_DOCS,
                        source_patterns=["src/**/*.py", "lib/**/*.js", "*.md"],
                        target_locations={"github": "docs/"},
                        priority=1,
                    )
                ],
                auto_merge_docs=True,
                require_approval=False,
            ),
            # Development branch - internal systems
            BranchConfiguration(
                branch_pattern="develop",
                branch_type=BranchType.DEVELOPMENT,
                update_scope=UpdateScope.INTERNAL_WIKI,
                target_platforms=["github", "confluence"],
                documentation_mappings=[
                    DocumentationMapping(
                        doc_type=DocumentationType.API_DOCS,
                        source_patterns=[
                            "api/**/*.py",
                            "routes/**/*.js",
                            "openapi.yaml",
                        ],
                        target_locations={
                            "github": "docs/api/",
                            "confluence": "SPACE:DEV/API Documentation",
                        },
                        priority=1,
                    ),
                    DocumentationMapping(
                        doc_type=DocumentationType.ARCHITECTURE,
                        source_patterns=["architecture/**/*", "docs/architecture/**/*"],
                        target_locations={
                            "github": "docs/architecture/",
                            "confluence": "SPACE:DEV/Architecture",
                        },
                        priority=2,
                    ),
                ],
                auto_merge_docs=False,
                require_approval=True,
            ),
            # Main branch - full enterprise sync
            BranchConfiguration(
                branch_pattern="main|master",
                branch_type=BranchType.MAIN,
                update_scope=UpdateScope.FULL_ENTERPRISE,
                target_platforms=["github", "confluence", "sharepoint"],
                documentation_mappings=[
                    DocumentationMapping(
                        doc_type=DocumentationType.API_DOCS,
                        source_patterns=["api/**/*", "openapi.yaml", "swagger.json"],
                        target_locations={
                            "github": "docs/api/",
                            "confluence": "SPACE:PROD/API Documentation",
                            "sharepoint": "sites/engineering/API Docs",
                        },
                        priority=1,
                    ),
                    DocumentationMapping(
                        doc_type=DocumentationType.USER_GUIDE,
                        source_patterns=["docs/user/**/*", "README.md"],
                        target_locations={
                            "github": "docs/user/",
                            "confluence": "SPACE:PROD/User Guides",
                            "sharepoint": "sites/support/User Documentation",
                        },
                        priority=1,
                    ),
                    DocumentationMapping(
                        doc_type=DocumentationType.RELEASE_NOTES,
                        source_patterns=[
                            "CHANGELOG.md",
                            "RELEASE.md",
                            "docs/releases/**/*",
                        ],
                        target_locations={
                            "github": "docs/releases/",
                            "confluence": "SPACE:PROD/Release Notes",
                            "sharepoint": "sites/support/Release Information",
                        },
                        priority=1,
                    ),
                ],
                auto_merge_docs=False,
                require_approval=True,
            ),
        ]

    async def process_pull_request(
        self,
        pr_context: PRContext,
        custom_config: Optional[Dict[str, Any]] = None,
        execute_updates: bool = True,
    ) -> Dict[str, Any]:
        """Process PR and determine documentation updates needed"""

        logger.info(
            f"Processing PR #{pr_context.pr_number}: {pr_context.source_branch} → {pr_context.target_branch}"
        )

        try:
            # Load repository-specific configuration if provided
            config = await self._load_repository_config(
                pr_context.repository, custom_config
            )

            # Determine branch configuration
            branch_config = self._match_branch_configuration(
                pr_context.target_branch, config
            )

            if not branch_config:
                return {
                    "documentation_updates_needed": False,
                    "reason": f"No configuration found for target branch: {pr_context.target_branch}",
                    "supported_branches": [c.branch_pattern for c in config],
                }

            # Analyze changed files to determine documentation impact
            doc_analysis = await self._analyze_documentation_impact(
                pr_context, branch_config
            )

            if not doc_analysis["updates_needed"]:
                return {
                    "documentation_updates_needed": False,
                    "reason": "No documentation-triggering changes detected",
                    "analyzed_files": len(pr_context.changed_files),
                    "branch_config": branch_config.branch_pattern,
                }

            # Generate documentation updates
            update_plan = await self._generate_update_plan(
                pr_context, branch_config, doc_analysis
            )

            execution_results = None
            if execute_updates:
                execution_results = await self._execute_documentation_updates(
                    update_plan, pr_context
                )

            return {
                "documentation_updates_needed": True,
                "branch_config": {
                    "pattern": branch_config.branch_pattern,
                    "type": branch_config.branch_type.value,
                    "scope": branch_config.update_scope.value,
                    "platforms": branch_config.target_platforms,
                },
                "documentation_analysis": doc_analysis,
                "update_plan": update_plan,
                "execution_results": execution_results if execute_updates else None,
                "execution_mode": "execute" if execute_updates else "plan_only",
                "github_actions_integration": True,
            }

        except Exception as e:
            logger.error(f"PR processing failed: {str(e)}")
            return {
                "documentation_updates_needed": False,
                "error": str(e),
                "pr_context": pr_context.pr_number,
            }

    async def _load_repository_config(
        self, repository: str, custom_config: Optional[Dict[str, Any]]
    ) -> List[BranchConfiguration]:
        """Load repository-specific configuration"""

        if custom_config:
            try:
                # Parse custom configuration
                return self._parse_custom_config(custom_config)
            except Exception as e:
                logger.warning(f"Failed to parse custom config: {e}, using defaults")

        # Try to load from repository .kinexus/config.yaml
        try:
            # This would fetch from the repository
            # For now, return default configuration
            return self.default_config
        except Exception:
            return self.default_config

    def _match_branch_configuration(
        self, target_branch: str, configs: List[BranchConfiguration]
    ) -> Optional[BranchConfiguration]:
        """Match target branch to configuration"""

        import re

        for config in configs:
            pattern = config.branch_pattern.replace("*", ".*")
            if re.match(pattern, target_branch):
                return config

        return None

    async def _analyze_documentation_impact(
        self, pr_context: PRContext, branch_config: BranchConfiguration
    ) -> Dict[str, Any]:
        """Analyze changed files to determine documentation impact"""

        import fnmatch

        impacted_mappings = []

        for mapping in branch_config.documentation_mappings:
            matching_files = []

            for file_path in pr_context.changed_files:
                for pattern in mapping.source_patterns:
                    if fnmatch.fnmatch(file_path, pattern):
                        matching_files.append(file_path)
                        break

            if matching_files:
                impacted_mappings.append(
                    {
                        "doc_type": mapping.doc_type.value,
                        "matching_files": matching_files,
                        "target_locations": mapping.target_locations,
                        "priority": mapping.priority,
                    }
                )

        # Use AI to analyze the semantic impact
        semantic_analysis = await self._analyze_semantic_impact(
            pr_context, impacted_mappings
        )

        return {
            "updates_needed": len(impacted_mappings) > 0,
            "impacted_mappings": impacted_mappings,
            "semantic_analysis": semantic_analysis,
            "total_changed_files": len(pr_context.changed_files),
            "documentation_files_affected": sum(
                len(m["matching_files"]) for m in impacted_mappings
            ),
        }

    async def _analyze_semantic_impact(
        self, pr_context: PRContext, impacted_mappings: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Use AI to analyze the semantic impact of changes"""

        prompt = f"""
        Analyze the semantic impact of this pull request on documentation:

        PR Title: {pr_context.pr_title}
        PR Description: {pr_context.pr_description}
        Target Branch: {pr_context.target_branch}
        Changed Files: {pr_context.changed_files[:10]}  # Limit for prompt size
        Commit Messages: {pr_context.commit_messages[:5]}

        Impacted Documentation Types: {[m["doc_type"] for m in impacted_mappings]}

        Determine:
        1. What type of documentation changes are needed?
        2. What is the priority level (1-5)?
        3. Are there breaking changes that require immediate documentation updates?
        4. What specific sections of documentation should be updated?
        5. Should this trigger automated documentation generation?

        Respond in JSON format.
        """

        try:
            response = await self._call_bedrock_model(prompt)
            return json.loads(response)
        except Exception as e:
            logger.warning(f"Semantic analysis failed: {e}")
            return {
                "analysis_available": False,
                "fallback_priority": 3,
                "suggested_updates": [
                    "Review and update relevant documentation sections"
                ],
            }

    async def _generate_update_plan(
        self,
        pr_context: PRContext,
        branch_config: BranchConfiguration,
        doc_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate detailed update plan based on analysis"""

        update_tasks = []

        for mapping_data in doc_analysis["impacted_mappings"]:
            for platform, location in mapping_data["target_locations"].items():
                if platform in branch_config.target_platforms:
                    update_tasks.append(
                        {
                            "platform": platform,
                            "location": location,
                            "doc_type": mapping_data["doc_type"],
                            "source_files": mapping_data["matching_files"],
                            "priority": mapping_data["priority"],
                            "update_method": self._determine_update_method(
                                platform, branch_config
                            ),
                        }
                    )

        # Sort by priority
        update_tasks.sort(key=lambda x: x["priority"])

        return {
            "total_tasks": len(update_tasks),
            "update_tasks": update_tasks,
            "execution_strategy": self._determine_execution_strategy(branch_config),
            "approval_required": branch_config.require_approval,
            "auto_merge": branch_config.auto_merge_docs,
        }

    def _determine_update_method(
        self, platform: str, branch_config: BranchConfiguration
    ) -> str:
        """Determine the best update method for the platform"""

        if platform == "github":
            return "github_api"
        elif platform == "confluence":
            return (
                "confluence_api"
                if branch_config.branch_type != BranchType.FEATURE
                else "browser_automation"
            )
        elif platform == "sharepoint":
            return "browser_automation"  # SharePoint often requires browser automation
        else:
            return "api_with_browser_fallback"

    def _determine_execution_strategy(self, branch_config: BranchConfiguration) -> str:
        """Determine execution strategy based on branch configuration"""

        if branch_config.update_scope == UpdateScope.REPO_ONLY:
            return "immediate_execution"
        elif branch_config.update_scope == UpdateScope.INTERNAL_WIKI:
            return "parallel_with_approval"
        else:
            return "staged_execution_with_validation"

    async def _execute_documentation_updates(
        self, update_plan: Dict[str, Any], pr_context: PRContext
    ) -> Dict[str, Any]:
        """Execute the documentation updates according to the plan"""

        execution_results = {
            "total_tasks": update_plan["total_tasks"],
            "completed_tasks": 0,
            "failed_tasks": 0,
            "task_results": [],
            "execution_strategy": update_plan["execution_strategy"],
        }

        try:
            # Import multi-agent supervisor for complex updates
            from multi_agent_supervisor import MultiAgentSupervisor

            supervisor = MultiAgentSupervisor()

            for task in update_plan["update_tasks"]:
                try:
                    # Convert PR context to change data
                    change_data = self._convert_pr_to_change_data(pr_context, task)

                    # Process with multi-agent supervisor
                    result = await supervisor.process_change_event(change_data)

                    task_result = {
                        "task": task,
                        "status": (
                            "completed"
                            if result.get("multi_agent_processing", {}).get(
                                "overall_success", False
                            )
                            else "failed"
                        ),
                        "execution_time": result.get("multi_agent_processing", {}).get(
                            "total_execution_time", 0
                        ),
                        "details": result,
                    }

                    execution_results["task_results"].append(task_result)

                    if task_result["status"] == "completed":
                        execution_results["completed_tasks"] += 1
                    else:
                        execution_results["failed_tasks"] += 1

                except Exception as e:
                    logger.error(f"Task execution failed: {str(e)}")
                    execution_results["task_results"].append(
                        {"task": task, "status": "failed", "error": str(e)}
                    )
                    execution_results["failed_tasks"] += 1

            # Generate summary
            execution_results["success_rate"] = (
                execution_results["completed_tasks"] / execution_results["total_tasks"]
                if execution_results["total_tasks"] > 0
                else 0
            )

            return execution_results

        except Exception as e:
            logger.error(f"Update execution failed: {str(e)}")
            return {
                "execution_failed": True,
                "error": str(e),
                "completed_tasks": 0,
                "total_tasks": update_plan["total_tasks"],
            }

    def _convert_pr_to_change_data(
        self, pr_context: PRContext, task: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert PR context to change data format for multi-agent supervisor"""

        return {
            "repository": {"full_name": pr_context.repository},
            "pull_request": {
                "number": pr_context.pr_number,
                "title": pr_context.pr_title,
                "body": pr_context.pr_description,
                "head": {"sha": pr_context.head_sha},
                "base": {"ref": pr_context.target_branch},
                "user": {"login": pr_context.author},
            },
            "commits": [{"message": msg} for msg in pr_context.commit_messages],
            "changed_files": pr_context.changed_files,
            "documentation_context": {
                "doc_type": task["doc_type"],
                "target_platform": task["platform"],
                "target_location": task["location"],
                "source_files": task["source_files"],
                "update_method": task["update_method"],
            },
            "github_actions_trigger": True,
        }

    async def _call_bedrock_model(self, prompt: str) -> str:
        """Call Bedrock model for analysis"""

        try:
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4000,
                "temperature": 0.1,
                "messages": [{"role": "user", "content": prompt}],
            }

            response = self.bedrock.invoke_model(
                modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
                body=json.dumps(request_body),
                contentType="application/json",
            )

            response_body = json.loads(response["body"].read())
            return response_body["content"][0]["text"]

        except Exception as e:
            logger.error(f"Bedrock call failed: {str(e)}")
            return '{"analysis_available": false, "error": "AI analysis unavailable"}'

    def _parse_custom_config(self, config: Dict[str, Any]) -> List[BranchConfiguration]:
        """Parse custom repository configuration"""

        configurations = []

        for branch_config in config.get("branches", []):
            mappings = []

            for mapping_config in branch_config.get("documentation_mappings", []):
                mappings.append(
                    DocumentationMapping(
                        doc_type=DocumentationType(mapping_config["doc_type"]),
                        source_patterns=mapping_config["source_patterns"],
                        target_locations=mapping_config["target_locations"],
                        priority=mapping_config.get("priority", 1),
                    )
                )

            configurations.append(
                BranchConfiguration(
                    branch_pattern=branch_config["branch_pattern"],
                    branch_type=BranchType(branch_config["branch_type"]),
                    update_scope=UpdateScope(branch_config["update_scope"]),
                    target_platforms=branch_config["target_platforms"],
                    documentation_mappings=mappings,
                    auto_merge_docs=branch_config.get("auto_merge_docs", False),
                    require_approval=branch_config.get("require_approval", False),
                )
            )

        return configurations


# GitHub Actions workflow generator
def generate_github_action_workflow() -> str:
    """Generate GitHub Actions workflow YAML for Kinexus AI integration"""

    workflow = {
        "name": "Kinexus AI Documentation Updates",
        "on": {
            "pull_request": {
                "types": ["opened", "synchronize", "reopened"],
                "branches": ["main", "master", "develop", "feature/*"],
            },
            "push": {"branches": ["main", "master"]},
        },
        "jobs": {
            "kinexus-documentation": {
                "runs-on": "ubuntu-latest",
                "steps": [
                    {
                        "name": "Checkout code",
                        "uses": "actions/checkout@v4",
                        "with": {"fetch-depth": 0},
                    },
                    {
                        "name": "Get changed files",
                        "id": "changed-files",
                        "uses": "tj-actions/changed-files@v40",
                        "with": {"files": "**/*"},
                    },
                    {
                        "name": "Trigger Kinexus AI Documentation Update",
                        "env": {
                            "KINEXUS_WEBHOOK_URL": "${{ secrets.KINEXUS_WEBHOOK_URL }}",
                            "KINEXUS_API_KEY": "${{ secrets.KINEXUS_API_KEY }}",
                        },
                        "run": """
curl -X POST "$KINEXUS_WEBHOOK_URL" \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer $KINEXUS_API_KEY" \\
  -d '{
    "action": "pull_request",
    "pull_request": {
      "number": ${{ github.event.pull_request.number || 0 }},
      "title": "${{ github.event.pull_request.title || github.event.head_commit.message }}",
      "body": "${{ github.event.pull_request.body || github.event.head_commit.message }}",
      "head": {"sha": "${{ github.sha }}"},
      "base": {"ref": "${{ github.base_ref || github.ref_name }}"},
      "user": {"login": "${{ github.actor }}"}
    },
    "repository": {"full_name": "${{ github.repository }}"},
    "changed_files": ${{ toJson(steps.changed-files.outputs.all_changed_files) }},
    "commit_messages": ["${{ github.event.head_commit.message || github.event.pull_request.title }}"],
    "github_actions_trigger": true
  }'
                        """,
                    },
                ],
            }
        },
    }

    return yaml.dump(workflow, default_flow_style=False)


# Integration function for the webhook handler
async def process_github_actions_webhook(
    webhook_data: Dict[str, Any],
    *,
    execute_updates: bool = True,
    custom_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Process GitHub Actions webhook for PR-based documentation updates
    """
    try:
        orchestrator = GitHubActionsOrchestrator()

        # Extract PR context from webhook
        pr_context = PRContext(
            pr_number=webhook_data.get("pull_request", {}).get("number", 0),
            source_branch=webhook_data.get("pull_request", {})
            .get("head", {})
            .get("ref", ""),
            target_branch=webhook_data.get("pull_request", {})
            .get("base", {})
            .get("ref", ""),
            changed_files=webhook_data.get("changed_files", []),
            commit_messages=webhook_data.get("commit_messages", []),
            pr_title=webhook_data.get("pull_request", {}).get("title", ""),
            pr_description=webhook_data.get("pull_request", {}).get("body", ""),
            author=webhook_data.get("pull_request", {})
            .get("user", {})
            .get("login", ""),
            repository=webhook_data.get("repository", {}).get("full_name", ""),
            head_sha=webhook_data.get("pull_request", {})
            .get("head", {})
            .get("sha", ""),
        )

        # Process the PR
        result = await orchestrator.process_pull_request(
            pr_context, custom_config=custom_config, execute_updates=execute_updates
        )

        return {
            "github_actions_integration_completed": True,
            "processing_method": "pr_based_documentation_workflow",
            "workflow_version": "2024-2025-tiered-updates",
            **result,
        }

    except Exception as e:
        logger.error(f"GitHub Actions webhook processing failed: {str(e)}")
        return {
            "github_actions_integration_completed": False,
            "error": str(e),
            "fallback_recommendation": "Process as standard webhook",
        }


if __name__ == "__main__":
    # Generate sample workflow file
    workflow_yaml = generate_github_action_workflow()
    print("Generated GitHub Actions Workflow:")
    print("=" * 50)
    print(workflow_yaml)

    # Test the integration
    import asyncio

    async def test_github_actions():
        test_webhook = {
            "action": "pull_request",
            "pull_request": {
                "number": 123,
                "title": "Add new API endpoints for user management",
                "body": "This PR adds new REST API endpoints for user CRUD operations",
                "head": {"ref": "feature/user-api", "sha": "abc123"},
                "base": {"ref": "develop"},
                "user": {"login": "developer"},
            },
            "repository": {"full_name": "company/api-service"},
            "changed_files": ["src/api/users.py", "docs/api.md", "tests/test_users.py"],
            "commit_messages": ["Add user API endpoints", "Update API documentation"],
            "github_actions_trigger": True,
        }

        result = await process_github_actions_webhook(
            test_webhook, execute_updates=False
        )
        print("\nTest Result:")
        print("=" * 50)
        print(json.dumps(result, indent=2))

    asyncio.run(test_github_actions())
