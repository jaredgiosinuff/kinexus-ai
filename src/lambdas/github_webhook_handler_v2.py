"""
GitHub Webhook Handler Lambda V2
Updated to integrate with Kinexus AI review workflow system.

This version:
1. Maintains backward compatibility with existing webhook handling
2. Calls the FastAPI review service to create reviews
3. Uses AI to assess change impact and generate documentation updates
4. Triggers real-time notifications via WebSocket
"""

import json
import os
import hashlib
import hmac
import httpx
from datetime import datetime
from typing import Dict, Any, List, Optional
import boto3
import structlog

logger = structlog.get_logger()

# AWS Clients
dynamodb = boto3.resource('dynamodb')
eventbridge = boto3.client('events')
secrets = boto3.client('secretsmanager')
bedrock = boto3.client('bedrock-runtime')

# Environment variables
CHANGES_TABLE = os.environ.get('CHANGES_TABLE', 'kinexus-changes')
EVENT_BUS = os.environ.get('EVENT_BUS', 'kinexus-events')
GITHUB_SECRET_ARN = os.environ.get('GITHUB_SECRET_ARN')
FASTAPI_BASE_URL = os.environ.get('FASTAPI_BASE_URL', 'http://localhost:8000')
SERVICE_TOKEN = os.environ.get('SERVICE_TOKEN')  # Service account JWT token


def verify_signature(payload: str, signature: str, secret: str) -> bool:
    """Verify GitHub webhook signature"""
    if not signature:
        return False

    sha_name, signature = signature.split('=')
    if sha_name != 'sha256':
        return False

    mac = hmac.new(secret.encode(), msg=payload.encode(), digestmod=hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), signature)


def extract_change_data(github_event: Dict[str, Any]) -> Dict[str, Any]:
    """Extract relevant data from GitHub webhook payload"""

    # Handle push events
    if 'commits' in github_event:
        commits = github_event['commits']
        repository = github_event['repository']

        # Aggregate all changed files
        files_changed = set()
        for commit in commits:
            files_changed.update(commit.get('added', []))
            files_changed.update(commit.get('modified', []))
            files_changed.update(commit.get('removed', []))

        return {
            'repository_name': repository['full_name'],
            'repository_url': repository['html_url'],
            'branch': github_event.get('ref', '').replace('refs/heads/', ''),
            'commits': [
                {
                    'id': c['id'],
                    'message': c['message'],
                    'author': c['author']['name'],
                    'timestamp': c['timestamp']
                }
                for c in commits
            ],
            'files_changed': list(files_changed),
            'pusher': github_event.get('pusher', {}).get('name'),
            'event_type': 'push'
        }

    # Handle pull request events
    elif 'pull_request' in github_event:
        pr = github_event['pull_request']
        return {
            'repository_name': github_event['repository']['full_name'],
            'repository_url': github_event['repository']['html_url'],
            'pull_request_number': pr['number'],
            'pull_request_title': pr['title'],
            'pull_request_body': pr.get('body', ''),
            'action': github_event.get('action'),
            'branch': pr['head']['ref'],
            'base_branch': pr['base']['ref'],
            'event_type': 'pull_request'
        }

    return {}


def calculate_impact_score(change_data: Dict[str, Any]) -> int:
    """
    Calculate impact score (1-10) based on change characteristics.

    This is a heuristic-based assessment that can be enhanced with AI.
    """
    score = 1
    files_changed = change_data.get('files_changed', [])

    # File count impact
    if len(files_changed) > 20:
        score += 3
    elif len(files_changed) > 10:
        score += 2
    elif len(files_changed) > 5:
        score += 1

    # File type impact
    critical_files = ['readme', 'changelog', 'api', 'security', 'config']
    for file_path in files_changed:
        file_lower = file_path.lower()
        if any(critical in file_lower for critical in critical_files):
            score += 2
            break

    # Documentation files
    doc_extensions = ['.md', '.rst', '.txt', '.adoc']
    if any(file_path.lower().endswith(ext) for file_path in files_changed for ext in doc_extensions):
        score += 1

    # Branch impact
    if change_data.get('branch') in ['main', 'master', 'production']:
        score += 2

    return min(score, 10)


