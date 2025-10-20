"""
Jira Integration for Issue Tracking and Documentation Synchronization
Manages documentation that lives in Jira issues, comments, and knowledge base
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp
import structlog

from .base_integration import BaseIntegration, SyncResult, TestResult

logger = structlog.get_logger()


class JiraClient:
    """
    Client for managing Jira issues and documentation synchronization.
    This client UPDATES existing issues and creates documentation links.

    IMPORTANT (2025):
    - Uses Jira REST API v3 (current as of October 2025)
    - API tokens now expire (1-365 days) - implement token refresh logic
    - Scoped API tokens recommended for enhanced security
    - For production: use OAuth 2.0 or JWT instead of basic auth
    """

    def __init__(self, server_url: str, username: str, api_token: str):
        self.server_url = server_url.rstrip("/")
        self.auth = (username, api_token)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def get_issue(self, issue_key: str) -> Optional[Dict]:
        """Get issue details by key (e.g., 'PROJ-123'). Uses Jira REST API v3 (2025)."""
        url = f"{self.server_url}/rest/api/3/issue/{issue_key}"
        params = {"expand": "renderedFields,comment,attachment,changelog"}

        async with aiohttp.ClientSession() as session:
            try:
                response = await session.get(
                    url,
                    auth=aiohttp.BasicAuth(self.auth[0], self.auth[1]),
                    headers=self.headers,
                    params=params,
                )
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    logger.debug(f"Issue not found: {issue_key}")
                    return None
                else:
                    logger.error(f"Error getting issue: {response.status}")
                    return None
            except Exception as e:
                logger.error(f"Error fetching issue: {e}")
                return None

    async def search_issues(self, jql: str, max_results: int = 100) -> List[Dict]:
        """Search for issues using JQL (Jira Query Language). Uses Jira REST API v3 (2025)."""
        url = f"{self.server_url}/rest/api/3/search"
        payload = {
            "jql": jql,
            "maxResults": max_results,
            "expand": ["renderedFields"],
            "fields": [
                "key",
                "summary",
                "description",
                "issuetype",
                "status",
                "assignee",
                "created",
                "updated",
            ],
        }

        async with aiohttp.ClientSession() as session:
            try:
                response = await session.post(
                    url,
                    auth=aiohttp.BasicAuth(self.auth[0], self.auth[1]),
                    headers=self.headers,
                    json=payload,
                )
                if response.status == 200:
                    data = await response.json()
                    return data.get("issues", [])
                else:
                    logger.error(f"Search failed: {response.status}")
                    return []
            except Exception as e:
                logger.error(f"Error searching issues: {e}")
                return []

    async def add_comment(self, issue_key: str, comment_body: str) -> Dict:
        """Add a comment to an issue. Uses Jira REST API v3 (2025)."""
        url = f"{self.server_url}/rest/api/3/issue/{issue_key}/comment"
        payload = {"body": comment_body}

        async with aiohttp.ClientSession() as session:
            response = await session.post(
                url,
                auth=aiohttp.BasicAuth(self.auth[0], self.auth[1]),
                headers=self.headers,
                json=payload,
            )

            if response.status in [200, 201]:
                logger.info(f"Added comment to issue {issue_key}")
                return await response.json()
            else:
                logger.error(f"Failed to add comment: {response.status}")
                raise Exception(f"Failed to add comment: {response.status}")

    async def update_issue_description(
        self, issue_key: str, new_description: str, update_reason: str
    ) -> Dict:
        """Update an issue's description with documentation updates. Uses Jira REST API v3 (2025)."""
        url = f"{self.server_url}/rest/api/3/issue/{issue_key}"

        # Add update note to description
        timestamp = datetime.utcnow().isoformat()
        description_with_note = f"""{new_description}

----
_Last updated by Kinexus AI on {timestamp}: {update_reason}_
"""

        payload = {"fields": {"description": description_with_note}}

        async with aiohttp.ClientSession() as session:
            response = await session.put(
                url,
                auth=aiohttp.BasicAuth(self.auth[0], self.auth[1]),
                headers=self.headers,
                json=payload,
            )

            if response.status == 204:
                logger.info(f"Updated issue description for {issue_key}")
                return {"status": "updated", "issue_key": issue_key}
            else:
                logger.error(f"Failed to update issue: {response.status}")
                raise Exception(f"Failed to update issue: {response.status}")

    async def create_documentation_issue(
        self,
        project_key: str,
        summary: str,
        description: str,
        components: List[str] = None,
    ) -> Dict:
        """Create a new documentation issue."""
        payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "description": description,
                "issuetype": {"name": "Task"},  # or "Documentation" if available
                "labels": ["documentation", "kinexus-ai-generated"],
            }
        }

        # Add components if specified
        if components:
            payload["fields"]["components"] = [{"name": comp} for comp in components]

        url = f"{self.server_url}/rest/api/3/issue"

        async with aiohttp.ClientSession() as session:
            response = await session.post(
                url,
                auth=aiohttp.BasicAuth(self.auth[0], self.auth[1]),
                headers=self.headers,
                json=payload,
            )

            if response.status in [200, 201]:
                result = await response.json()
                logger.info(f"Created documentation issue: {result['key']}")
                return result
            else:
                logger.error(f"Failed to create issue: {response.status}")
                raise Exception(f"Failed to create issue: {response.status}")

    async def link_issues(
        self, inward_issue: str, outward_issue: str, link_type: str = "Relates"
    ) -> Dict:
        """Create a link between two issues."""
        url = f"{self.server_url}/rest/api/3/issueLink"
        payload = {
            "type": {"name": link_type},
            "inwardIssue": {"key": inward_issue},
            "outwardIssue": {"key": outward_issue},
        }

        async with aiohttp.ClientSession() as session:
            response = await session.post(
                url,
                auth=aiohttp.BasicAuth(self.auth[0], self.auth[1]),
                headers=self.headers,
                json=payload,
            )

            if response.status in [200, 201]:
                logger.info(f"Linked issues {inward_issue} and {outward_issue}")
                return {"status": "linked"}
            else:
                logger.error(f"Failed to link issues: {response.status}")
                raise Exception(f"Failed to link issues: {response.status}")

    async def find_related_issues(
        self, keywords: List[str], project_keys: List[str] = None
    ) -> List[Dict]:
        """Find issues that might need documentation updates based on keywords."""
        # Build JQL query
        text_conditions = " OR ".join([f'text ~ "{keyword}"' for keyword in keywords])

        if project_keys:
            project_condition = f"project in ({','.join(project_keys)})"
            jql = f"({project_condition}) AND ({text_conditions})"
        else:
            jql = text_conditions

        # Add filters for relevant issue types
        jql += ' AND issuetype in ("Story", "Bug", "Task", "Epic")'
        jql += " ORDER BY updated DESC"

        issues = await self.search_issues(jql)

        # Score relevance based on keyword matches
        for issue in issues:
            description = issue.get("fields", {}).get("description", "") or ""
            summary = issue.get("fields", {}).get("summary", "") or ""
            content = (description + " " + summary).lower()

            score = sum(1 for keyword in keywords if keyword.lower() in content)
            issue["relevance_score"] = score

        # Sort by relevance
        issues.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

        return issues


class JiraDocumentationManager:
    """
    High-level documentation management for Jira projects.
    """

    def __init__(self, client: JiraClient):
        self.client = client

    async def process_code_change(self, change_data: Dict) -> List[Dict]:
        """
        Process a code change and update related Jira documentation.
        """
        results = []

        # Extract keywords from the change
        keywords = self._extract_keywords(change_data)
        project_keys = change_data.get("jira_projects", [])

        # Find related issues
        related_issues = await self.client.find_related_issues(keywords, project_keys)

        logger.info(f"Found {len(related_issues)} related issues for update")

        # Update each related issue
        for issue in related_issues[:10]:  # Limit to top 10 most relevant
            try:
                # Determine what needs updating
                update_strategy = await self._determine_update_strategy(
                    issue, change_data
                )

                if update_strategy["needs_update"]:
                    result = await self._apply_update(
                        issue, update_strategy, change_data
                    )
                    results.append(result)
                else:
                    logger.debug(f"Issue {issue['key']} doesn't need updates")
            except Exception as e:
                logger.error(f"Failed to update issue {issue['key']}: {e}")
                results.append(
                    {"issue_key": issue["key"], "status": "error", "error": str(e)}
                )

        return results

    async def create_documentation_from_change(self, change_data: Dict) -> Dict:
        """
        Create new documentation issues for significant changes.
        """
        if not change_data.get("jira_projects"):
            return {"status": "skipped", "reason": "No Jira projects configured"}

        project_key = change_data["jira_projects"][0]  # Use first project

        # Generate summary and description
        summary = f"Documentation update needed: {change_data.get('commit_message', 'Code changes')}"

        description = f"""h2. Code Changes Requiring Documentation Update

*Repository:* {change_data.get('repository', 'Unknown')}
*Branch:* {change_data.get('branch', 'Unknown')}
*Commit:* {change_data.get('commit_sha', 'Unknown')}

h3. Files Changed:
{self._format_file_list(change_data.get('files_changed', []))}

h3. Change Summary:
{change_data.get('commit_message', 'No commit message provided')}

h3. Documentation Tasks:
- [ ] Review affected documentation sections
- [ ] Update API documentation if applicable
- [ ] Update user guides and tutorials
- [ ] Update troubleshooting guides
- [ ] Verify all links and references

h3. Additional Context:
This issue was automatically created by Kinexus AI to track documentation updates needed for recent code changes.
"""

        try:
            result = await self.client.create_documentation_issue(
                project_key=project_key,
                summary=summary,
                description=description,
                components=change_data.get("components", []),
            )

            return {
                "status": "created",
                "issue_key": result["key"],
                "issue_url": f"{self.client.server_url}/browse/{result['key']}",
            }
        except Exception as e:
            logger.error(f"Failed to create documentation issue: {e}")
            return {"status": "error", "error": str(e)}

    def _extract_keywords(self, change_data: Dict) -> List[str]:
        """Extract relevant keywords from change data for searching."""
        keywords = []

        # From file paths
        if "files_changed" in change_data:
            for file in change_data["files_changed"]:
                # Extract meaningful parts from file path
                parts = file.split("/")
                keywords.extend(
                    [p for p in parts if not p.startswith(".") and len(p) > 2]
                )

        # From commit messages
        if "commit_message" in change_data:
            # Extract significant words
            words = change_data["commit_message"].split()
            keywords.extend([w for w in words if len(w) > 3 and not w.startswith("#")])

        # From function/class names if available
        if "code_entities" in change_data:
            keywords.extend(change_data["code_entities"])

        return list(set(keywords))  # Unique keywords

    async def _determine_update_strategy(self, issue: Dict, change_data: Dict) -> Dict:
        """Determine what sections need updating based on the change."""
        fields = issue.get("fields", {})
        description = fields.get("description", "") or ""
        summary = fields.get("summary", "") or ""
        issue_type = fields.get("issuetype", {}).get("name", "").lower()

        strategy = {"needs_update": False, "update_type": None, "action": None}

        # Check if issue mentions changed files
        for file in change_data.get("files_changed", []):
            if file in description or file in summary:
                strategy["needs_update"] = True
                strategy["update_type"] = "code_reference"
                strategy["action"] = "add_comment"
                break

        # Check if it's a documentation-related issue
        if any(keyword in issue_type for keyword in ["doc", "story", "task"]):
            if any(
                keyword in description.lower()
                for keyword in ["api", "guide", "tutorial"]
            ):
                strategy["needs_update"] = True
                strategy["update_type"] = "documentation_task"
                strategy["action"] = "add_comment"

        return strategy

    async def _apply_update(
        self, issue: Dict, strategy: Dict, change_data: Dict
    ) -> Dict:
        """Apply the determined updates to the issue."""
        issue_key = issue["key"]

        if strategy["action"] == "add_comment":
            # Create a comment with the update information
            comment_body = f"""*Automated Documentation Update*

The code referenced in this issue has been updated:

*Repository:* {change_data.get('repository', 'Unknown')}
*Commit:* {change_data.get('commit_sha', 'Unknown')}
*Message:* {change_data.get('commit_message', 'No message')}

*Files Changed:*
{self._format_file_list(change_data.get('files_changed', []))}

Please review if this issue's documentation requirements have been affected.

_Comment added automatically by Kinexus AI_"""

            result = await self.client.add_comment(issue_key, comment_body)

            return {
                "status": "updated",
                "issue_key": issue_key,
                "action": "comment_added",
                "comment_id": result.get("id"),
            }

        return {"status": "no_action", "issue_key": issue_key}

    def _format_file_list(self, files: List[str]) -> str:
        """Format file list for Jira markup."""
        if not files:
            return "No files specified"

        return "\n".join([f"* {{code}}{file}{{code}}" for file in files])


