"""
Document Orchestrator Lambda
Core agent that processes changes and orchestrates documentation updates
"""

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List
from urllib.parse import quote

import boto3
import requests
import structlog
from botocore.config import Config

logger = structlog.get_logger()

# AWS Clients with retry config
config = Config(
    region_name="us-east-1", retries={"max_attempts": 3, "mode": "adaptive"}
)

dynamodb = boto3.resource("dynamodb", config=config)
s3 = boto3.client("s3", config=config)
bedrock = boto3.client("bedrock-runtime", config=config)
eventbridge = boto3.client("events", config=config)

# Environment variables
CHANGES_TABLE = os.environ.get("CHANGES_TABLE", "kinexus-changes")
DOCUMENTS_TABLE = os.environ.get("DOCUMENTS_TABLE", "kinexus-documents")
DOCUMENTS_BUCKET = os.environ.get("DOCUMENTS_BUCKET", "kinexus-documents")
EVENT_BUS = os.environ.get("EVENT_BUS", "kinexus-events")

# Confluence configuration
CONFLUENCE_URL = os.environ.get("CONFLUENCE_URL", "")
CONFLUENCE_SPACE = os.environ.get("CONFLUENCE_SPACE", "")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL", "")
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN", "")

# AI Model configuration
CLAUDE_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"  # Claude 3 Haiku - fast, cost-effective, on-demand


