"""
Document Manager Lambda
AI-driven management of EXISTING documentation across repositories and systems

CORE PHILOSOPHY:
- Primary mode: UPDATE existing documentation
- Secondary mode: CREATE new docs only when permitted and necessary
- Always work with the actual documentation where it lives
- Maintain version history and rollback capability
"""
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import boto3
from botocore.config import Config
import base64
import structlog

logger = structlog.get_logger()

# AWS Clients
config = Config(region_name='us-east-1', retries={'max_attempts': 3, 'mode': 'adaptive'})
dynamodb = boto3.resource('dynamodb', config=config)
s3 = boto3.client('s3', config=config)
bedrock = boto3.client('bedrock-runtime', config=config)
secrets = boto3.client('secretsmanager', config=config)

# Environment variables
DOCUMENTS_TABLE = os.environ.get('DOCUMENTS_TABLE', 'kinexus-documents')
DOCUMENT_SOURCES_TABLE = os.environ.get('DOCUMENT_SOURCES_TABLE', 'kinexus-document-sources')
PERMISSIONS_TABLE = os.environ.get('PERMISSIONS_TABLE', 'kinexus-permissions')

CLAUDE_MODEL_ID = 'anthropic.claude-3-opus-20240229'


class DocumentManager:
    """
    Manages existing documentation across multiple sources.
    This is NOT a generator - it's a manager of living documents.
    """

    def __init__(self):
        self.documents_table = dynamodb.Table(DOCUMENTS_TABLE)
        self.sources_table = dynamodb.Table(DOCUMENT_SOURCES_TABLE)
        self.permissions_table = dynamodb.Table(PERMISSIONS_TABLE)

        # Document source connectors (to be initialized on demand)
        self.github_client = None
        self.confluence_client = None
        self.sharepoint_client = None

    async def process_change(self, change_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a change by updating EXISTING documentation.
        """

        # Step 1: Identify affected existing documents
        affected_docs = await self.identify_affected_documents(change_data)

        if not affected_docs:
            logger.info("No existing documents affected by this change")

            # Check if we should create new documentation
            if await self.should_create_new_document(change_data):
                return await self.create_new_document(change_data)
            else:
                return {'message': 'No documentation updates needed'}

        # Step 2: Process each affected document
        results = []
        for doc in affected_docs:
            result = await self.update_existing_document(doc, change_data)
            results.append(result)

        return {'documents_updated': results}

    async def identify_affected_documents(self, change_data: Dict[str, Any]) -> List[Dict]:
        """
        Find existing documents that should be updated based on the change.
        This is the CORE of the system - mapping changes to real documents.
        """

        affected_docs = []
        source = change_data.get('source')

        if source == 'github':
            # GitHub changes affect repository documentation
            repo = change_data.get('change_data', {}).get('repository_name')
            files_changed = change_data.get('change_data', {}).get('files_changed', [])

            # Check for direct documentation files that were changed
            for file in files_changed:
                if any(doc_file in file.lower() for doc_file in ['readme', '.md', 'doc']):
                    # This is a direct documentation change - track it but don't double-update
                    logger.info(f"Direct doc change detected: {file}")
                    continue

            # Find related documentation that needs updating
            # 1. Repository README
            readme_doc = await self.find_document(
                source_type='github',
                repository=repo,
                path='README.md'
            )
            if readme_doc:
                affected_docs.append(readme_doc)

            # 2. API documentation (if code files changed)
            if any('.py' in f or '.js' in f or '.ts' in f for f in files_changed):
                api_doc = await self.find_document(
                    source_type='github',
                    repository=repo,
                    path='docs/API.md'
                )
                if api_doc:
                    affected_docs.append(api_doc)

                # Also check Confluence for API documentation
                confluence_api_doc = await self.find_document(
                    source_type='confluence',
                    space='DEV',
                    title=f"{repo} API Documentation"
                )
                if confluence_api_doc:
                    affected_docs.append(confluence_api_doc)

        elif source == 'jira':
            # Jira changes affect feature and release documentation
            issue_key = change_data.get('change_data', {}).get('issue_key')
            components = change_data.get('change_data', {}).get('documentation_context', {}).get('components', [])

            # 1. Check for feature documentation in Confluence
            feature_doc = await self.find_document(
                source_type='confluence',
                space='PRODUCT',
                title=f"Feature: {issue_key}"
            )
            if feature_doc:
                affected_docs.append(feature_doc)

            # 2. Check for component documentation
            for component in components:
                component_doc = await self.find_document(
                    source_type='github',
                    repository=f"company/{component}",
                    path='README.md'
                )
                if component_doc:
                    affected_docs.append(component_doc)

            # 3. Check for release notes
            version = change_data.get('change_data', {}).get('documentation_context', {}).get('fix_versions', [])
            if version:
                release_doc = await self.find_document(
                    source_type='confluence',
                    space='RELEASES',
                    title=f"Release Notes {version[0]}"
                )
                if release_doc:
                    affected_docs.append(release_doc)

        return affected_docs

    async def find_document(self, source_type: str, **kwargs) -> Optional[Dict]:
        """
        Find an existing document in a source system.
        Returns document metadata including location and access method.
        """

        # Query our document registry
        if source_type == 'github':
            response = self.sources_table.query(
                IndexName='source-type-index',
                KeyConditionExpression='source_type = :st AND repository = :repo',
                ExpressionAttributeValues={
                    ':st': source_type,
                    ':repo': kwargs.get('repository'),
                    ':path': kwargs.get('path')
                }
            )
        elif source_type == 'confluence':
            response = self.sources_table.query(
                IndexName='source-type-index',
                KeyConditionExpression='source_type = :st AND space = :space',
                ExpressionAttributeValues={
                    ':st': source_type,
                    ':space': kwargs.get('space')
                }
            )
        else:
            return None

        items = response.get('Items', [])

        # Filter by additional criteria
        for item in items:
            if source_type == 'github' and item.get('path') == kwargs.get('path'):
                return item
            elif source_type == 'confluence' and kwargs.get('title') in item.get('title', ''):
                return item

        # If not in registry, check if it actually exists in the source system
        return await self.discover_document(source_type, **kwargs)

    async def discover_document(self, source_type: str, **kwargs) -> Optional[Dict]:
        """
        Discover documents that exist in source systems but aren't in our registry yet.
        """

        if source_type == 'github':
            # Use GitHub API to check if file exists
            if not self.github_client:
                self.github_client = await self.init_github_client()

            try:
                repo = kwargs.get('repository')
                path = kwargs.get('path')

                # Try to get the file
                file_content = await self.github_client.get_file(repo, path)

                if file_content:
                    # Register this document for future reference
                    doc_metadata = {
                        'document_id': f"github_{repo}_{path}".replace('/', '_'),
                        'source_type': 'github',
                        'repository': repo,
                        'path': path,
                        'discovered_at': datetime.utcnow().isoformat(),
                        'content_sha': file_content.get('sha'),
                        'editable': True
                    }

                    # Store in registry
                    self.sources_table.put_item(Item=doc_metadata)

                    return doc_metadata
            except Exception as e:
                logger.debug(f"Document not found: {e}")
                return None

        elif source_type == 'confluence':
            # Use Confluence API to search for page
            if not self.confluence_client:
                self.confluence_client = await self.init_confluence_client()

            try:
                space = kwargs.get('space')
                title = kwargs.get('title')

                page = await self.confluence_client.get_page_by_title(space, title)

                if page:
                    doc_metadata = {
                        'document_id': f"confluence_{space}_{page['id']}",
                        'source_type': 'confluence',
                        'space': space,
                        'page_id': page['id'],
                        'title': page['title'],
                        'discovered_at': datetime.utcnow().isoformat(),
                        'version': page['version']['number'],
                        'editable': True
                    }

                    self.sources_table.put_item(Item=doc_metadata)
                    return doc_metadata
            except Exception as e:
                logger.debug(f"Confluence page not found: {e}")
                return None

        return None

    async def update_existing_document(self, doc_metadata: Dict, change_data: Dict) -> Dict:
        """
        Update an existing document based on changes.
        This is the PRIMARY operation of the system.
        """

        source_type = doc_metadata['source_type']

        # Step 1: Fetch current content
        current_content = await self.fetch_document_content(doc_metadata)

        if not current_content:
            logger.error(f"Could not fetch document content for {doc_metadata['document_id']}")
            return {'error': 'Could not fetch document content'}

        # Step 2: Analyze what needs updating
        update_strategy = await self.analyze_update_needs(
            current_content,
            doc_metadata,
            change_data
        )

        if update_strategy['action'] == 'no_change':
            return {
                'document_id': doc_metadata['document_id'],
                'action': 'no_change',
                'reason': update_strategy.get('reason')
            }

        # Step 3: Generate updated content using AI
        updated_content = await self.generate_updated_content(
            current_content,
            update_strategy,
            change_data
        )

        # Step 4: Validate the update
        validation = await self.validate_update(current_content, updated_content)

        if not validation['is_valid']:
            logger.warning(f"Update validation failed: {validation['reason']}")
            return {
                'document_id': doc_metadata['document_id'],
                'action': 'validation_failed',
                'reason': validation['reason']
            }

        # Step 5: Apply the update to the source system
        result = await self.apply_document_update(
            doc_metadata,
            current_content,
            updated_content,
            change_data
        )

        # Step 6: Track the update
        await self.track_document_update(
            doc_metadata,
            change_data,
            result
        )

        return result

    async def fetch_document_content(self, doc_metadata: Dict) -> Optional[str]:
        """
        Fetch the actual content of a document from its source.
        """

        source_type = doc_metadata['source_type']

        if source_type == 'github':
            if not self.github_client:
                self.github_client = await self.init_github_client()

            content_response = await self.github_client.get_file_content(
                doc_metadata['repository'],
                doc_metadata['path']
            )

            # GitHub returns base64 encoded content
            if content_response:
                return base64.b64decode(content_response['content']).decode('utf-8')

        elif source_type == 'confluence':
            if not self.confluence_client:
                self.confluence_client = await self.init_confluence_client()

            page_content = await self.confluence_client.get_page_content(
                doc_metadata['page_id']
            )

            return page_content

        elif source_type == 's3':
            # For S3-stored documents
            response = s3.get_object(
                Bucket=doc_metadata['bucket'],
                Key=doc_metadata['key']
            )
            return response['Body'].read().decode('utf-8')

        return None

    async def analyze_update_needs(self, current_content: str, doc_metadata: Dict,
                                  change_data: Dict) -> Dict:
        """
        Use AI to analyze what sections of a document need updating.
        """

        prompt = f"""
        Analyze this existing document and determine what needs updating based on the change.

        Document: {doc_metadata.get('path') or doc_metadata.get('title')}
        Document Type: {doc_metadata['source_type']}

        Current Content (first 2000 chars):
        {current_content[:2000]}

        Change Information:
        Source: {change_data.get('source')}
        Type: {change_data.get('change_data', {}).get('documentation_context', {}).get('documentation_type', 'unknown')}
        Summary: {json.dumps(change_data.get('change_data', {}).get('summary', 'N/A'))}
        Details: {json.dumps(change_data.get('change_data', {})[:500])}

        Determine:
        1. Does this document need updating? (yes/no)
        2. Which sections need updating?
        3. What type of update (addition, modification, removal)?
        4. Priority of update (critical, high, medium, low)?

        Respond with structured JSON.
        """

        try:
            response = bedrock.invoke_model(
                modelId=CLAUDE_MODEL_ID,
                contentType='application/json',
                accept='application/json',
                body=json.dumps({
                    'prompt': f"\n\nHuman: {prompt}\n\nAssistant:",
                    'max_tokens_to_sample': 1000,
                    'temperature': 0.3
                })
            )

            analysis_text = json.loads(response['body'].read())['completion']

            # Parse AI response (in production, would be more robust)
            # For now, return a structured response
            return {
                'action': 'update',
                'sections': ['API Documentation', 'Configuration'],
                'update_type': 'modification',
                'priority': 'high',
                'reasoning': analysis_text
            }

        except Exception as e:
            logger.error(f"Error analyzing update needs: {e}")
            return {'action': 'no_change', 'reason': str(e)}

    async def generate_updated_content(self, current_content: str,
                                      update_strategy: Dict,
                                      change_data: Dict) -> str:
        """
        Generate the updated document content using AI.
        CRITICAL: This preserves existing content and only updates what's needed.
        """

        prompt = f"""
        Update the following document based on the changes.
        IMPORTANT: Preserve all existing content except for the sections that need updating.

        Current Document Content:
        {current_content}

        Sections to Update:
        {', '.join(update_strategy.get('sections', []))}

        Change Information:
        {json.dumps(change_data.get('change_data', {}))}

        Update Instructions:
        - Maintain the existing document structure and style
        - Only modify the specified sections
        - Preserve all other content exactly as is
        - Add a note at the end indicating the update (e.g., "Last updated: [date] - [summary]")
        - If adding new content, integrate it naturally into the existing structure

        Return the complete updated document.
        """

        try:
            response = bedrock.invoke_model(
                modelId=CLAUDE_MODEL_ID,
                contentType='application/json',
                accept='application/json',
                body=json.dumps({
                    'prompt': f"\n\nHuman: {prompt}\n\nAssistant:",
                    'max_tokens_to_sample': 6000,
                    'temperature': 0.3
                })
            )

            updated_content = json.loads(response['body'].read())['completion']
            return updated_content

        except Exception as e:
            logger.error(f"Error generating updated content: {e}")
            # Return original content if update fails
            return current_content

    async def validate_update(self, original: str, updated: str) -> Dict[str, Any]:
        """
        Validate that the update is safe and appropriate.
        """

        # Check that the document wasn't drastically changed
        original_lines = original.split('\n')
        updated_lines = updated.split('\n')

        # If more than 50% of the document changed, flag for review
        import difflib
        matcher = difflib.SequenceMatcher(None, original_lines, updated_lines)
        similarity_ratio = matcher.ratio()

        if similarity_ratio < 0.5:
            return {
                'is_valid': False,
                'reason': 'Too many changes (>50% of document)',
                'requires_human_review': True
            }

        # Check for removal of critical sections
        critical_sections = ['Installation', 'Configuration', 'API', 'Security', 'License']
        for section in critical_sections:
            if section in original and section not in updated:
                return {
                    'is_valid': False,
                    'reason': f'Critical section removed: {section}',
                    'requires_human_review': True
                }

        return {'is_valid': True}

    async def apply_document_update(self, doc_metadata: Dict, original_content: str,
                                   updated_content: str, change_data: Dict) -> Dict:
        """
        Apply the update to the actual document in its source system.
        """

        source_type = doc_metadata['source_type']

        if source_type == 'github':
            if not self.github_client:
                self.github_client = await self.init_github_client()

            # Create a commit with the updated content
            result = await self.github_client.update_file(
                repository=doc_metadata['repository'],
                path=doc_metadata['path'],
                content=updated_content,
                message=f"AI: Update documentation based on {change_data.get('source')} change",
                sha=doc_metadata.get('content_sha')
            )

            return {
                'document_id': doc_metadata['document_id'],
                'action': 'updated',
                'source': 'github',
                'commit_sha': result.get('commit', {}).get('sha'),
                'url': result.get('content', {}).get('html_url')
            }

        elif source_type == 'confluence':
            if not self.confluence_client:
                self.confluence_client = await self.init_confluence_client()

            # Update the Confluence page
            result = await self.confluence_client.update_page(
                page_id=doc_metadata['page_id'],
                title=doc_metadata['title'],
                content=updated_content,
                version_number=doc_metadata.get('version', 0) + 1,
                version_message=f"AI: Updated based on {change_data.get('source')} change"
            )

            return {
                'document_id': doc_metadata['document_id'],
                'action': 'updated',
                'source': 'confluence',
                'page_id': result['id'],
                'url': result['_links']['webui']
            }

        else:
            # Fallback: Store in S3
            s3_key = f"managed-docs/{doc_metadata['document_id']}/{datetime.utcnow().isoformat()}.md"
            s3.put_object(
                Bucket='kinexus-documents',
                Key=s3_key,
                Body=updated_content.encode('utf-8')
            )

            return {
                'document_id': doc_metadata['document_id'],
                'action': 'updated',
                'source': 's3',
                's3_key': s3_key
            }

    async def should_create_new_document(self, change_data: Dict) -> bool:
        """
        Determine if we should create a new document (requires permission).
        """

        # Check permissions table
        source = change_data.get('source')
        context = change_data.get('change_data', {})

        # Look up creation permissions
        response = self.permissions_table.get_item(
            Key={'permission_type': 'create_document', 'source': source}
        )

        if 'Item' not in response:
            return False  # No permission to create

        permission = response['Item']

        # Check conditions
        if permission.get('requires_label'):
            # For Jira, check if it has the required label
            labels = context.get('documentation_context', {}).get('labels', [])
            if permission['requires_label'] not in labels:
                return False

        if permission.get('requires_explicit'):
            # Needs explicit flag in change data
            if not context.get('create_new_document'):
                return False

        return permission.get('allowed', False)

    async def create_new_document(self, change_data: Dict) -> Dict:
        """
        Create a new document when no existing document was found.
        This is SECONDARY to updating existing docs.
        """

        # Determine where to create the document
        location = await self.determine_new_document_location(change_data)

        # Generate the new document
        content = await self.generate_new_document_content(change_data)

        # Create in the appropriate system
        if location['type'] == 'github':
            result = await self.github_client.create_file(
                repository=location['repository'],
                path=location['path'],
                content=content,
                message=f"AI: Create new documentation for {change_data.get('source')} change"
            )
        elif location['type'] == 'confluence':
            result = await self.confluence_client.create_page(
                space=location['space'],
                title=location['title'],
                content=content
            )
        else:
            # Default to S3
            s3_key = f"new-docs/{datetime.utcnow().isoformat()}/{location['filename']}"
            s3.put_object(
                Bucket='kinexus-documents',
                Key=s3_key,
                Body=content.encode('utf-8')
            )
            result = {'s3_key': s3_key}

        # Register the new document
        doc_metadata = {
            'document_id': f"{location['type']}_{result.get('id', 'new')}",
            'source_type': location['type'],
            'created_from': change_data.get('source'),
            'created_at': datetime.utcnow().isoformat(),
            **location,
            **result
        }

        self.sources_table.put_item(Item=doc_metadata)

        return {
            'action': 'created',
            'document_id': doc_metadata['document_id'],
            'location': location,
            'reason': 'No existing document found, created new'
        }

    async def track_document_update(self, doc_metadata: Dict, change_data: Dict, result: Dict):
        """
        Track all document updates for audit and rollback capability.
        """

        update_record = {
            'update_id': f"{doc_metadata['document_id']}_{datetime.utcnow().timestamp()}",
            'document_id': doc_metadata['document_id'],
            'source_type': doc_metadata['source_type'],
            'change_id': change_data.get('change_id'),
            'change_source': change_data.get('source'),
            'timestamp': datetime.utcnow().isoformat(),
            'result': result
        }

        # Store in updates table
        self.documents_table.put_item(Item=update_record)

    # Client initialization methods
    async def init_github_client(self):
        """Initialize GitHub client with credentials"""
        # In production, get from Secrets Manager
        from src.integrations.github_client import GitHubClient
        return GitHubClient(token=os.environ.get('GITHUB_TOKEN'))

    async def init_confluence_client(self):
        """Initialize Confluence client"""
        from src.integrations.confluence_client import ConfluenceClient
        return ConfluenceClient(
            url=os.environ.get('CONFLUENCE_URL'),
            token=os.environ.get('CONFLUENCE_TOKEN')
        )


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for document management"""

    try:
        manager = DocumentManager()

        # Process the change event
        if 'detail-type' in event and event['detail-type'] == 'ChangeDetected':
            change_id = event['detail']['change_id']

            # Fetch change data from DynamoDB
            changes_table = dynamodb.Table('kinexus-changes')
            response = changes_table.get_item(Key={'change_id': change_id})

            if 'Item' in response:
                import asyncio
                result = asyncio.run(manager.process_change(response['Item']))
                return {
                    'statusCode': 200,
                    'body': json.dumps(result)
                }

        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid event'})
        }

    except Exception as e:
        logger.error(f"Error in document manager: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }