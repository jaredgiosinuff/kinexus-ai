"""
SharePoint Client for Document Management
Manages documents that live in SharePoint document libraries
"""

from datetime import datetime
from typing import Dict, List, Optional

import httpx
import msal
import structlog

logger = structlog.get_logger()


class SharePointClient:
    """
    Client for managing documents in SharePoint.
    This client UPDATES existing documents, not creates shadow copies.
    """

    def __init__(
        self, tenant_id: str, client_id: str, client_secret: str, site_url: str
    ):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.site_url = site_url.rstrip("/")
        self.access_token = None
        self._init_auth()

    def _init_auth(self):
        """Initialize MSAL authentication."""
        authority = f"https://login.microsoftonline.com/{self.tenant_id}"

        self.app = msal.ConfidentialClientApplication(
            self.client_id, authority=authority, client_credential=self.client_secret
        )

    async def _get_access_token(self) -> str:
        """Get or refresh access token."""
        scope = ["https://graph.microsoft.com/.default"]

        result = self.app.acquire_token_silent(scope, account=None)
        if not result:
            result = self.app.acquire_token_for_client(scopes=scope)

        if "access_token" in result:
            self.access_token = result["access_token"]
            return self.access_token
        else:
            raise Exception(
                f"Could not obtain access token: {result.get('error_description')}"
            )

    async def get_document(self, library_name: str, file_path: str) -> Optional[Dict]:
        """
        Get document metadata and download URL from SharePoint.
        """
        await self._get_access_token()

        # Parse site URL to get site ID
        site_id = await self._get_site_id()

        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient() as client:
            # First, get the drive ID for the document library
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                logger.error(f"Failed to get drives: {response.status_code}")
                return None

            drives = response.json().get("value", [])
            drive_id = None
            for drive in drives:
                if drive["name"] == library_name:
                    drive_id = drive["id"]
                    break

            if not drive_id:
                logger.error(f"Document library {library_name} not found")
                return None

            # Get the file
            file_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root:/{file_path}"
            response = await client.get(file_url, headers=headers)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.debug(f"File not found: {file_path}")
                return None
            else:
                logger.error(f"Error getting file: {response.status_code}")
                return None

    async def get_document_content(
        self, library_name: str, file_path: str
    ) -> Optional[str]:
        """
        Download and return the content of a document.
        """
        file_metadata = await self.get_document(library_name, file_path)
        if not file_metadata:
            return None

        download_url = file_metadata.get("@microsoft.graph.downloadUrl")
        if not download_url:
            logger.error("No download URL found")
            return None

        async with httpx.AsyncClient() as client:
            response = await client.get(download_url)
            if response.status_code == 200:
                return response.text
            else:
                logger.error(f"Failed to download file: {response.status_code}")
                return None

    async def update_document(
        self, library_name: str, file_path: str, content: str, message: str
    ) -> Dict:
        """
        Update an existing document in SharePoint.
        This is the PRIMARY operation - we update docs where they live.
        """
        await self._get_access_token()

        site_id = await self._get_site_id()

        # Get drive ID
        drive_id = await self._get_drive_id(site_id, library_name)
        if not drive_id:
            raise Exception(f"Document library {library_name} not found")

        # Upload the updated content
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root:/{file_path}:/content"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "text/plain",
        }

        async with httpx.AsyncClient() as client:
            response = await client.put(
                url, headers=headers, content=content.encode("utf-8")
            )

            if response.status_code in [200, 201]:
                logger.info(f"Updated {library_name}/{file_path}")

                # Add version comment
                await self._add_version_comment(site_id, drive_id, file_path, message)

                return response.json()
            else:
                logger.error(f"Failed to update document: {response.status_code}")
                raise Exception(f"Failed to update document: {response.status_code}")

    async def update_document_section(
        self,
        library_name: str,
        file_path: str,
        section_name: str,
        new_content: str,
        reason: str,
    ) -> Dict:
        """
        Update a specific section within a document.
        Preserves all other content.
        """
        # Get current content
        current_content = await self.get_document_content(library_name, file_path)
        if not current_content:
            return {"error": "Document not found"}

        # Update the section (simplified - in production use proper parsing)
        lines = current_content.split("\n")
        updated_lines = []
        in_section = False
        section_level = 0

        for line in lines:
            # Detect section start (Markdown headers)
            if section_name in line and line.startswith("#"):
                in_section = True
                section_level = len(line.split(" ")[0])  # Count # symbols
                updated_lines.append(line)
                updated_lines.append("")  # Empty line after header
                updated_lines.append(new_content)
                continue

            # Detect section end
            if in_section and line.startswith("#"):
                current_level = len(line.split(" ")[0])
                if current_level <= section_level:
                    in_section = False

            # Add line if not in the section we're replacing
            if not in_section:
                updated_lines.append(line)

        updated_content = "\n".join(updated_lines)

        # Add update note
        timestamp = datetime.utcnow().isoformat()
        update_note = (
            f"\n\n<!-- Last updated by Kinexus AI on {timestamp}: {reason} -->\n"
        )

        if "<!-- Last updated by Kinexus AI" not in updated_content:
            updated_content += update_note
        else:
            # Replace existing update note
            import re

            updated_content = re.sub(
                r"<!-- Last updated by Kinexus AI.*?-->",
                update_note.strip(),
                updated_content,
            )

        # Update the document
        _result = await self.update_document(
            library_name=library_name,
            file_path=file_path,
            content=updated_content,
            message=f"AI: Update {section_name} - {reason}",
        )

        return {
            "status": "updated",
            "library": library_name,
            "path": file_path,
            "section": section_name,
        }

    async def create_document(
        self, library_name: str, file_path: str, content: str, message: str
    ) -> Dict:
        """
        Create a new document in SharePoint.
        This is SECONDARY - only when explicitly permitted and needed.
        """
        # Same as update but for new files
        return await self.update_document(library_name, file_path, content, message)

    async def search_documents(
        self, query: str, library_name: Optional[str] = None
    ) -> List[Dict]:
        """
        Search for documents across SharePoint.
        """
        await self._get_access_token()

        # Use Microsoft Graph search API
        url = "https://graph.microsoft.com/v1.0/search/query"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        search_request = {
            "requests": [
                {
                    "entityTypes": ["driveItem"],
                    "query": {"queryString": query},
                    "from": 0,
                    "size": 25,
                }
            ]
        }

        # Add site scope if specified
        if self.site_url:
            search_request["requests"][0]["region"] = "NAM"  # Adjust as needed

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=search_request)

            if response.status_code == 200:
                data = response.json()
                hits = (
                    data.get("value", [{}])[0]
                    .get("hitsContainers", [{}])[0]
                    .get("hits", [])
                )
                return [hit["resource"] for hit in hits]
            else:
                logger.error(f"Search failed: {response.status_code}")
                return []

    async def _get_site_id(self) -> str:
        """Get the SharePoint site ID from the site URL."""
        await self._get_access_token()

        # Parse site URL to extract host and path
        from urllib.parse import urlparse

        parsed = urlparse(self.site_url)
        host = parsed.netloc
        site_path = parsed.path

        url = f"https://graph.microsoft.com/v1.0/sites/{host}:{site_path}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()["id"]
            else:
                raise Exception(f"Could not get site ID: {response.status_code}")

    async def _get_drive_id(self, site_id: str, library_name: str) -> Optional[str]:
        """Get the drive ID for a document library."""
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                drives = response.json().get("value", [])
                for drive in drives:
                    if drive["name"] == library_name:
                        return drive["id"]
        return None

    async def _add_version_comment(
        self, site_id: str, drive_id: str, file_path: str, comment: str
    ):
        """Add a version comment to a document."""
        # This would use SharePoint's versioning API
        # Simplified for MVP
        logger.info(f"Version comment: {comment}")


