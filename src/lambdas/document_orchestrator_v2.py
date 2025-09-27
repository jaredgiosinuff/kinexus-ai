"""
Document Orchestrator Lambda V2
Handles both GitHub and Jira changes with appropriate strategies

DOCUMENTATION STRATEGY:
- GitHub changes: Update technical docs (README, API docs, code comments)
- Jira tickets: Update feature docs, release notes, user guides
- Combined: Cross-reference for complete picture
"""
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
import boto3
from botocore.config import Config
import structlog

logger = structlog.get_logger()

# AWS Clients
config = Config(region_name='us-east-1', retries={'max_attempts': 3, 'mode': 'adaptive'})
dynamodb = boto3.resource('dynamodb', config=config)
s3 = boto3.client('s3', config=config)
bedrock = boto3.client('bedrock-runtime', config=config)
eventbridge = boto3.client('events', config=config)

# Environment variables
CHANGES_TABLE = os.environ.get('CHANGES_TABLE', 'kinexus-changes')
DOCUMENTS_TABLE = os.environ.get('DOCUMENTS_TABLE', 'kinexus-documents')
DOCUMENTS_BUCKET = os.environ.get('DOCUMENTS_BUCKET', 'kinexus-documents')
EVENT_BUS = os.environ.get('EVENT_BUS', 'kinexus-events')

# Documentation storage structure (where docs live)
DOCUMENTATION_STRUCTURE = {
    'github': {
        'README.md': 's3://kinexus-documents/repos/{repo_name}/README.md',
        'API.md': 's3://kinexus-documents/repos/{repo_name}/docs/API.md',
        'CHANGELOG.md': 's3://kinexus-documents/repos/{repo_name}/CHANGELOG.md',
    },
    'jira': {
        'release_notes': 's3://kinexus-documents/releases/{version}/RELEASE_NOTES.md',
        'feature_docs': 's3://kinexus-documents/features/{issue_key}.md',
        'user_guides': 's3://kinexus-documents/guides/{component}/{issue_key}.md',
    },
    'combined': {
        'system_docs': 's3://kinexus-documents/system/{component}/README.md',
        'api_reference': 's3://kinexus-documents/api/v{version}/reference.md',
    }
}

# Model to use
CLAUDE_MODEL_ID = 'anthropic.claude-3-opus-20240229'


