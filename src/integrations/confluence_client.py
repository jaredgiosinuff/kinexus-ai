"""
Confluence Client for Document Management
Manages documents that live in Confluence spaces
"""
import base64
import json
from typing import Dict, Any, Optional, List
import httpx
import structlog
from datetime import datetime

logger = structlog.get_logger()


class ConfluenceClient:
    """
    Client for managing documents in Confluence.
    This client UPDATES existing pages, not creates shadow copies.

    IMPORTANT (2025):
    - Uses Confluence Cloud REST API v2 (current as of October 2025)
    - API tokens now expire (1-365 days) - implement token refresh logic
    - Scoped API tokens: use https://api.atlassian.com/ex/confluence/{cloudId} for scoped tokens
    - For production: use OAuth 2.0 instead of basic auth per Atlassian security requirements
    """

    def __init__(self, base_url: str, username: str, api_token: str, cloud_id: str = None):
        self.base_url = base_url.rstrip('/')
        self.cloud_id = cloud_id
        self.auth = (username, api_token)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        # Use scoped API endpoint if cloud_id provided (2025 requirement)
        if cloud_id:
            self.api_base = f"https://api.atlassian.com/ex/confluence/{cloud_id}"
        else:
            self.api_base = f"{self.base_url}/wiki"

    async def get_page_by_id(self, page_id: str) -> Optional[Dict]:
        """
        Get page content and metadata by page ID.
        """
        url = f"{self.api_base}/rest/api/content/{page_id}"
        params = {
            "expand": "body.storage,version,ancestors,space"
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url,
                    auth=self.auth,
                    headers=self.headers,
                    params=params
                )
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    logger.debug(f"Page not found: {page_id}")
                    return None
                else:
                    logger.error(f"Error getting page: {response.status_code}")
                    return None
            except Exception as e:
                logger.error(f"Error fetching page: {e}")
                return None

    async def search_pages(self, cql: str, limit: int = 100) -> List[Dict]:
        """
        Search for pages using CQL (Confluence Query Language).
        Example CQL: 'space = "DEV" and text ~ "payment api"'
        """
        url = f"{self.api_base}/rest/api/content/search"
        params = {
            "cql": cql,
            "limit": limit,
            "expand": "body.storage,version"
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url,
                    auth=self.auth,
                    headers=self.headers,
                    params=params
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("results", [])
                else:
                    logger.error(f"Search failed: {response.status_code}")
                    return []
            except Exception as e:
                logger.error(f"Error searching pages: {e}")
                return []

    async def update_page(self, page_id: str, new_content: str,
                         update_message: str, current_version: int) -> Dict:
        """
        Update an existing Confluence page.
        This is the PRIMARY operation - we update docs where they live.
        """
        url = f"{self.api_base}/rest/api/content/{page_id}"

        # Get current page info for title
        current_page = await self.get_page_by_id(page_id)
        if not current_page:
            raise Exception(f"Page {page_id} not found")

        data = {
            "version": {
                "number": current_version + 1,
                "message": f"AI Update: {update_message}"
            },
            "title": current_page["title"],
            "type": "page",
            "body": {
                "storage": {
                    "value": new_content,
                    "representation": "storage"
                }
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.put(
                url,
                auth=self.auth,
                headers=self.headers,
                json=data
            )

            if response.status_code == 200:
                logger.info(f"Updated Confluence page {page_id}")
                return response.json()
            else:
                logger.error(f"Failed to update page: {response.status_code} - {response.text}")
                raise Exception(f"Failed to update page: {response.status_code}")

    async def update_page_section(self, page_id: str, section_heading: str,
                                 new_section_content: str, update_reason: str) -> Dict:
        """
        Update a specific section within a Confluence page.
        Preserves all other content.
        """
        # Get current page
        page_data = await self.get_page_by_id(page_id)
        if not page_data:
            logger.warning(f"Page {page_id} not found")
            return {'error': 'Page not found'}

        current_content = page_data['body']['storage']['value']
        current_version = page_data['version']['number']

        # Parse and update the section
        # Confluence uses a different markup, we need to handle HTML-like structure
        updated_content = self._update_html_section(
            current_content,
            section_heading,
            new_section_content
        )

        # Add update note
        timestamp = datetime.utcnow().isoformat()
        update_note = f'<p><em>Last updated by Kinexus AI on {timestamp}: {update_reason}</em></p>'

        # If there's already an update note, replace it
        if "Last updated by Kinexus AI" in updated_content:
            import re
            updated_content = re.sub(
                r'<p><em>Last updated by Kinexus AI.*?</em></p>',
                update_note,
                updated_content
            )
        else:
            # Add at the bottom
            updated_content += f"\n{update_note}"

        # Update the page
        result = await self.update_page(
            page_id=page_id,
            new_content=updated_content,
            update_message=f"Update {section_heading} - {update_reason}",
            current_version=current_version
        )

        return {
            'status': 'updated',
            'page_id': page_id,
            'section': section_heading,
            'version': result.get('version', {}).get('number')
        }

    def _update_html_section(self, html_content: str, section_heading: str,
                            new_content: str) -> str:
        """
        Update a section in HTML content (Confluence storage format).
        """
        # This is simplified - in production, use a proper HTML parser
        lines = html_content.split('\n')
        updated_lines = []
        in_section = False
        section_level = 0

        for line in lines:
            # Detect section start (h1, h2, h3, etc.)
            if section_heading in line and '<h' in line:
                in_section = True
                # Extract heading level
                import re
                match = re.match(r'<h(\d)>', line)
                if match:
                    section_level = int(match.group(1))
                updated_lines.append(line)
                # Add new content after heading
                updated_lines.append(new_content)
                continue

            # Detect section end
            if in_section and '<h' in line:
                import re
                match = re.match(r'<h(\d)>', line)
                if match:
                    current_level = int(match.group(1))
                    if current_level <= section_level:
                        in_section = False

            # Add line if not in the section we're replacing
            if not in_section:
                updated_lines.append(line)

        return '\n'.join(updated_lines)

    async def create_page(self, space_key: str, title: str, content: str,
                         parent_id: Optional[str] = None) -> Dict:
        """
        Create a new page in Confluence.
        This is SECONDARY - only when explicitly permitted and needed.
        """
        url = f"{self.api_base}/rest/api/content"

        data = {
            "type": "page",
            "title": title,
            "space": {"key": space_key},
            "body": {
                "storage": {
                    "value": content,
                    "representation": "storage"
                }
            },
            "metadata": {
                "labels": [
                    {"name": "kinexus-ai-managed"},
                    {"name": "auto-generated"}
                ]
            }
        }

        # Add parent if specified
        if parent_id:
            data["ancestors"] = [{"id": parent_id}]

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                auth=self.auth,
                headers=self.headers,
                json=data
            )

            if response.status_code in [200, 201]:
                logger.info(f"Created new page: {title} in space {space_key}")
                return response.json()
            else:
                logger.error(f"Failed to create page: {response.status_code}")
                raise Exception(f"Failed to create page: {response.status_code}")

    async def find_related_pages(self, keywords: List[str], space_key: Optional[str] = None) -> List[Dict]:
        """
        Find pages that might need updating based on keywords.
        """
        # Build CQL query
        text_conditions = ' OR '.join([f'text ~ "{keyword}"' for keyword in keywords])

        if space_key:
            cql = f'space = "{space_key}" AND ({text_conditions})'
        else:
            cql = text_conditions

        pages = await self.search_pages(cql)

        # Score relevance based on keyword matches
        for page in pages:
            content = page.get('body', {}).get('storage', {}).get('value', '').lower()
            score = sum(1 for keyword in keywords if keyword.lower() in content)
            page['relevance_score'] = score

        # Sort by relevance
        pages.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)

        return pages


class ConfluenceDocumentManager:
    """
    High-level document management for Confluence spaces.
    """

    def __init__(self, client: ConfluenceClient):
        self.client = client

    async def process_code_change(self, change_data: Dict) -> List[Dict]:
        """
        Process a code change and update related Confluence documentation.
        """
        results = []

        # Extract keywords from the change
        keywords = self._extract_keywords(change_data)

        # Find related pages
        space_key = change_data.get('confluence_space')  # Could be configured per repo
        related_pages = await self.client.find_related_pages(keywords, space_key)

        logger.info(f"Found {len(related_pages)} related pages for update")

        # Update each related page
        for page in related_pages[:5]:  # Limit to top 5 most relevant
            try:
                # Determine what needs updating
                update_strategy = await self._determine_update_strategy(page, change_data)

                if update_strategy['needs_update']:
                    result = await self._apply_update(page, update_strategy, change_data)
                    results.append(result)
                else:
                    logger.debug(f"Page {page['id']} doesn't need updates")
            except Exception as e:
                logger.error(f"Failed to update page {page['id']}: {e}")
                results.append({
                    'page_id': page['id'],
                    'status': 'error',
                    'error': str(e)
                })

        return results

    def _extract_keywords(self, change_data: Dict) -> List[str]:
        """
        Extract relevant keywords from change data for searching.
        """
        keywords = []

        # From file paths
        if 'files_changed' in change_data:
            for file in change_data['files_changed']:
                # Extract meaningful parts from file path
                parts = file.split('/')
                keywords.extend([p for p in parts if not p.startswith('.')])

        # From commit messages
        if 'commit_message' in change_data:
            # Extract significant words (simple approach)
            words = change_data['commit_message'].split()
            keywords.extend([w for w in words if len(w) > 3])

        # From function/class names if available
        if 'code_entities' in change_data:
            keywords.extend(change_data['code_entities'])

        return list(set(keywords))  # Unique keywords

    async def _determine_update_strategy(self, page: Dict, change_data: Dict) -> Dict:
        """
        Determine what sections need updating based on the change.
        """
        # This would use AI to analyze the page and determine updates
        # For now, simplified logic

        content = page.get('body', {}).get('storage', {}).get('value', '')

        strategy = {
            'needs_update': False,
            'sections_to_update': [],
            'update_type': None
        }

        # Check if page mentions changed files
        for file in change_data.get('files_changed', []):
            if file in content:
                strategy['needs_update'] = True
                strategy['update_type'] = 'code_reference'
                strategy['sections_to_update'].append('Code Examples')
                break

        # Check if it's API documentation
        if 'api' in page.get('title', '').lower():
            if any('api' in f for f in change_data.get('files_changed', [])):
                strategy['needs_update'] = True
                strategy['update_type'] = 'api_update'
                strategy['sections_to_update'].append('API Reference')

        return strategy

    async def _apply_update(self, page: Dict, strategy: Dict, change_data: Dict) -> Dict:
        """
        Apply the determined updates to the page.
        """
        # In production, this would use AI to generate the actual update content
        # For now, we'll add a simple notification

        update_content = f"""
        <div class="panel">
            <div class="panelContent">
                <p><strong>Recent Update:</strong></p>
                <p>The code referenced in this documentation has been updated.</p>
                <ul>
                    <li>Change: {change_data.get('commit_message', 'Code update')}</li>
                    <li>Date: {datetime.utcnow().isoformat()}</li>
                    <li>Files: {', '.join(change_data.get('files_changed', []))}</li>
                </ul>
            </div>
        </div>
        """

        # Update the first section that needs updating
        section = strategy['sections_to_update'][0] if strategy['sections_to_update'] else 'Updates'

        result = await self.client.update_page_section(
            page_id=page['id'],
            section_heading=section,
            new_section_content=update_content,
            update_reason=f"Code change: {change_data.get('commit_message', 'Update')}"
        )

        return result

    async def ensure_documentation_exists(self, repo: str, space_key: str) -> Dict:
        """
        Check if documentation exists for a repository, create if permitted.
        """
        # Search for existing documentation
        cql = f'space = "{space_key}" AND title ~ "{repo}"'
        existing = await self.client.search_pages(cql, limit=1)

        if not existing:
            logger.info(f"No documentation found for {repo} in space {space_key}")
            return {'status': 'no_docs', 'action': 'would_create'}

        return {
            'status': 'docs_exist',
            'page_id': existing[0]['id'],
            'title': existing[0]['title']
        }