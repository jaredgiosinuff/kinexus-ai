import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

import aiohttp

from .base_integration import BaseIntegration, SyncResult, TestResult

class GitHubIntegration(BaseIntegration):
    """GitHub integration for repository data and changes."""

    def __init__(self, integration):
        super().__init__(integration)
        self.api_base_url = "https://api.github.com"
        self.required_config_fields = ["repositories"]
        self.request_timeout = aiohttp.ClientTimeout(total=30)

    async def test_connection(self) -> TestResult:
        """Test connection to GitHub API."""
        try:
            headers = self.get_auth_headers()

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_base_url}/user",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:

                    if response.status == 200:
                        data = await response.json()
                        return TestResult(
                            success=True,
                            message="Connection successful",
                            details={"user": data.get("login")}
                        )
                    else:
                        return TestResult(
                            success=False,
                            message=f"HTTP {response.status}"
                        )

        except Exception as e:
            return TestResult(
                success=False,
                message=f"Connection failed: {str(e)}"
            )

    async def sync(self) -> SyncResult:
        """Sync data from GitHub repositories."""
        self.log_sync_start()
        start_time = datetime.utcnow()

        if not self.validate_config(self.required_config_fields):
            return SyncResult(success=False, error_message="Invalid configuration")

        repositories_config = self.integration.config.get("repositories", [])
        repositories = self._normalize_repositories(repositories_config)
        if not repositories:
            return SyncResult(success=False, error_message="No repositories configured")

        headers = self.get_auth_headers()
        headers.setdefault("Accept", "application/vnd.github+json")

        commits_total = 0
        repo_metadata: List[Dict[str, Any]] = []
        errors: List[str] = []

        try:
            async with aiohttp.ClientSession(headers=headers, timeout=self.request_timeout) as session:
                for repo in repositories:
                    try:
                        commits, latest_sha = await self._fetch_recent_commits(session, repo)
                        commits_total += commits
                        repo_metadata.append({
                            "repository": repo["name"],
                            "branch": repo.get("branch"),
                            "commits": commits,
                            "latest_sha": latest_sha
                        })
                    except Exception as exc:  # pragma: no cover - network failures
                        error_message = f"{repo['name']}: {exc}"
                        self.logger.error("Repository sync failed", {"repository": repo["name"], "error": str(exc)})
                        errors.append(error_message)

        except Exception as exc:  # pragma: no cover
            self.logger.error("GitHub sync encountered an unexpected error", {"error": str(exc)})
            errors.append(str(exc))

        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        success = len(errors) == 0

        result = SyncResult(
            success=success,
            records_processed=commits_total,
            records_added=commits_total,
            records_failed=len(errors),
            error_message="; ".join(errors) if errors else None,
            metadata={
                "repositories": repo_metadata,
                "errors": errors,
                "since": self.integration.last_sync.isoformat() if self.integration.last_sync else None
            }
        )

        self.log_sync_complete(result, duration_ms)
        return result

    async def process_webhook(self, event_type: str, payload: Dict[str, Any]) -> bool:
        """Process GitHub webhook events."""
        self.log_webhook_received(event_type)

        # Implementation would handle push, pull_request, issues events
        # This is a placeholder implementation

        return True

    def _normalize_repositories(self, repositories: List[Any]) -> List[Dict[str, Optional[str]]]:
        normalized: List[Dict[str, Optional[str]]] = []
        for item in repositories:
            if isinstance(item, str):
                normalized.append({"name": item, "branch": None})
            elif isinstance(item, dict) and "name" in item:
                normalized.append({"name": item["name"], "branch": item.get("branch")})
        return normalized

    async def _fetch_recent_commits(
        self,
        session: aiohttp.ClientSession,
        repo: Dict[str, Optional[str]]
    ) -> Tuple[int, Optional[str]]:
        repo_name = repo["name"]
        params = {"per_page": 50}
        if repo.get("branch"):
            params["sha"] = repo["branch"]
        if self.integration.last_sync:
            params["since"] = self.integration.last_sync.isoformat()

        url = f"{self.api_base_url}/repos/{repo_name}/commits"
        async with session.get(url, params=params) as response:
            if response.status == 403:
                retry = self.handle_rate_limit(response.headers)
                if retry:
                    await asyncio.sleep(retry)
                    return await self._fetch_recent_commits(session, repo)

            if response.status != 200:
                text = await response.text()
                raise RuntimeError(f"HTTP {response.status}: {text}")

            commits = await response.json()
            if not isinstance(commits, list):
                raise RuntimeError("Unexpected response payload from GitHub")

            latest_sha = commits[0].get("sha") if commits else None
            return len(commits), latest_sha
