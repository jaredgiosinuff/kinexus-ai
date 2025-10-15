"""
Document Processor Lambda V2
Updated to work with the new review-based workflow.

This Lambda now focuses on:
1. Processing APPROVED reviews to generate final documents
2. Updating documents in their source systems (Confluence, GitHub, etc.)
3. Handling document versioning and rollbacks
4. Integrating with the FastAPI system for status updates
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3
import httpx
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
DOCUMENTS_BUCKET = os.environ.get("DOCUMENTS_BUCKET", "kinexus-documents")
FASTAPI_BASE_URL = os.environ.get("FASTAPI_BASE_URL", "http://localhost:8000")
SERVICE_TOKEN = os.environ.get("SERVICE_TOKEN")

# AI Model configuration
CLAUDE_MODEL_ID = "anthropic.claude-3-opus-20240229"


class DocumentProcessor:
    """Processes approved reviews to generate and publish final documents"""

    def __init__(self):
        self.integration_clients = {
            "github": GitHubIntegration(),
            "confluence": ConfluenceIntegration(),
            "sharepoint": SharePointIntegration(),
        }

    async def process_approved_review(
        self, review_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process an approved review to generate and publish the final document.

        Args:
            review_data: Complete review data from the API

        Returns:
            Dict with processing results
        """
        try:
            review_id = review_data["id"]
            document_data = review_data["document"]

            logger.info(
                f"Processing approved review {review_id} for document {document_data['id']}"
            )

            # Generate the final document content
            generated_content = await self.generate_document_content(review_data)

            if not generated_content:
                return {"error": "Failed to generate document content"}

            # Apply any reviewer modifications
            if review_data.get("modifications"):
                generated_content = self.apply_modifications(
                    generated_content, review_data["modifications"]
                )

            # Save to S3 for backup/versioning
            s3_key = await self.save_to_s3(review_data, generated_content)

            # Update the document in its source system
            update_result = await self.update_source_document(
                document_data, generated_content, review_data
            )

            # Update document version via API
            version_result = await self.update_document_version(
                document_data["id"], generated_content, review_data
            )

            # Mark review as published
            await self.mark_review_published(
                review_id,
                {
                    "s3_key": s3_key,
                    "source_update": update_result,
                    "version_update": version_result,
                },
            )

            logger.info(f"Successfully processed review {review_id}")

            return {
                "status": "success",
                "review_id": review_id,
                "document_id": document_data["id"],
                "s3_key": s3_key,
                "source_update": update_result,
                "version_update": version_result,
            }

        except Exception as e:
            logger.error(f"Error processing approved review: {e}", exc_info=True)
            return {"error": str(e)}

    async def generate_document_content(
        self, review_data: Dict[str, Any]
    ) -> Optional[str]:
        """
        Generate the final document content using AI based on the review context.
        """
        try:
            change_context = review_data.get("change_context", {})
            document = review_data["document"]
            ai_reasoning = review_data.get("ai_reasoning", "")

            # Build comprehensive prompt
            prompt = f"""
            Generate updated documentation based on this approved review:

            Document Information:
            - Title: {document['title']}
            - Type: {document['document_type']}
            - Current Path: {document['path']}

            Changes That Triggered This Update:
            - Repository: {change_context.get('repository', 'Unknown')}
            - Branch: {change_context.get('branch', 'main')}
            - Files Changed: {', '.join(change_context.get('files_changed', [])[:10])}

            Commit Details:
            {json.dumps(change_context.get('commits', []), indent=2)}

            AI Assessment:
            {ai_reasoning}

            Previous AI Analysis:
            {json.dumps(change_context.get('ai_assessment', {}), indent=2)}

            Requirements:
            1. Create comprehensive documentation that reflects the changes
            2. Use clear, professional language appropriate for the document type
            3. Include relevant code examples where applicable
            4. Maintain consistent formatting with existing documentation standards
            5. Ensure the content is immediately usable without further editing

            For API documentation: Include endpoints, parameters, responses, and examples
            For user guides: Provide step-by-step instructions with context
            For README files: Focus on getting started, installation, and key features
            For changelogs: List changes in a structured, chronological format

            Generate the complete document content in Markdown format:
            """

            response = bedrock.invoke_model(
                modelId=CLAUDE_MODEL_ID,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(
                    {
                        "prompt": f"\n\nHuman: {prompt}\n\nAssistant:",
                        "max_tokens_to_sample": 4000,
                        "temperature": 0.3,
                        "top_p": 0.9,
                    }
                ),
            )

            result = json.loads(response["body"].read())
            return result["completion"].strip()

        except Exception as e:
            logger.error(f"Error generating document content: {e}")
            return None

    def apply_modifications(self, content: str, modifications: Dict[str, Any]) -> str:
        """
        Apply reviewer modifications to the generated content.
        """
        try:
            # Handle different types of modifications
            if "replacements" in modifications:
                for replacement in modifications["replacements"]:
                    content = content.replace(replacement["old"], replacement["new"])

            if "additions" in modifications:
                for addition in modifications["additions"]:
                    position = addition.get("position", "end")
                    text = addition["text"]

                    if position == "start":
                        content = text + "\n\n" + content
                    elif position == "end":
                        content = content + "\n\n" + text
                    # Could add more sophisticated positioning logic here

            if "custom_content" in modifications:
                # If reviewer provided complete custom content, use that
                content = modifications["custom_content"]

            return content

        except Exception as e:
            logger.error(f"Error applying modifications: {e}")
            return content  # Return original content if modifications fail

    async def save_to_s3(self, review_data: Dict[str, Any], content: str) -> str:
        """
        Save the final document content to S3 for backup and versioning.
        """
        try:
            document_id = review_data["document"]["id"]
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            s3_key = f"final_documents/{document_id}/v{timestamp}.md"

            s3.put_object(
                Bucket=DOCUMENTS_BUCKET,
                Key=s3_key,
                Body=content.encode("utf-8"),
                ContentType="text/markdown",
                Metadata={
                    "review_id": review_data["id"],
                    "document_id": document_id,
                    "generated_at": datetime.utcnow().isoformat(),
                    "change_id": review_data["change_id"],
                    "approved_by": review_data.get("reviewer", {}).get(
                        "email", "unknown"
                    ),
                },
            )

            logger.info(f"Saved document to S3: {s3_key}")
            return s3_key

        except Exception as e:
            logger.error(f"Error saving to S3: {e}")
            raise

    async def update_source_document(
        self, document_data: Dict[str, Any], content: str, review_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update the document in its source system (GitHub, Confluence, etc.).
        """
        try:
            source_system = document_data["source_system"]

            if source_system not in self.integration_clients:
                return {"error": f"Unsupported source system: {source_system}"}

            client = self.integration_clients[source_system]

            result = await client.update_document(
                external_id=document_data["external_id"],
                path=document_data["path"],
                content=content,
                metadata={
                    "updated_by": "Kinexus AI",
                    "review_id": review_data["id"],
                    "change_id": review_data["change_id"],
                    "approved_by": review_data.get("reviewer", {}).get(
                        "email", "unknown"
                    ),
                },
            )

            return result

        except Exception as e:
            logger.error(f"Error updating source document: {e}")
            return {"error": str(e)}

    async def update_document_version(
        self, document_id: str, content: str, review_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new document version via the FastAPI service.
        """
        try:
            version_data = {
                "content": content,
                "content_format": "markdown",
                "change_summary": f"Updated via review {review_data['id']} for change {review_data['change_id']}",
                "ai_generated": True,
                "ai_model": CLAUDE_MODEL_ID,
                "ai_confidence": review_data.get("ai_confidence"),
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{FASTAPI_BASE_URL}/api/documents/{document_id}/versions",
                    headers={"Authorization": f"Bearer {SERVICE_TOKEN}"},
                    json=version_data,
                    timeout=30.0,
                )

                if response.status_code == 201:
                    return response.json()
                else:
                    logger.error(
                        f"Failed to create document version: {response.status_code} - {response.text}"
                    )
                    return {"error": "Failed to create document version"}

        except Exception as e:
            logger.error(f"Error updating document version: {e}")
            return {"error": str(e)}

    async def mark_review_published(self, review_id: str, publish_data: Dict[str, Any]):
        """
        Mark the review as published via the FastAPI service.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{FASTAPI_BASE_URL}/api/reviews/{review_id}/publish",
                    headers={"Authorization": f"Bearer {SERVICE_TOKEN}"},
                    json=publish_data,
                    timeout=30.0,
                )

                if response.status_code != 200:
                    logger.error(
                        f"Failed to mark review as published: {response.status_code}"
                    )

        except Exception as e:
            logger.error(f"Error marking review as published: {e}")


# Integration client classes (placeholder implementations)
class GitHubIntegration:
    """Handles GitHub document updates"""

    async def update_document(
        self, external_id: str, path: str, content: str, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update document in GitHub repository"""
        # TODO: Implement GitHub API integration
        logger.info(f"Would update GitHub document: {external_id} at {path}")
        return {"status": "success", "method": "github_api", "path": path}


class ConfluenceIntegration:
    """Handles Confluence document updates"""

    async def update_document(
        self, external_id: str, path: str, content: str, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update document in Confluence"""
        # TODO: Implement Confluence API integration
        logger.info(f"Would update Confluence document: {external_id}")
        return {"status": "success", "method": "confluence_api", "page_id": external_id}


class SharePointIntegration:
    """Handles SharePoint document updates"""

    async def update_document(
        self, external_id: str, path: str, content: str, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update document in SharePoint"""
        # TODO: Implement SharePoint API integration
        logger.info(f"Would update SharePoint document: {external_id} at {path}")
        return {"status": "success", "method": "sharepoint_api", "path": path}


async def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler entry point"""

    try:
        processor = DocumentProcessor()

        # Handle EventBridge events from review system
        if "detail-type" in event and event["detail-type"] == "ReviewApproved":
            review_data = event["detail"]
            logger.info(
                f"Processing approved review from EventBridge: {review_data.get('review_id')}"
            )

            result = await processor.process_approved_review(review_data)

            return {"statusCode": 200, "body": json.dumps(result)}

        # Handle direct invocation with review data
        elif "review_data" in event:
            result = await processor.process_approved_review(event["review_data"])

            return {"statusCode": 200, "body": json.dumps(result)}

        else:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid event format"}),
            }

    except Exception as e:
        logger.error(f"Error in document processor: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"}),
        }


# Async wrapper for Lambda
def lambda_handler_sync(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Synchronous wrapper for the async Lambda handler"""
    import asyncio

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(lambda_handler(event, context))