def search_confluence(cql_query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search Confluence using CQL (Confluence Query Language)

    Args:
        cql_query: CQL query string (e.g., "text~'authentication'")
        limit: Maximum number of results to return

    Returns:
        List of matching Confluence pages with title, id, and URL
    """
    if not CONFLUENCE_URL or not JIRA_EMAIL or not JIRA_API_TOKEN:
        logger.warning("Confluence credentials not configured")
        return []

    try:
        search_url = f"{CONFLUENCE_URL}/rest/api/content/search"
        params = {
            "cql": cql_query,
            "limit": limit,
            "expand": "version,body.storage"
        }

        response = requests.get(
            search_url,
            params=params,
            auth=(JIRA_EMAIL, JIRA_API_TOKEN),
            timeout=10
        )
        response.raise_for_status()

        results = response.json().get("results", [])

        # Extract relevant fields
        pages = []
        for result in results:
            pages.append({
                "id": result["id"],
                "title": result["title"],
                "url": f"{CONFLUENCE_URL}/wiki{result['_links']['webui']}",
                "version": result.get("version", {}).get("number", 1),
                "space": result.get("space", {}).get("key", ""),
                "content_preview": result.get("body", {}).get("storage", {}).get("value", "")[:500]
            })

        logger.info(f"Confluence search returned {len(pages)} results", cql=cql_query)
        return pages

    except Exception as e:
        logger.error(f"Confluence search failed: {e}", cql=cql_query)
        return []


def extract_keywords_from_text(text: str, max_keywords: int = 5) -> List[str]:
    """
    Extract meaningful keywords from text

    Args:
        text: Input text (summary, description, etc.)
        max_keywords: Maximum number of keywords to extract

    Returns:
        List of keywords
    """
    # Remove common stop words
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
        "been", "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "should", "could", "may", "might", "must", "can", "this",
        "that", "these", "those", "i", "you", "he", "she", "it", "we", "they"
    }

    # Clean and tokenize
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())

    # Filter stop words and get unique keywords
    keywords = []
    seen = set()
    for word in words:
        if word not in stop_words and word not in seen:
            keywords.append(word)
            seen.add(word)
            if len(keywords) >= max_keywords:
                break

    return keywords


class DocumentOrchestrator:
    """Main orchestration logic for documentation processing"""

    def __init__(self):
        self.changes_table = dynamodb.Table(CHANGES_TABLE)
        self.documents_table = dynamodb.Table(DOCUMENTS_TABLE)

    async def process_change(self, change_id: str) -> Dict[str, Any]:
        """Process a single change event"""

        # Get change details from DynamoDB
        change = self.changes_table.get_item(Key={"change_id": change_id})
        if "Item" not in change:
            logger.error(f"Change not found: {change_id}")
            return {"error": "Change not found"}

        change_data = change["Item"]
        logger.info(
            "Processing change",
            change_id=change_id,
            repository=change_data.get("change_data", {}).get("repository_name"),
        )

        # Analyze what documentation needs updating
        analysis = await self.analyze_documentation_impact(change_data)

        # Generate or update documentation
        if analysis["action"] == "create":
            result = await self.create_documentation(change_data, analysis)
        elif analysis["action"] == "update":
            result = await self.update_documentation(change_data, analysis)
        else:
            result = {"message": "No documentation changes needed"}

        # Update change status
        self.changes_table.update_item(
            Key={"change_id": change_id},
            UpdateExpression="SET #status = :status, #processed = :processed, processed_at = :timestamp",
            ExpressionAttributeNames={"#status": "status", "#processed": "processed"},
            ExpressionAttributeValues={
                ":status": "completed",
                ":processed": True,
                ":timestamp": datetime.utcnow().isoformat(),
            },
        )

        return result

    async def analyze_documentation_impact(
        self, change_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze what documentation needs to be created or updated using Confluence search"""

        # Determine if this is a Jira ticket or GitHub change
        files_changed = change_data.get("change_data", {}).get("files_changed", [])
        ticket_summary = change_data.get("change_data", {}).get("summary", "")
        ticket_description = change_data.get("change_data", {}).get("documentation_context", {}).get("description", "")

        is_jira_ticket = not files_changed and ticket_summary

        if is_jira_ticket:
            # JIRA-ONLY WORKFLOW: Search Confluence with keywords
            logger.info("Processing Jira ticket", summary=ticket_summary)

            # Extract keywords from ticket
            combined_text = f"{ticket_summary} {ticket_description}"
            keywords = extract_keywords_from_text(combined_text, max_keywords=8)

            if not keywords:
                return {
                    "action": "create",
                    "reason": "No keywords extracted, creating new documentation",
                    "jira_ticket": ticket_summary
                }

            # Try multiple search strategies
            search_results = []

            # Strategy 1: Combined keywords
            cql_query = f"type=page AND text~'{' '.join(keywords[:3])}'"
            results_combined = search_confluence(cql_query, limit=5)
            search_results.extend(results_combined)

            # Strategy 2: Individual important keywords
            for keyword in keywords[:2]:
                cql_query = f"type=page AND title~'{keyword}'"
                results_title = search_confluence(cql_query, limit=3)
                search_results.extend(results_title)

            # Remove duplicates
            seen_ids = set()
            unique_results = []
            for result in search_results:
                if result["id"] not in seen_ids:
                    unique_results.append(result)
                    seen_ids.add(result["id"])

            # Use Claude to analyze and rank results
            if unique_results:
                analysis_result = await self._analyze_confluence_results(
                    ticket_summary, ticket_description, unique_results, keywords
                )
                return analysis_result
            else:
                # No results found - create new documentation
                return {
                    "action": "create",
                    "reason": "No related Confluence pages found, creating new documentation",
                    "jira_ticket": ticket_summary,
                    "keywords": keywords
                }

        else:
            # GITHUB WORKFLOW (existing logic)
            commits = change_data.get("change_data", {}).get("commits", [])
            context = {
                "files_changed": files_changed,
                "commit_messages": [c["message"] for c in commits],
                "repository": change_data.get("change_data", {}).get("repository_name"),
            }

            # For MVP, simple logic - if README changed, update it
            if any("README" in f for f in files_changed):
                return {
                    "action": "update",
                    "target": "README.md",
                    "reason": "README file was directly modified",
                }
            elif any(
                f.endswith(".py") or f.endswith(".js") or f.endswith(".ts")
                for f in files_changed
            ):
                return {
                    "action": "update",
                    "target": "API_DOCUMENTATION.md",
                    "reason": "Code files were modified",
                }
            else:
                return {
                    "action": "none",
                    "reason": "No documentation-relevant changes detected",
                }

    async def _analyze_confluence_results(
        self,
        ticket_summary: str,
        ticket_description: str,
        search_results: List[Dict[str, Any]],
        keywords: List[str]
    ) -> Dict[str, Any]:
        """
        Use Claude to analyze Confluence search results and decide whether to
        update existing documentation or create new documentation

        Args:
            ticket_summary: Jira ticket summary
            ticket_description: Jira ticket description
            search_results: List of Confluence pages from search
            keywords: Extracted keywords

        Returns:
            Analysis result with action ("update" or "create") and target page
        """
        # Build prompt for Claude
        results_summary = []
        for i, result in enumerate(search_results[:5], 1):  # Top 5 results
            results_summary.append(
                f"{i}. Title: {result['title']}\n"
                f"   URL: {result['url']}\n"
                f"   Preview: {result['content_preview'][:200]}...\n"
            )

        prompt = f"""You are analyzing whether a Jira ticket should update existing Confluence documentation or create new documentation.

JIRA TICKET:
Summary: {ticket_summary}
Description: {ticket_description}
Keywords: {', '.join(keywords)}

RELATED CONFLUENCE PAGES FOUND:
{''.join(results_summary)}

TASK:
Analyze the search results and determine:
1. Is there an existing page that should be UPDATED with this change?
2. Or should we CREATE NEW documentation?

Respond ONLY with valid JSON in this exact format:
{{
    "action": "update" or "create",
    "confidence": 0-100,
    "target_page_id": "confluence page id if update, null if create",
    "target_page_title": "page title if update, suggested title if create",
    "reasoning": "brief explanation of your decision"
}}

Be conservative - only choose "update" if you're confident the existing page directly covers this topic."""

        try:
            response = bedrock.invoke_model(
                modelId=CLAUDE_MODEL_ID,
                contentType="application/json",
                accept="application/json",
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 500,
                    "messages": [{
                        "role": "user",
                        "content": prompt
                    }],
                    "temperature": 0.2,
                    "top_p": 0.9,
                }),
            )

            response_body = json.loads(response["body"].read())
            claude_response = response_body["content"][0]["text"]

            # Parse Claude's JSON response
            # Extract JSON from potential markdown code blocks
            json_match = re.search(r'\{.*\}', claude_response, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
            else:
                analysis = json.loads(claude_response)

            logger.info("Claude analysis complete",
                        action=analysis.get("action"),
                        confidence=analysis.get("confidence"))

            # Build result
            if analysis.get("action") == "update" and analysis.get("target_page_id"):
                # Find the target page details
                target_page = next(
                    (r for r in search_results if r["id"] == analysis["target_page_id"]),
                    search_results[0]  # Fallback to first result
                )
                return {
                    "action": "update",
                    "target_page_id": target_page["id"],
                    "target_page_title": target_page["title"],
                    "target_page_url": target_page["url"],
                    "target_page_version": target_page["version"],
                    "confidence": analysis.get("confidence", 50),
                    "reason": analysis.get("reasoning", "Claude recommended update"),
                    "jira_ticket": ticket_summary
                }
            else:
                # Create new documentation
                return {
                    "action": "create",
                    "suggested_title": analysis.get("target_page_title", ticket_summary),
                    "confidence": analysis.get("confidence", 50),
                    "reason": analysis.get("reasoning", "Claude recommended new doc"),
                    "jira_ticket": ticket_summary,
                    "keywords": keywords,
                    "related_pages": [r["url"] for r in search_results[:3]]
                }

        except Exception as e:
            logger.error(f"Error analyzing Confluence results with Claude: {e}")
            # Fallback: create new documentation on error
            return {
                "action": "create",
                "reason": f"Analysis error: {str(e)}, defaulting to create new doc",
                "jira_ticket": ticket_summary
            }

    async def create_documentation(
        self, change_data: Dict[str, Any], analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create new documentation based on changes"""

        # Build generation prompt
        prompt = self._build_generation_prompt(change_data, analysis, is_update=False)

        try:
            # Generate content with Claude using Messages API
            response = bedrock.invoke_model(
                modelId=CLAUDE_MODEL_ID,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(
                    {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 4000,
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.5,
                        "top_p": 0.95,
                    }
                ),
            )

            response_body = json.loads(response["body"].read())
            generated_content = response_body["content"][0]["text"]

            # Store in S3
            document_id = (
                f"doc_{change_data['change_id']}_{datetime.utcnow().timestamp()}"
            )
            s3_key = f"documents/{document_id}.md"

            s3.put_object(
                Bucket=DOCUMENTS_BUCKET,
                Key=s3_key,
                Body=generated_content.encode("utf-8"),
                ContentType="text/markdown",
                Metadata={
                    "change_id": change_data["change_id"],
                    "repository": change_data.get("change_data", {}).get(
                        "repository_name", ""
                    ),
                    "generated_at": datetime.utcnow().isoformat(),
                },
            )

            # Store metadata in DynamoDB
            self.documents_table.put_item(
                Item={
                    "document_id": document_id,
                    "title": analysis.get("target", "Documentation"),
                    "s3_key": s3_key,
                    "change_id": change_data["change_id"],
                    "repository": change_data.get("change_data", {}).get(
                        "repository_name"
                    ),
                    "created_at": datetime.utcnow().isoformat(),
                    "status": "generated",
                    "content_preview": generated_content[:500],
                }
            )

            logger.info("Documentation created", document_id=document_id)

            return {
                "action": "created",
                "document_id": document_id,
                "s3_key": s3_key,
                "preview": generated_content[:500],
            }

        except Exception as e:
            logger.error(f"Error creating documentation: {str(e)}", exc_info=True)
            return {"error": str(e)}

    async def update_documentation(
        self, change_data: Dict[str, Any], analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update existing documentation based on changes"""

        # For MVP, similar to create but with context of existing doc
        # In production, would fetch existing doc and merge changes
        return await self.create_documentation(change_data, analysis)

    def _build_analysis_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for impact analysis"""
        return f"""
        Analyze the following code changes and determine what documentation needs to be updated:

        Repository: {context['repository']}
        Files Changed: {', '.join(context['files_changed'][:10])}
        Commit Messages: {' | '.join(context['commit_messages'][:5])}

        Based on these changes, determine:
        1. Does documentation need to be updated?
        2. What type of documentation is affected (API docs, README, guides)?
        3. What is the priority of this update?

        Respond in a structured format.
        """

    def _build_generation_prompt(
        self,
        change_data: Dict[str, Any],
        analysis: Dict[str, Any],
        is_update: bool = False,
    ) -> str:
        """Build prompt for documentation generation"""

        # Check if this is a Jira ticket or GitHub change
        files = change_data.get("change_data", {}).get("files_changed", [])
        ticket_summary = change_data.get("summary", "")
        ticket_description = change_data.get("documentation_context", {}).get("description", "")

        if ticket_summary and not files:
            # JIRA TICKET PROMPT
            action_type = "Update" if is_update else "Create"
            target = analysis.get("target_page_title", analysis.get("suggested_title", ticket_summary))

            prompt = f"""Generate technical documentation for a Jira ticket that describes a system change or new feature.

JIRA TICKET:
Summary: {ticket_summary}
Description: {ticket_description}
Keywords: {', '.join(analysis.get('keywords', []))}

DOCUMENTATION TASK:
{action_type} documentation titled: "{target}"

{"Existing page to update: " + analysis.get('target_page_url', '') if is_update else "Creating new documentation."}

{"Related pages for reference: " + ', '.join(analysis.get('related_pages', [])) if analysis.get('related_pages') else ""}

REQUIREMENTS:
Generate comprehensive technical documentation in Markdown format that includes:

1. **Overview** - Brief summary of the feature/change
2. **Purpose** - Why this change was made
3. **Implementation Details** - Key technical details
4. **Usage/How-To** - Step-by-step instructions if applicable
5. **Examples** - Code snippets or configuration examples if relevant
6. **Impact** - What systems/users are affected
7. **Notes** - Any caveats, limitations, or follow-up work needed

Be thorough but concise. Use proper Markdown formatting with headers, lists, and code blocks.
Output ONLY the Markdown documentation content (no preamble or explanations)."""

            return prompt

        else:
            # GITHUB CHANGES PROMPT (original logic)
            commits = change_data.get("change_data", {}).get("commits", [])

            return f"""
Generate technical documentation for the following code changes:

Repository: {change_data.get('change_data', {}).get('repository_name')}
Target Document: {analysis.get('target', 'Documentation')}

Changes Made:
- Files: {', '.join(files[:10])}
- Commits: {[c['message'] for c in commits[:5]]}

Create clear, concise documentation that:
1. Explains what changed
2. Provides usage examples if applicable
3. Notes any breaking changes
4. Includes relevant code snippets

Format as Markdown.
"""


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler entry point"""

    try:
        # Handle EventBridge events
        if "detail-type" in event and event["detail-type"] == "ChangeDetected":
            detail = event["detail"]
            change_id = detail["change_id"]

            logger.info("Processing change from EventBridge", change_id=change_id)

            # Process the change
            orchestrator = DocumentOrchestrator()
            import asyncio

            result = asyncio.run(orchestrator.process_change(change_id))

            return {"statusCode": 200, "body": json.dumps(result)}

        # Handle direct invocation (for testing)
        elif "change_id" in event:
            orchestrator = DocumentOrchestrator()
            import asyncio

            result = asyncio.run(orchestrator.process_change(event["change_id"]))

            return {"statusCode": 200, "body": json.dumps(result)}

        else:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid event format"}),
            }

    except Exception as e:
        logger.error(f"Error in orchestrator: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"}),
        }