class EnhancedDocumentOrchestrator:
    """Enhanced orchestrator that handles multiple change sources"""

    def __init__(self):
        self.changes_table = dynamodb.Table(CHANGES_TABLE)
        self.documents_table = dynamodb.Table(DOCUMENTS_TABLE)

    async def process_change(self, change_id: str) -> Dict[str, Any]:
        """Process a change from any source"""

        # Get change details
        change = self.changes_table.get_item(Key={'change_id': change_id})
        if 'Item' not in change:
            logger.error(f"Change not found: {change_id}")
            return {'error': 'Change not found'}

        change_data = change['Item']
        source = change_data.get('source')

        logger.info(f"Processing {source} change", change_id=change_id)

        # Route to appropriate handler
        if source == 'github':
            result = await self.process_github_change(change_data)
        elif source == 'jira':
            result = await self.process_jira_change(change_data)
        else:
            result = {'error': f'Unknown source: {source}'}

        # Update change status
        self.changes_table.update_item(
            Key={'change_id': change_id},
            UpdateExpression='SET #status = :status, processed = :processed, processed_at = :timestamp',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': 'completed' if 'error' not in result else 'error',
                ':processed': True,
                ':timestamp': datetime.utcnow().isoformat()
            }
        )

        return result

    async def process_github_change(self, change_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process GitHub changes - focus on technical documentation"""

        github_data = change_data.get('change_data', {})
        repository = github_data.get('repository_name', 'unknown')
        files_changed = github_data.get('files_changed', [])
        commits = github_data.get('commits', [])

        # Determine what documentation to update
        docs_to_update = []

        # Check what changed
        has_api_changes = any('.py' in f or '.js' in f or '.ts' in f for f in files_changed)
        has_readme_change = any('README' in f.upper() for f in files_changed)
        has_config_change = any('config' in f.lower() or '.env' in f or '.yml' in f for f in files_changed)

        if has_api_changes:
            docs_to_update.append('api_documentation')
        if has_readme_change:
            docs_to_update.append('readme_update')
        if has_config_change:
            docs_to_update.append('configuration_guide')

        # Always update changelog
        docs_to_update.append('changelog')

        results = []
        for doc_type in docs_to_update:
            result = await self.generate_github_documentation(
                repository, files_changed, commits, doc_type
            )
            results.append(result)

        return {'github_docs_updated': results}

    async def process_jira_change(self, change_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Jira changes - focus on user-facing documentation"""

        jira_context = change_data.get('change_data', {}).get('documentation_context', {})
        issue_key = jira_context.get('issue_key')
        doc_type = jira_context.get('documentation_type', 'general')

        # Generate appropriate documentation based on ticket type
        if doc_type == 'api':
            result = await self.generate_api_documentation_from_jira(jira_context)
        elif doc_type == 'feature':
            result = await self.generate_feature_documentation(jira_context)
        elif doc_type == 'breaking-change':
            result = await self.generate_migration_guide(jira_context)
        else:
            result = await self.generate_release_notes_entry(jira_context)

        # Cross-reference with recent GitHub changes if available
        related_code_changes = await self.find_related_code_changes(jira_context)
        if related_code_changes:
            result['related_code_changes'] = related_code_changes

        return result

    async def generate_github_documentation(
        self, repository: str, files_changed: List[str],
        commits: List[Dict], doc_type: str
    ) -> Dict[str, Any]:
        """Generate technical documentation from GitHub changes"""

        prompt = self._build_github_prompt(repository, files_changed, commits, doc_type)

        try:
            response = bedrock.invoke_model(
                modelId=CLAUDE_MODEL_ID,
                contentType='application/json',
                accept='application/json',
                body=json.dumps({
                    'prompt': f"\n\nHuman: {prompt}\n\nAssistant:",
                    'max_tokens_to_sample': 3000,
                    'temperature': 0.3,
                    'top_p': 0.9
                })
            )

            generated_content = json.loads(response['body'].read())['completion']

            # Determine S3 location based on doc type
            s3_key = self._get_s3_key(repository, doc_type, source='github')

            # Store in S3
            s3.put_object(
                Bucket=DOCUMENTS_BUCKET,
                Key=s3_key,
                Body=generated_content.encode('utf-8'),
                ContentType='text/markdown',
                Metadata={
                    'repository': repository,
                    'doc_type': doc_type,
                    'generated_at': datetime.utcnow().isoformat(),
                    'source': 'github'
                }
            )

            # Store metadata in DynamoDB
            document_id = f"github_{repository}_{doc_type}_{datetime.utcnow().timestamp()}"
            self.documents_table.put_item(
                Item={
                    'document_id': document_id,
                    'title': f"{repository} - {doc_type}",
                    's3_key': s3_key,
                    'source': 'github',
                    'repository': repository,
                    'doc_type': doc_type,
                    'created_at': datetime.utcnow().isoformat(),
                    'status': 'generated',
                    'content_preview': generated_content[:500]
                }
            )

            logger.info(f"GitHub documentation created",
                       repository=repository,
                       doc_type=doc_type,
                       s3_key=s3_key)

            return {
                'document_id': document_id,
                's3_key': s3_key,
                'doc_type': doc_type
            }

        except Exception as e:
            logger.error(f"Error generating GitHub docs: {str(e)}")
            return {'error': str(e)}

    async def generate_feature_documentation(self, jira_context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate feature documentation from Jira ticket"""

        prompt = f"""
        Generate comprehensive feature documentation based on this completed Jira ticket:

        Ticket: {jira_context['issue_key']}
        Summary: {jira_context['summary']}
        Type: {jira_context['issue_type']}
        Description: {jira_context.get('description', 'N/A')}
        Acceptance Criteria: {jira_context.get('acceptance_criteria', 'N/A')}
        Components: {', '.join(jira_context.get('components', []))}

        Create documentation that includes:
        1. Feature Overview
        2. Use Cases
        3. Configuration (if applicable)
        4. API Changes (if applicable)
        5. Examples
        6. Migration Notes (if breaking changes)

        Format as Markdown suitable for a user guide.
        """

        try:
            response = bedrock.invoke_model(
                modelId=CLAUDE_MODEL_ID,
                contentType='application/json',
                accept='application/json',
                body=json.dumps({
                    'prompt': f"\n\nHuman: {prompt}\n\nAssistant:",
                    'max_tokens_to_sample': 4000,
                    'temperature': 0.5,
                })
            )

            generated_content = json.loads(response['body'].read())['completion']

            # Store in S3
            s3_key = f"features/{jira_context['issue_key']}.md"
            s3.put_object(
                Bucket=DOCUMENTS_BUCKET,
                Key=s3_key,
                Body=generated_content.encode('utf-8'),
                ContentType='text/markdown',
                Metadata={
                    'issue_key': jira_context['issue_key'],
                    'generated_at': datetime.utcnow().isoformat(),
                    'source': 'jira'
                }
            )

            # Store metadata
            document_id = f"jira_{jira_context['issue_key']}_{datetime.utcnow().timestamp()}"
            self.documents_table.put_item(
                Item={
                    'document_id': document_id,
                    'title': f"Feature: {jira_context['summary']}",
                    's3_key': s3_key,
                    'source': 'jira',
                    'issue_key': jira_context['issue_key'],
                    'created_at': datetime.utcnow().isoformat(),
                    'status': 'generated',
                    'content_preview': generated_content[:500]
                }
            )

            return {
                'document_id': document_id,
                's3_key': s3_key,
                'doc_type': 'feature'
            }

        except Exception as e:
            logger.error(f"Error generating feature docs: {str(e)}")
            return {'error': str(e)}

    async def find_related_code_changes(self, jira_context: Dict[str, Any]) -> List[Dict]:
        """Find GitHub changes related to this Jira ticket"""

        issue_key = jira_context['issue_key']

        # Query recent GitHub changes mentioning this ticket
        response = self.changes_table.scan(
            FilterExpression='#source = :source AND contains(#data, :issue_key)',
            ExpressionAttributeNames={
                '#source': 'source',
                '#data': 'raw_event'
            },
            ExpressionAttributeValues={
                ':source': 'github',
                ':issue_key': issue_key
            },
            Limit=10
        )

        related_changes = []
        for item in response.get('Items', []):
            commits = item.get('change_data', {}).get('commits', [])
            for commit in commits:
                if issue_key in commit.get('message', ''):
                    related_changes.append({
                        'commit_id': commit['id'],
                        'message': commit['message'],
                        'repository': item.get('change_data', {}).get('repository_name')
                    })

        return related_changes

    def _build_github_prompt(self, repository: str, files: List[str],
                            commits: List[Dict], doc_type: str) -> str:
        """Build prompt for GitHub documentation generation"""

        commit_messages = [c.get('message', '') for c in commits[:5]]

        if doc_type == 'api_documentation':
            return f"""
            Generate API documentation for these code changes:
            Repository: {repository}
            Files changed: {', '.join(files[:10])}
            Commits: {' | '.join(commit_messages)}

            Include: endpoints, parameters, responses, examples
            Format: OpenAPI/Swagger compatible Markdown
            """
        elif doc_type == 'changelog':
            return f"""
            Generate a CHANGELOG entry for these changes:
            Repository: {repository}
            Files: {', '.join(files[:10])}
            Commits: {' | '.join(commit_messages)}

            Format: Keep a Changelog format (Added, Changed, Deprecated, Removed, Fixed, Security)
            """
        else:
            return f"""
            Update README documentation based on:
            Repository: {repository}
            Changes: {', '.join(files[:10])}
            Commits: {' | '.join(commit_messages)}

            Focus on: setup instructions, configuration, usage examples
            """

    def _get_s3_key(self, identifier: str, doc_type: str, source: str) -> str:
        """Generate S3 key for document storage"""

        if source == 'github':
            repo_name = identifier.replace('/', '_')
            if doc_type == 'api_documentation':
                return f"repos/{repo_name}/docs/API.md"
            elif doc_type == 'changelog':
                return f"repos/{repo_name}/CHANGELOG.md"
            else:
                return f"repos/{repo_name}/README.md"
        elif source == 'jira':
            return f"jira/{doc_type}/{identifier}.md"
        else:
            return f"documents/{source}/{identifier}_{doc_type}.md"


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler entry point"""

    try:
        # Handle EventBridge events from both GitHub and Jira
        if 'detail-type' in event and event['detail-type'] == 'ChangeDetected':
            detail = event['detail']
            change_id = detail['change_id']

            logger.info(f"Processing change from EventBridge", change_id=change_id)

            orchestrator = EnhancedDocumentOrchestrator()
            import asyncio
            result = asyncio.run(orchestrator.process_change(change_id))

            return {
                'statusCode': 200,
                'body': json.dumps(result)
            }

        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid event format'})
            }

    except Exception as e:
        logger.error(f"Error in orchestrator: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }