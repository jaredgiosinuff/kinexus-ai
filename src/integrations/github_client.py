"""
GitHub Client for Document Management
Manages documents that live in GitHub repositories
"""

import base64
from typing import Dict, Optional

import httpx
import structlog

logger = structlog.get_logger()


class GitHubClient:
    """
    Client for managing documents in GitHub repositories.
    This client UPDATES existing files, not creates shadow copies.
    """

    def __init__(self, token: str, base_url: str = "https://api.github.com"):
        self.token = token
        self.base_url = base_url
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }

    async def get_file(self, repo: str, path: str, ref: str = "main") -> Optional[Dict]:
        """
        Get file metadata and content from GitHub.
        Returns None if file doesn't exist.
        """
        url = f"{self.base_url}/repos/{repo}/contents/{path}"
        params = {"ref": ref}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self.headers, params=params)
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    logger.debug(f"File not found: {repo}/{path}")
                    return None
                else:
                    logger.error(f"Error getting file: {response.status_code}")
                    return None
            except Exception as e:
                logger.error(f"Error fetching file: {e}")
                return None

    async def get_file_content(
        self, repo: str, path: str, ref: str = "main"
    ) -> Optional[str]:
        """
        Get the decoded content of a file.
        """
        file_data = await self.get_file(repo, path, ref)
        if file_data and "content" in file_data:
            # GitHub returns base64 encoded content
            content = base64.b64decode(file_data["content"]).decode("utf-8")
            return content
        return None

    async def update_file(
        self,
        repo: str,
        path: str,
        content: str,
        message: str,
        sha: str,
        branch: str = "main",
    ) -> Dict:
        """
        Update an existing file in GitHub.
        This is the PRIMARY operation - we update docs where they live.
        """
        url = f"{self.base_url}/repos/{repo}/contents/{path}"

        # Encode content to base64
        encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")

        data = {
            "message": message,
            "content": encoded_content,
            "sha": sha,  # Required for updates
            "branch": branch,
        }

        async with httpx.AsyncClient() as client:
            response = await client.put(url, headers=self.headers, json=data)

            if response.status_code in [200, 201]:
                logger.info(f"Updated {repo}/{path}")
                return response.json()
            else:
                logger.error(
                    f"Failed to update file: {response.status_code} - {response.text}"
                )
                raise Exception(f"Failed to update file: {response.status_code}")

    async def create_file(
        self, repo: str, path: str, content: str, message: str, branch: str = "main"
    ) -> Dict:
        """
        Create a new file in GitHub.
        This is SECONDARY - only when explicitly permitted and needed.
        """
        url = f"{self.base_url}/repos/{repo}/contents/{path}"

        encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")

        data = {"message": message, "content": encoded_content, "branch": branch}

        async with httpx.AsyncClient() as client:
            response = await client.put(url, headers=self.headers, json=data)

            if response.status_code in [200, 201]:
                logger.info(f"Created new file {repo}/{path}")
                return response.json()
            else:
                logger.error(f"Failed to create file: {response.status_code}")
                raise Exception(f"Failed to create file: {response.status_code}")

    async def find_documentation_files(self, repo: str) -> list:
        """
        Find all documentation files in a repository.
        Looks for common documentation patterns.
        """
        doc_files = []

        # Check root directory
        root_files = await self.list_files(repo, "")
        for file in root_files:
            if file["name"].upper() in ["README.MD", "CONTRIBUTING.MD", "CHANGELOG.MD"]:
                doc_files.append(file)

        # Check docs directory if it exists
        docs_files = await self.list_files(repo, "docs")
        if docs_files:
            doc_files.extend([f for f in docs_files if f["name"].endswith(".md")])

        return doc_files

    async def list_files(self, repo: str, path: str = "") -> list:
        """
        List files in a directory.
        """
        url = f"{self.base_url}/repos/{repo}/contents/{path}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self.headers)
                if response.status_code == 200:
                    return response.json()
                return []
            except Exception:
                return []


class GitHubDocumentManager:
    """
    High-level document management for GitHub repositories.
    """

    def __init__(self, client: GitHubClient):
        self.client = client

    async def update_readme_section(
        self, repo: str, section_name: str, new_content: str, reason: str
    ) -> Dict:
        """
        Update a specific section of a README file.
        Preserves all other content.
        """

        # Get current README
        file_data = await self.client.get_file(repo, "README.md")
        if not file_data:
            logger.warning(f"No README.md found in {repo}")
            return {"error": "README.md not found"}

        current_content = base64.b64decode(file_data["content"]).decode("utf-8")

        # Find and update the section
        lines = current_content.split("\n")
        updated_lines = []
        in_section = False
        section_level = 0

        for line in lines:
            # Detect section start
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

        # Add update note at the bottom
        update_note = f"\n\n<!-- Last updated by Kinexus AI: {reason} -->\n"
        if "<!-- Last updated by Kinexus AI:" not in updated_content:
            updated_content += update_note
        else:
            # Replace existing update note
            import re

            updated_content = re.sub(
                r"<!-- Last updated by Kinexus AI:.*?-->",
                update_note.strip(),
                updated_content,
            )

        # Update the file
        result = await self.client.update_file(
            repo=repo,
            path="README.md",
            content=updated_content,
            message=f"AI: Update {section_name} section - {reason}",
            sha=file_data["sha"],
        )

        return {
            "status": "updated",
            "section": section_name,
            "commit": result.get("commit", {}).get("sha"),
        }

    async def ensure_documentation_exists(self, repo: str) -> Dict:
        """
        Check if basic documentation exists, create if permitted.
        """
        readme = await self.client.get_file(repo, "README.md")

        if not readme:
            # Check if we have permission to create
            # In production, this would check permissions table
            logger.info(f"No README.md in {repo}, would create if permitted")
            return {"status": "no_readme", "action": "would_create"}

        return {"status": "readme_exists", "path": "README.md"}
