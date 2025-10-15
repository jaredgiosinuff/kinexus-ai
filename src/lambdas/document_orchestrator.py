"""
Document Orchestrator Lambda
Core agent that processes changes and orchestrates documentation updates
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3
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

# AI Model configuration
CLAUDE_MODEL_ID = "anthropic.claude-3-opus-20240229"  # Use available model


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
            f"Processing change",
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
            UpdateExpression="SET #status = :status, processed = :processed, processed_at = :timestamp",
            ExpressionAttributeNames={"#status": "status"},
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
        """Analyze what documentation needs to be created or updated"""

        files_changed = change_data.get("change_data", {}).get("files_changed", [])
        commits = change_data.get("change_data", {}).get("commits", [])

        # Build context for AI analysis
        context = {
            "files_changed": files_changed,
            "commit_messages": [c["message"] for c in commits],
            "repository": change_data.get("change_data", {}).get("repository_name"),
        }

        # Use Claude to analyze impact
        prompt = self._build_analysis_prompt(context)

        try:
            response = bedrock.invoke_model(
                modelId=CLAUDE_MODEL_ID,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(
                    {
                        "prompt": f"\n\nHuman: {prompt}\n\nAssistant:",
                        "max_tokens_to_sample": 1000,
                        "temperature": 0.3,
                        "top_p": 0.9,
                    }
                ),
            )

            result_text = json.loads(response["body"].read())["completion"]

            # Parse the structured response
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

        except Exception as e:
            logger.error(f"Error analyzing impact: {str(e)}", exc_info=True)
            return {"action": "error", "error": str(e)}

    async def create_documentation(
        self, change_data: Dict[str, Any], analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create new documentation based on changes"""

        # Build generation prompt
        prompt = self._build_generation_prompt(change_data, analysis, is_update=False)

        try:
            # Generate content with Claude
            response = bedrock.invoke_model(
                modelId=CLAUDE_MODEL_ID,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(
                    {
                        "prompt": f"\n\nHuman: {prompt}\n\nAssistant:",
                        "max_tokens_to_sample": 4000,
                        "temperature": 0.5,
                        "top_p": 0.95,
                    }
                ),
            )

            generated_content = json.loads(response["body"].read())["completion"]

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

            logger.info(f"Documentation created", document_id=document_id)

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

        files = change_data.get("change_data", {}).get("files_changed", [])
        commits = change_data.get("change_data", {}).get("commits", [])

        return f"""
        Generate technical documentation for the following changes:

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

            logger.info(f"Processing change from EventBridge", change_id=change_id)

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