class SharePointDocumentManager:
    """
    High-level document management for SharePoint.
    """

    def __init__(self, client: SharePointClient):
        self.client = client

    async def process_change(self, change_data: Dict) -> List[Dict]:
        """
        Process a change and update related SharePoint documentation.
        """
        results = []

        # Build search query from change data
        search_terms = []

        # Add file names
        for file in change_data.get("files_changed", []):
            # Extract meaningful parts
            parts = file.replace("/", " ").replace("_", " ").replace("-", " ")
            search_terms.append(parts)

        # Add keywords from commit message
        if "commit_message" in change_data:
            search_terms.append(change_data["commit_message"])

        query = " OR ".join(search_terms) if search_terms else ""

        if not query:
            logger.warning("No search terms extracted from change data")
            return results

        # Search for related documents
        documents = await self.client.search_documents(query)
        logger.info(f"Found {len(documents)} related documents in SharePoint")

        # Update each document
        for doc in documents[:5]:  # Limit to top 5
            try:
                result = await self._update_document(doc, change_data)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to update document: {e}")
                results.append(
                    {"document": doc.get("name"), "status": "error", "error": str(e)}
                )

        return results

    async def _update_document(self, doc: Dict, change_data: Dict) -> Dict:
        """
        Update a specific document based on the change.
        """
        # Extract library and path from document metadata
        parent_ref = doc.get("parentReference", {})
        library_name = parent_ref.get("name", "Documents")
        file_path = doc.get("name")

        # Determine what needs updating
        # In production, this would use AI to analyze and generate updates

        update_content = f"""
## Recent System Update

**Date:** {datetime.utcnow().isoformat()}
**Change Type:** Code Update
**Summary:** {change_data.get('commit_message', 'System update')}

### Affected Components
"""

        for file in change_data.get("files_changed", []):
            update_content += f"- `{file}`\n"

        update_content += """

### Action Required
Please review the updated components and ensure any dependent documentation is current.
"""

        # Update the document
        result = await self.client.update_document_section(
            library_name=library_name,
            file_path=file_path,
            section_name="Updates",
            new_content=update_content,
            reason=f"Code change: {change_data.get('commit_message', 'Update')}",
        )

        return result

    async def ensure_documentation_structure(self, library_name: str) -> Dict:
        """
        Ensure basic documentation structure exists in SharePoint.
        """
        # Check for key documents
        required_docs = [
            "README.md",
            "API_Documentation.md",
            "Architecture.md",
            "Deployment_Guide.md",
        ]

        existing = []
        missing = []

        for doc_name in required_docs:
            doc = await self.client.get_document(library_name, doc_name)
            if doc:
                existing.append(doc_name)
            else:
                missing.append(doc_name)

        return {
            "library": library_name,
            "existing_docs": existing,
            "missing_docs": missing,
            "status": "complete" if not missing else "incomplete",
        }