class JiraIntegration(BaseIntegration):
    """Jira integration for issue tracking and project management."""

    def __init__(self, integration):
        super().__init__(integration)
        self.required_config_fields = [
            "server_url",
            "username",
            "api_token",
            "projects",
        ]
        self._client = None
        self._doc_manager = None

    @property
    def client(self) -> JiraClient:
        """Get or create Jira client."""
        if not self._client:
            config = self.integration.config
            self._client = JiraClient(
                server_url=config["server_url"],
                username=config["username"],
                api_token=config["api_token"],
            )
        return self._client

    @property
    def doc_manager(self) -> JiraDocumentationManager:
        """Get or create documentation manager."""
        if not self._doc_manager:
            self._doc_manager = JiraDocumentationManager(self.client)
        return self._doc_manager

    async def test_connection(self) -> TestResult:
        """Test connection to Jira API."""
        try:
            # Test basic authentication by getting current user (API v3 2025)
            url = f"{self.client.server_url}/rest/api/3/myself"

            async with aiohttp.ClientSession() as session:
                response = await session.get(
                    url,
                    auth=aiohttp.BasicAuth(self.client.auth[0], self.client.auth[1]),
                    headers=self.client.headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                )

                if response.status == 200:
                    data = await response.json()
                    return TestResult(
                        success=True,
                        message="Connection successful",
                        details={
                            "user": data.get("displayName"),
                            "account_id": data.get("accountId"),
                            "server": self.client.server_url,
                        },
                    )
                else:
                    return TestResult(
                        success=False,
                        message=f"HTTP {response.status}: Authentication failed",
                    )

        except Exception as e:
            return TestResult(success=False, message=f"Connection failed: {str(e)}")

    async def sync(self) -> SyncResult:
        """Sync data from Jira projects."""
        try:
            projects = self.integration.config.get("projects", [])
            total_issues = 0

            for project_key in projects:
                # Get recent issues from this project
                jql = (
                    f"project = {project_key} AND updated >= -7d ORDER BY updated DESC"
                )
                issues = await self.client.search_issues(jql, max_results=50)
                total_issues += len(issues)

                logger.info(f"Synced {len(issues)} issues from project {project_key}")

            return SyncResult(
                success=True,
                records_processed=total_issues,
                metadata={
                    "projects_synced": len(projects),
                    "sync_type": "recent_issues",
                },
            )

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            return SyncResult(success=False, records_processed=0, error=str(e))

    async def process_webhook(self, event_type: str, payload: Dict[str, Any]) -> bool:
        """Process Jira webhook events."""
        self.log_webhook_received(event_type)

        try:
            if event_type in ["jira:issue_created", "jira:issue_updated"]:
                issue_data = payload.get("issue", {})
                issue_key = issue_data.get("key")

                if issue_key:
                    logger.info(f"Processing Jira webhook for issue {issue_key}")

                    # Here you could trigger documentation analysis
                    # For now, just log the event
                    fields = issue_data.get("fields", {})
                    issue_type = fields.get("issuetype", {}).get("name", "")
                    summary = fields.get("summary", "")

                    logger.info(f"Issue {issue_key} ({issue_type}): {summary}")

                    return True

            logger.debug(f"Unhandled Jira webhook event: {event_type}")
            return True

        except Exception as e:
            logger.error(f"Error processing Jira webhook: {e}")
            return False

    async def handle_code_change(self, change_data: Dict) -> Dict:
        """Handle code changes and update related Jira documentation."""
        try:
            # Add Jira project configuration to change data
            change_data["jira_projects"] = self.integration.config.get("projects", [])

            # Process the change and update related issues
            update_results = await self.doc_manager.process_code_change(change_data)

            # Optionally create a new documentation issue for significant changes
            create_result = None
            if change_data.get("impact_score", 0) > 7:  # High impact changes
                create_result = await self.doc_manager.create_documentation_from_change(
                    change_data
                )

            return {
                "status": "processed",
                "updates": update_results,
                "new_issue": create_result,
                "summary": f"Updated {len(update_results)} issues",
            }

        except Exception as e:
            logger.error(f"Error handling code change: {e}")
            return {"status": "error", "error": str(e)}
