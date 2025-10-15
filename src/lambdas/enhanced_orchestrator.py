"""
Enhanced Document Orchestrator - With Real Platform Integrations
Core philosophy: Update documentation where it already lives
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3
import structlog
from botocore.config import Config

logger = structlog.get_logger()

# AWS Clients
config = Config(
    region_name="us-east-1", retries={"max_attempts": 3, "mode": "adaptive"}
)

dynamodb = boto3.resource("dynamodb", config=config)
bedrock = boto3.client("bedrock-runtime", config=config)
ssm = boto3.client("ssm", config=config)
eventbridge = boto3.client("events", config=config)

# Environment variables
CHANGES_TABLE = os.environ.get("CHANGES_TABLE", "kinexus-changes")
DOCUMENTS_TABLE = os.environ.get("DOCUMENTS_TABLE", "kinexus-documents")
EVENT_BUS = os.environ.get("EVENT_BUS", "kinexus-events")

# AI Model - Claude 4 Opus for September 2025
CLAUDE_MODEL_ID = "anthropic.claude-4-opus-20250805"


class PlatformOrchestrator:
    """
    Manages documentation updates across GitHub, Confluence, and SharePoint.
    This is the real implementation that updates docs where they live.
    """

    def __init__(self):
        self.changes_table = dynamodb.Table(CHANGES_TABLE)
        self.documents_table = dynamodb.Table(DOCUMENTS_TABLE)
        self.clients = self._init_clients()

    def _init_clients(self) -> Dict:
        """Initialize platform clients dynamically."""
        clients = {}

        # Import clients conditionally to handle Lambda layer
        try:
            # These would be in the Lambda layer at runtime
            from integrations.confluence_client import (
                ConfluenceClient,
                ConfluenceDocumentManager,
            )
            from integrations.github_client import GitHubClient, GitHubDocumentManager
            from integrations.sharepoint_client import (
                SharePointClient,
                SharePointDocumentManager,
            )

            # GitHub
            github_token = self._get_secret("github_token")
            if github_token:
                clients["github"] = {
                    "client": GitHubClient(github_token),
                    "manager": GitHubDocumentManager(GitHubClient(github_token)),
                }

            # Confluence
            confluence_url = self._get_secret("confluence_url")
            confluence_user = self._get_secret("confluence_user")
            confluence_token = self._get_secret("confluence_token")
            if all([confluence_url, confluence_user, confluence_token]):
                client = ConfluenceClient(
                    confluence_url, confluence_user, confluence_token
                )
                clients["confluence"] = {
                    "client": client,
                    "manager": ConfluenceDocumentManager(client),
                }

            # SharePoint
            sp_tenant = self._get_secret("sharepoint_tenant_id")
            sp_client = self._get_secret("sharepoint_client_id")
            sp_secret = self._get_secret("sharepoint_client_secret")
            sp_site = self._get_secret("sharepoint_site_url")
            if all([sp_tenant, sp_client, sp_secret, sp_site]):
                client = SharePointClient(sp_tenant, sp_client, sp_secret, sp_site)
                clients["sharepoint"] = {
                    "client": client,
                    "manager": SharePointDocumentManager(client),
                }

        except ImportError:
            logger.warning("Integration clients not available in Lambda layer")

        return clients

    def _get_secret(self, key: str) -> Optional[str]:
        """Get secret from SSM Parameter Store or environment."""
        try:
            response = ssm.get_parameter(Name=f"/kinexus/{key}", WithDecryption=True)
            return response["Parameter"]["Value"]
        except Exception:
            return os.environ.get(key.upper())

    async def process_change(self, change_id: str) -> Dict[str, Any]:
        """
        Main entry point: Process a change and update all relevant documentation.
        """
        # Get change data
        change = self.changes_table.get_item(Key={"change_id": change_id})
        if "Item" not in change:
            logger.error(f"Change not found: {change_id}")
            return {"error": "Change not found"}

        change_data = change["Item"]

        logger.info(
            "Processing change",
            change_id=change_id,
            source=change_data.get("source"),
            repo=change_data.get("change_data", {}).get("repository_name"),
        )

        # Step 1: Analyze impact using AI
        impact = await self.analyze_impact(change_data)

        if impact["action"] == "none":
            logger.info("No documentation updates needed")
            return {"status": "no_updates_needed"}

        # Step 2: Find affected documents across platforms
        affected_docs = await self.find_affected_documents(change_data, impact)

        # Step 3: Generate updates using AI
        updates = await self.generate_updates(change_data, affected_docs)

        # Step 4: Apply updates to each platform
        results = await self.apply_updates(updates)

        # Step 5: Record results
        self._record_results(change_id, results)

        return results

    async def analyze_impact(self, change_data: Dict) -> Dict:
        """
        Use Claude 4 to analyze what documentation needs updating.
        """
        # Build context
        context = {
            "source": change_data.get("source"),
            "repository": change_data.get("change_data", {}).get("repository_name"),
            "files_changed": change_data.get("change_data", {}).get(
                "files_changed", []
            )[:20],
            "commits": [
                c["message"]
                for c in change_data.get("change_data", {}).get("commits", [])[:10]
            ],
            "timestamp": change_data.get("timestamp"),
        }

        prompt = f"""
        Analyze this change and determine documentation impact.

        Change: {json.dumps(context, indent=2)}

        Consider:
        1. What types of documentation need updating? (README, API docs, guides)
        2. Which platforms likely have this documentation? (GitHub, Confluence, SharePoint)
        3. What is the priority? (critical, high, medium, low)

        IMPORTANT: We UPDATE existing docs, not create new ones.

        Return JSON:
        {{
            "action": "update" or "none",
            "doc_types": ["README", "API", "Configuration"],
            "platforms": ["github", "confluence"],
            "priority": "high",
            "reasoning": "explanation"
        }}
        """

        try:
            # Call Claude 4 Opus
            response = bedrock.invoke_model(
                modelId=CLAUDE_MODEL_ID,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(
                    {
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 1500,
                        "temperature": 0.3,
                    }
                ),
            )

            result = json.loads(response["body"].read())
            # Extract JSON from response
            import re

            json_match = re.search(
                r"\{.*\}", result.get("content", [{}])[0].get("text", ""), re.DOTALL
            )
            if json_match:
                return json.loads(json_match.group())

        except Exception as e:
            logger.error(f"AI analysis error: {e}")

        # Fallback logic
        return self._simple_impact_analysis(change_data)

    def _simple_impact_analysis(self, change_data: Dict) -> Dict:
        """Fallback when AI is unavailable."""
        files = change_data.get("change_data", {}).get("files_changed", [])

        # Simple heuristics
        if any("README" in f for f in files):
            return {
                "action": "update",
                "doc_types": ["README"],
                "platforms": ["github"],
                "priority": "high",
                "reasoning": "README file changed",
            }

        if any(f.endswith((".py", ".js", ".ts", ".java")) for f in files):
            return {
                "action": "update",
                "doc_types": ["API", "Configuration"],
                "platforms": ["github", "confluence"],
                "priority": "medium",
                "reasoning": "Code files changed",
            }

        return {"action": "none"}

    async def find_affected_documents(
        self, change_data: Dict, impact: Dict
    ) -> List[Dict]:
        """
        Find documents that need updating across all platforms.
        """
        affected = []

        # Build search keywords
        keywords = self._extract_keywords(change_data)

        # Search each platform
        for platform in impact.get("platforms", []):
            if platform not in self.clients:
                continue

            try:
                if platform == "github":
                    docs = await self._find_github_docs(change_data, keywords)
                elif platform == "confluence":
                    docs = await self._find_confluence_docs(keywords)
                elif platform == "sharepoint":
                    docs = await self._find_sharepoint_docs(keywords)
                else:
                    continue

                affected.extend(docs)

            except Exception as e:
                logger.error(f"Error searching {platform}: {e}")

        return affected

    def _extract_keywords(self, change_data: Dict) -> List[str]:
        """Extract search keywords from change data."""
        keywords = []

        # From file paths
        for file in change_data.get("change_data", {}).get("files_changed", []):
            # Extract meaningful parts
            parts = file.replace("/", " ").replace("_", " ").replace("-", " ").split()
            keywords.extend([p for p in parts if len(p) > 2])

        # From commit messages
        for commit in change_data.get("change_data", {}).get("commits", []):
            msg_words = commit["message"].split()
            keywords.extend([w for w in msg_words if len(w) > 3])

        return list(set(keywords))[:20]  # Unique, limited

    async def _find_github_docs(
        self, change_data: Dict, keywords: List[str]
    ) -> List[Dict]:
        """Find GitHub documents to update."""
        docs = []
        repo = change_data.get("change_data", {}).get("repository_name")

        if not repo or "github" not in self.clients:
            return docs

        # Check standard documentation files
        doc_files = [
            "README.md",
            "CONTRIBUTING.md",
            "docs/API.md",
            "docs/Configuration.md",
        ]

        for file_path in doc_files:
            try:
                file_data = await self.clients["github"]["client"].get_file(
                    repo, file_path
                )
                if file_data:
                    docs.append(
                        {
                            "platform": "github",
                            "repo": repo,
                            "path": file_path,
                            "sha": file_data["sha"],
                            "type": "markdown",
                        }
                    )
            except Exception:
                pass

        return docs

    async def _find_confluence_docs(self, keywords: List[str]) -> List[Dict]:
        """Find Confluence pages to update."""
        if "confluence" not in self.clients:
            return []

        # Build CQL query
        keyword_conditions = " OR ".join([f'text ~ "{kw}"' for kw in keywords[:5]])
        cql = f"type = page AND ({keyword_conditions})"

        pages = await self.clients["confluence"]["client"].search_pages(cql, limit=10)

        return [
            {
                "platform": "confluence",
                "page_id": p["id"],
                "title": p["title"],
                "version": p["version"]["number"],
                "type": "confluence",
            }
            for p in pages
        ]

    async def _find_sharepoint_docs(self, keywords: List[str]) -> List[Dict]:
        """Find SharePoint documents to update."""
        if "sharepoint" not in self.clients:
            return []

        query = " OR ".join(keywords[:5])
        docs = await self.clients["sharepoint"]["client"].search_documents(query)

        return [
            {
                "platform": "sharepoint",
                "document_id": d.get("id"),
                "name": d.get("name"),
                "path": d.get("webUrl"),
                "type": "sharepoint",
            }
            for d in docs[:5]
        ]

    async def generate_updates(
        self, change_data: Dict, affected_docs: List[Dict]
    ) -> List[Dict]:
        """
        Generate update content for each affected document using AI.
        """
        updates = []

        for doc in affected_docs:
            try:
                # Generate update content
                content = await self._generate_update_content(change_data, doc)

                updates.append(
                    {"document": doc, "content": content, "status": "pending"}
                )

            except Exception as e:
                logger.error(f"Error generating update for {doc}: {e}")

        return updates

    async def _generate_update_content(self, change_data: Dict, doc: Dict) -> str:
        """
        Generate the actual update content using Claude 4.
        """
        prompt = f"""
        Generate a documentation update based on this change:

        Change:
        - Repository: {change_data.get('change_data', {}).get('repository_name')}
        - Files: {change_data.get('change_data', {}).get('files_changed', [])}
        - Message: {change_data.get('change_data', {}).get('commit_message')}

        Document to update:
        - Platform: {doc['platform']}
        - Path/Title: {doc.get('path', doc.get('title', 'Unknown'))}
        - Type: {doc['type']}

        Generate a concise update that:
        1. Explains what changed
        2. Updates any code examples if relevant
        3. Notes breaking changes
        4. Maintains the document's existing style

        Return ONLY the update content, not the entire document.
        """

        try:
            response = bedrock.invoke_model(
                modelId=CLAUDE_MODEL_ID,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(
                    {
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 2000,
                        "temperature": 0.5,
                    }
                ),
            )

            result = json.loads(response["body"].read())
            return result.get("content", [{}])[0].get("text", "")

        except Exception as e:
            logger.error(f"Error generating content: {e}")
            # Fallback content
            return f"""
### System Update

**Date:** {datetime.utcnow().isoformat()}
**Change:** {change_data.get('change_data', {}).get('commit_message', 'System update')}

Files affected:
{chr(10).join('- ' + f for f in change_data.get('change_data', {}).get('files_changed', [])[:5])}

Please review these changes and update any dependent systems.

*Automatically updated by Kinexus AI*
"""

    async def apply_updates(self, updates: List[Dict]) -> Dict:
        """
        Apply updates to each platform.
        """
        results = {"github": [], "confluence": [], "sharepoint": [], "summary": {}}

        for update in updates:
            doc = update["document"]
            content = update["content"]
            platform = doc["platform"]

            try:
                if platform == "github" and "github" in self.clients:
                    result = await self._update_github_doc(doc, content)
                    results["github"].append(result)

                elif platform == "confluence" and "confluence" in self.clients:
                    result = await self._update_confluence_doc(doc, content)
                    results["confluence"].append(result)

                elif platform == "sharepoint" and "sharepoint" in self.clients:
                    result = await self._update_sharepoint_doc(doc, content)
                    results["sharepoint"].append(result)

            except Exception as e:
                logger.error(f"Error updating {platform} doc: {e}")
                results[platform].append({"error": str(e)})

        # Calculate summary
        total_success = sum(
            len([r for r in results[p] if "error" not in r])
            for p in ["github", "confluence", "sharepoint"]
        )
        total_failed = sum(
            len([r for r in results[p] if "error" in r])
            for p in ["github", "confluence", "sharepoint"]
        )

        results["summary"] = {
            "total_updated": total_success,
            "total_failed": total_failed,
            "platforms_updated": [p for p in results if results[p]],
            "success_rate": (
                (total_success / (total_success + total_failed) * 100)
                if (total_success + total_failed) > 0
                else 0
            ),
        }

        return results

    async def _update_github_doc(self, doc: Dict, content: str) -> Dict:
        """Update a GitHub document."""
        client = self.clients["github"]["client"]

        # Get current content
        current = await client.get_file_content(doc["repo"], doc["path"])
        if not current:
            return {"error": "File not found"}

        # Merge update (simplified - in production, use proper merging)
        updated = current + "\n\n" + content

        # Update file
        result = await client.update_file(
            repo=doc["repo"],
            path=doc["path"],
            content=updated,
            message="AI: Update documentation - automated by Kinexus",
            sha=doc["sha"],
        )

        return {
            "platform": "github",
            "path": doc["path"],
            "commit": result.get("commit", {}).get("sha"),
        }

    async def _update_confluence_doc(self, doc: Dict, content: str) -> Dict:
        """Update a Confluence page."""
        client = self.clients["confluence"]["client"]

        result = await client.update_page_section(
            page_id=doc["page_id"],
            section_heading="Updates",
            new_section_content=content,
            update_reason="Automated update from code changes",
        )

        return {
            "platform": "confluence",
            "page_id": doc["page_id"],
            "title": doc["title"],
            "version": result.get("version"),
        }

    async def _update_sharepoint_doc(self, doc: Dict, content: str) -> Dict:
        """Update a SharePoint document."""
        manager = self.clients["sharepoint"]["manager"]

        # Simplified - in production, extract proper library and path
        result = await manager._update_document(doc, {"content": content})

        return {
            "platform": "sharepoint",
            "document": doc["name"],
            "status": result.get("status"),
        }

    def _record_results(self, change_id: str, results: Dict):
        """Record processing results."""
        self.changes_table.update_item(
            Key={"change_id": change_id},
            UpdateExpression="SET #status = :status, processed_at = :timestamp, results = :results",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": "completed",
                ":timestamp": datetime.utcnow().isoformat(),
                ":results": results["summary"],
            },
        )

        # Publish event
        eventbridge.put_events(
            Entries=[
                {
                    "Source": "kinexus.orchestrator",
                    "DetailType": "DocumentationUpdated",
                    "Detail": json.dumps(
                        {
                            "change_id": change_id,
                            "summary": results["summary"],
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    ),
                    "EventBusName": EVENT_BUS,
                }
            ]
        )


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler entry point.
    """
    try:
        orchestrator = PlatformOrchestrator()

        # Handle EventBridge events
        if "detail-type" in event and event["detail-type"] == "ChangeDetected":
            change_id = event["detail"]["change_id"]
            result = asyncio.run(orchestrator.process_change(change_id))

        # Handle direct invocation
        elif "change_id" in event:
            result = asyncio.run(orchestrator.process_change(event["change_id"]))

        else:
            return {"statusCode": 400, "body": json.dumps({"error": "Invalid event"})}

        return {"statusCode": 200, "body": json.dumps(result)}

    except Exception as e:
        logger.error(f"Lambda error: {e}", exc_info=True)
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