async def assess_documentation_impact(change_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Use AI to assess what documentation needs to be updated.

    Returns impact assessment and suggested documentation updates.
    """
    prompt = f"""
    Analyze this code change and determine what documentation might need updating:

    Repository: {change_data.get('repository_name')}
    Branch: {change_data.get('branch')}
    Files Changed: {change_data.get('files_changed', [])}

    Commits:
    {json.dumps(change_data.get('commits', []), indent=2)}

    Please assess:
    1. What types of documentation are likely affected?
    2. What specific sections or pages might need updates?
    3. What is the urgency/priority of these updates?
    4. Provide a brief reasoning for your assessment.

    Respond in JSON format with this structure:
    {{
        "affected_docs": ["api_reference", "user_guide", "changelog"],
        "priority": "high|medium|low",
        "reasoning": "explanation of why these docs need updating",
        "suggested_updates": "brief description of what updates are needed"
    }}
    """

    try:
        response = bedrock.invoke_model(
            modelId='anthropic.claude-3-opus-20240229',
            body=json.dumps({
                'prompt': prompt,
                'max_tokens': 1000,
                'temperature': 0.3
            })
        )

        response_body = json.loads(response['body'].read())
        ai_response = response_body['completion']

        # Extract JSON from AI response
        import re
        json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())

    except Exception as e:
        logger.error(f"Failed to get AI assessment: {e}")

    # Fallback assessment
    return {
        "affected_docs": ["general"],
        "priority": "medium",
        "reasoning": "Automatic assessment based on file changes",
        "suggested_updates": "Review changes and update relevant documentation"
    }


async def find_or_create_document(repository_name: str, doc_type: str) -> Optional[str]:
    """
    Find existing document or create a new document record.

    Returns document_id if successful.
    """
    try:
        async with httpx.AsyncClient() as client:
            # Search for existing document
            response = await client.get(
                f"{FASTAPI_BASE_URL}/api/documents",
                headers={"Authorization": f"Bearer {SERVICE_TOKEN}"},
                params={
                    "source_system": "github",
                    "external_id": f"{repository_name}_{doc_type}"
                }
            )

            if response.status_code == 200:
                documents = response.json()
                if documents:
                    return documents[0]['id']

            # Create new document
            document_data = {
                "external_id": f"{repository_name}_{doc_type}",
                "source_system": "github",
                "path": f"docs/{doc_type}.md",
                "title": f"{doc_type.replace('_', ' ').title()} - {repository_name}",
                "document_type": doc_type,
                "doc_metadata": {
                    "repository": repository_name,
                    "auto_managed": True
                }
            }

            response = await client.post(
                f"{FASTAPI_BASE_URL}/api/documents",
                headers={"Authorization": f"Bearer {SERVICE_TOKEN}"},
                json=document_data
            )

            if response.status_code == 201:
                return response.json()['id']

    except Exception as e:
        logger.error(f"Failed to find/create document: {e}")

    return None


async def create_review_via_api(
    document_id: str,
    change_id: str,
    impact_score: int,
    ai_assessment: Dict[str, Any],
    change_data: Dict[str, Any]
) -> bool:
    """
    Create a review via the FastAPI service.

    Returns True if successful.
    """
    try:
        review_data = {
            "document_id": document_id,
            "change_id": change_id,
            "proposed_version": 1,  # TODO: Get actual version
            "impact_score": impact_score,
            "ai_reasoning": ai_assessment.get("reasoning", ""),
            "ai_confidence": 75,  # TODO: Calculate actual confidence
            "ai_model": "claude-3-opus-20240229",
            "change_context": {
                "repository": change_data.get("repository_name"),
                "branch": change_data.get("branch"),
                "files_changed": change_data.get("files_changed", []),
                "commits": change_data.get("commits", []),
                "ai_assessment": ai_assessment
            },
            "priority": {
                "high": 8,
                "medium": 5,
                "low": 2
            }.get(ai_assessment.get("priority", "medium"), 5)
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{FASTAPI_BASE_URL}/api/reviews",
                headers={"Authorization": f"Bearer {SERVICE_TOKEN}"},
                json=review_data,
                timeout=30.0
            )

            if response.status_code == 201:
                review = response.json()
                logger.info(f"Created review {review['id']} for document {document_id}")
                return True
            else:
                logger.error(f"Failed to create review: {response.status_code} - {response.text}")

    except Exception as e:
        logger.error(f"Failed to create review via API: {e}")

    return False


async def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for GitHub webhooks with review integration"""

    try:
        # Parse the request
        body = event.get('body', '{}')
        headers = event.get('headers', {})

        # Verify GitHub signature if secret is configured
        if GITHUB_SECRET_ARN:
            secret_response = secrets.get_secret_value(SecretId=GITHUB_SECRET_ARN)
            github_secret = json.loads(secret_response['SecretString'])['webhook_secret']

            signature = headers.get('x-hub-signature-256')
            if not verify_signature(body, signature, github_secret):
                logger.warning("Invalid GitHub signature")
                return {
                    'statusCode': 401,
                    'body': json.dumps({'error': 'Invalid signature'})
                }

        # Parse GitHub event
        github_event = json.loads(body)
        github_event_type = headers.get('x-github-event', 'unknown')

        logger.info(f"Received GitHub event", event_type=github_event_type)

        # Extract change data
        change_data = extract_change_data(github_event)
        if not change_data:
            logger.info("No relevant change data found")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Event received but no action taken'})
            }

        # Create change record (backward compatibility)
        change_id = f"github_{change_data['repository_name']}_{datetime.utcnow().timestamp()}"
        change_record = {
            'change_id': change_id,
            'source': 'github',
            'source_event_type': github_event_type,
            'change_data': change_data,
            'raw_event': github_event,
            'created_at': datetime.utcnow().isoformat(),
            'status': 'processing',
            'processed': False
        }

        # Store in DynamoDB
        table = dynamodb.Table(CHANGES_TABLE)
        table.put_item(Item=change_record)

        # NEW: AI-powered review workflow
        if SERVICE_TOKEN:  # Only if FastAPI integration is configured
            try:
                # Calculate impact score
                impact_score = calculate_impact_score(change_data)

                # Get AI assessment
                ai_assessment = await assess_documentation_impact(change_data)

                # Process each affected document type
                reviews_created = []
                for doc_type in ai_assessment.get("affected_docs", ["general"]):
                    document_id = await find_or_create_document(
                        change_data['repository_name'],
                        doc_type
                    )

                    if document_id:
                        review_created = await create_review_via_api(
                            document_id,
                            change_id,
                            impact_score,
                            ai_assessment,
                            change_data
                        )

                        if review_created:
                            reviews_created.append(doc_type)

                # Update change record with review status
                change_record['reviews_created'] = reviews_created
                change_record['ai_assessment'] = ai_assessment
                change_record['impact_score'] = impact_score
                change_record['status'] = 'reviews_created' if reviews_created else 'no_reviews_needed'

                table.put_item(Item=change_record)

                logger.info(f"Created {len(reviews_created)} reviews for change {change_id}")

            except Exception as e:
                logger.error(f"Failed to create reviews: {e}")
                # Continue with legacy workflow

        # Send to EventBridge (legacy compatibility)
        eventbridge.put_events(
            Entries=[
                {
                    'Source': 'kinexus.github',
                    'DetailType': 'ChangeDetected',
                    'Detail': json.dumps({
                        'change_id': change_id,
                        'repository': change_data['repository_name'],
                        'files_changed': change_data.get('files_changed', []),
                        'event_type': github_event_type,
                        'reviews_created': change_record.get('reviews_created', [])
                    }),
                    'EventBusName': EVENT_BUS
                }
            ]
        )

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Change event processed with review workflow',
                'change_id': change_id,
                'reviews_created': change_record.get('reviews_created', []),
                'impact_score': change_record.get('impact_score'),
                'ai_assessment': change_record.get('ai_assessment')
            })
        }

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }


# Async wrapper for Lambda (since Lambda doesn't natively support async)
def lambda_handler_sync(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Synchronous wrapper for the async Lambda handler"""
    import asyncio

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(lambda_handler(event, context))