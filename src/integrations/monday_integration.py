import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp

from .base_integration import BaseIntegration, SyncResult, TestResult


class MondayIntegration(BaseIntegration):
    """Monday.com integration for project management data."""

    def __init__(self, integration):
        super().__init__(integration)
        self.api_base_url = "https://api.monday.com/v2"
        self.required_config_fields = ["boards"]

    async def test_connection(self) -> TestResult:
        """Test connection to Monday.com API."""
        start_time = datetime.utcnow()

        try:
            if not self.validate_config(self.required_config_fields):
                return TestResult(
                    success=False,
                    message="Invalid configuration: missing required fields",
                )

            # Test query to get user information
            query = """
            query {
                me {
                    id
                    name
                    email
                }
            }
            """

            headers = self.get_auth_headers()
            headers["Content-Type"] = "application/json"

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_base_url,
                    json={"query": query},
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    response_time = (
                        datetime.utcnow() - start_time
                    ).total_seconds() * 1000

                    if response.status == 200:
                        data = await response.json()

                        if "errors" in data:
                            return TestResult(
                                success=False,
                                message=f"API error: {data['errors'][0]['message']}",
                                response_time_ms=response_time,
                            )

                        user_data = data.get("data", {}).get("me", {})
                        return TestResult(
                            success=True,
                            message="Connection successful",
                            details={
                                "user_id": user_data.get("id"),
                                "user_name": user_data.get("name"),
                                "user_email": user_data.get("email"),
                            },
                            response_time_ms=response_time,
                        )
                    else:
                        error_text = await response.text()
                        return TestResult(
                            success=False,
                            message=f"HTTP {response.status}: {error_text}",
                            response_time_ms=response_time,
                        )

        except asyncio.TimeoutError:
            return TestResult(success=False, message="Connection timeout")
        except Exception as e:
            return TestResult(success=False, message=f"Connection failed: {str(e)}")

    async def sync(self) -> SyncResult:
        """Sync data from Monday.com boards."""
        self.log_sync_start()
        start_time = datetime.utcnow()

        try:
            if not self.validate_config(self.required_config_fields):
                return SyncResult(
                    success=False,
                    error_message="Invalid configuration: missing required fields",
                )

            boards = self.integration.config.get("boards", [])
            columns = self.integration.config.get("columns", [])

            total_processed = 0
            total_added = 0
            total_updated = 0
            total_failed = 0

            for board_id in boards:
                try:
                    result = await self._sync_board(board_id, columns)
                    total_processed += result.records_processed
                    total_added += result.records_added
                    total_updated += result.records_updated
                    total_failed += result.records_failed

                except Exception as e:
                    self.logger.error(
                        "Failed to sync board", {"board_id": board_id, "error": str(e)}
                    )
                    total_failed += 1

            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            result = SyncResult(
                success=total_failed == 0,
                records_processed=total_processed,
                records_added=total_added,
                records_updated=total_updated,
                records_failed=total_failed,
                metadata={"boards_synced": len(boards), "duration_ms": duration_ms},
            )

            self.log_sync_complete(result, duration_ms)
            return result

        except Exception as e:
            error_message = f"Sync failed: {str(e)}"
            self.logger.error(
                "Monday.com sync failed",
                {"integration_id": self.integration.id, "error": str(e)},
            )

            return SyncResult(success=False, error_message=error_message)

    async def _sync_board(self, board_id: int, columns: List[str]) -> SyncResult:
        """Sync items from a specific board."""
        try:
            # Build GraphQL query for board items
            column_filter = ""
            if columns:
                column_filter = f"columns: {json.dumps(columns)}"

            query = f"""
            query {{
                boards(ids: [{board_id}]) {{
                    id
                    name
                    description
                    state
                    board_kind
                    items_page {{
                        cursor
                        items {{
                            id
                            name
                            state
                            created_at
                            updated_at
                            creator {{
                                id
                                name
                                email
                            }}
                            column_values({column_filter}) {{
                                id
                                type
                                text
                                value
                                column {{
                                    id
                                    title
                                    type
                                }}
                            }}
                            subitems {{
                                id
                                name
                                column_values {{
                                    id
                                    type
                                    text
                                    value
                                }}
                            }}
                            updates {{
                                id
                                body
                                created_at
                                creator {{
                                    id
                                    name
                                }}
                            }}
                        }}
                    }}
                }}
            }}
            """

            headers = self.get_auth_headers()
            headers["Content-Type"] = "application/json"

            processed = 0
            added = 0
            updated = 0
            failed = 0

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_base_url,
                    json={"query": query},
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as response:

                    if response.status != 200:
                        raise Exception(
                            f"API request failed with status {response.status}"
                        )

                    data = await response.json()

                    if "errors" in data:
                        raise Exception(
                            f"GraphQL error: {data['errors'][0]['message']}"
                        )

                    boards_data = data.get("data", {}).get("boards", [])

                    if not boards_data:
                        self.logger.warning("Board not found", {"board_id": board_id})
                        return SyncResult(success=True)

                    board_data = boards_data[0]
                    items = board_data.get("items_page", {}).get("items", [])

                    for item in items:
                        try:
                            # Process each item
                            await self._process_item(board_id, item)
                            processed += 1

                            # Determine if this is new or updated
                            # For simplicity, we'll consider all as updated
                            # In a real implementation, you'd check against existing data
                            updated += 1

                        except Exception as e:
                            self.logger.error(
                                "Failed to process item",
                                {
                                    "board_id": board_id,
                                    "item_id": item.get("id"),
                                    "error": str(e),
                                },
                            )
                            failed += 1

            return SyncResult(
                success=failed == 0,
                records_processed=processed,
                records_added=added,
                records_updated=updated,
                records_failed=failed,
            )

        except Exception as e:
            self.logger.error(
                "Failed to sync board", {"board_id": board_id, "error": str(e)}
            )
            raise

    async def _process_item(self, board_id: int, item_data: Dict[str, Any]):
        """Process a Monday.com item and store in our system."""
        try:
            # Extract item information
            item_id = item_data.get("id")
            item_name = item_data.get("name")
            item_state = item_data.get("state")
            created_at = item_data.get("created_at")
            updated_at = item_data.get("updated_at")

            # Extract creator information
            creator = item_data.get("creator", {})
            creator_name = creator.get("name")
            creator_email = creator.get("email")

            # Extract column values
            column_values = {}
            for column_value in item_data.get("column_values", []):
                column = column_value.get("column", {})
                column_id = column.get("id")
                column_title = column.get("title")
                value_text = column_value.get("text")
                value_raw = column_value.get("value")

                if column_id:
                    column_values[column_id] = {
                        "title": column_title,
                        "text": value_text,
                        "raw_value": value_raw,
                        "type": column_value.get("type"),
                    }

            # Extract subitems
            subitems = []
            for subitem in item_data.get("subitems", []):
                subitem_data = {
                    "id": subitem.get("id"),
                    "name": subitem.get("name"),
                    "column_values": {},
                }

                for sub_column_value in subitem.get("column_values", []):
                    sub_column_id = sub_column_value.get("id")
                    if sub_column_id:
                        subitem_data["column_values"][sub_column_id] = {
                            "text": sub_column_value.get("text"),
                            "raw_value": sub_column_value.get("value"),
                            "type": sub_column_value.get("type"),
                        }

                subitems.append(subitem_data)

            # Extract updates/comments
            updates = []
            for update in item_data.get("updates", []):
                update_creator = update.get("creator", {})
                updates.append(
                    {
                        "id": update.get("id"),
                        "body": update.get("body"),
                        "created_at": update.get("created_at"),
                        "creator_name": update_creator.get("name"),
                        "creator_id": update_creator.get("id"),
                    }
                )

            # Create document data structure
            _document_data = {
                "source": "monday.com",
                "source_id": f"monday_{board_id}_{item_id}",
                "title": item_name,
                "content": self._format_item_content(item_data, column_values),
                "metadata": {
                    "board_id": board_id,
                    "item_id": item_id,
                    "item_state": item_state,
                    "creator_name": creator_name,
                    "creator_email": creator_email,
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "column_values": column_values,
                    "subitems": subitems,
                    "updates": updates[:5],  # Limit to recent 5 updates
                },
                "tags": self._extract_tags(column_values),
                "last_modified": updated_at,
                "integration_id": self.integration.id,
            }

            # Here you would typically save to your document management system
            # For now, we'll just log the processed item
            self.logger.debug(
                "Item processed",
                {
                    "board_id": board_id,
                    "item_id": item_id,
                    "item_name": item_name,
                    "column_count": len(column_values),
                    "subitem_count": len(subitems),
                    "update_count": len(updates),
                },
            )

            # In a real implementation, you would:
            # 1. Check if document already exists
            # 2. Create or update the document
            # 3. Update vector embeddings
            # 4. Trigger any necessary workflows

        except Exception as e:
            self.logger.error(
                "Failed to process Monday.com item",
                {"board_id": board_id, "item_id": item_data.get("id"), "error": str(e)},
            )
            raise

    def _format_item_content(
        self, item_data: Dict[str, Any], column_values: Dict[str, Any]
    ) -> str:
        """Format item data into readable content."""
        content_parts = []

        # Add item name as title
        item_name = item_data.get("name")
        if item_name:
            content_parts.append(f"# {item_name}")

        # Add item state
        item_state = item_data.get("state")
        if item_state:
            content_parts.append(f"**Status:** {item_state}")

        # Add column values
        if column_values:
            content_parts.append("\n## Details")
            for column_id, column_data in column_values.items():
                title = column_data.get("title", column_id)
                text = column_data.get("text")
                if text and text.strip():
                    content_parts.append(f"**{title}:** {text}")

        # Add recent updates/comments
        updates = item_data.get("updates", [])
        if updates:
            content_parts.append("\n## Recent Updates")
            for update in updates[:3]:  # Show only recent 3 updates
                body = update.get("body", "").strip()
                creator_name = update.get("creator", {}).get("name", "Unknown")
                created_at = update.get("created_at", "")
                if body:
                    content_parts.append(f"**{creator_name}** ({created_at}): {body}")

        return "\n\n".join(content_parts)

    def _extract_tags(self, column_values: Dict[str, Any]) -> List[str]:
        """Extract tags from column values."""
        tags = ["monday.com"]

        # Add tags based on column types and values
        for column_id, column_data in column_values.items():
            column_type = column_data.get("type", "")
            text = column_data.get("text", "")

            # Extract tags from status columns
            if column_type in ["color", "status"] and text:
                tags.append(f"status:{text.lower()}")

            # Extract tags from people columns
            elif column_type == "multiple-person" and text:
                tags.append(f"assigned:{text.lower()}")

            # Extract tags from timeline columns
            elif column_type == "timeline" and text:
                tags.append("has_timeline")

            # Extract tags from priority columns
            elif "priority" in column_data.get("title", "").lower() and text:
                tags.append(f"priority:{text.lower()}")

        return list(set(tags))  # Remove duplicates

    async def process_webhook(self, event_type: str, payload: Dict[str, Any]) -> bool:
        """Process Monday.com webhook events."""
        self.log_webhook_received(event_type)

        try:
            # Monday.com webhook payload structure
            event = payload.get("event", {})
            pulse_id = event.get("pulseId")
            board_id = event.get("boardId")
            _user_id = event.get("userId")

            # Check if this board is in our configuration
            configured_boards = self.integration.config.get("boards", [])
            if board_id and board_id not in configured_boards:
                self.logger.debug(
                    "Webhook for unconfigured board",
                    {"board_id": board_id, "pulse_id": pulse_id},
                )
                return True  # Not an error, just not relevant

            # Handle different event types
            if event_type in ["create_pulse", "create_item"]:
                await self._handle_item_created(board_id, pulse_id, payload)
            elif event_type in ["change_column_value", "update_column_value"]:
                await self._handle_item_updated(board_id, pulse_id, payload)
            elif event_type in ["delete_pulse", "archive_pulse"]:
                await self._handle_item_deleted(board_id, pulse_id, payload)
            elif event_type == "create_update":
                await self._handle_update_created(board_id, pulse_id, payload)
            else:
                self.logger.warning(
                    "Unhandled webhook event type",
                    {
                        "event_type": event_type,
                        "board_id": board_id,
                        "pulse_id": pulse_id,
                    },
                )

            return True

        except Exception as e:
            self.logger.error(
                "Failed to process webhook", {"event_type": event_type, "error": str(e)}
            )
            return False

    async def _handle_item_created(
        self, board_id: int, pulse_id: int, payload: Dict[str, Any]
    ):
        """Handle item creation webhook."""
        try:
            # Fetch the full item data
            item_data = await self._fetch_item_data(board_id, pulse_id)
            if item_data:
                await self._process_item(board_id, item_data)

            self.logger.info(
                "Item created via webhook", {"board_id": board_id, "pulse_id": pulse_id}
            )

        except Exception as e:
            self.logger.error(
                "Failed to handle item creation",
                {"board_id": board_id, "pulse_id": pulse_id, "error": str(e)},
            )

    async def _handle_item_updated(
        self, board_id: int, pulse_id: int, payload: Dict[str, Any]
    ):
        """Handle item update webhook."""
        try:
            # Fetch the updated item data
            item_data = await self._fetch_item_data(board_id, pulse_id)
            if item_data:
                await self._process_item(board_id, item_data)

            self.logger.info(
                "Item updated via webhook", {"board_id": board_id, "pulse_id": pulse_id}
            )

        except Exception as e:
            self.logger.error(
                "Failed to handle item update",
                {"board_id": board_id, "pulse_id": pulse_id, "error": str(e)},
            )

    async def _handle_item_deleted(
        self, board_id: int, pulse_id: int, payload: Dict[str, Any]
    ):
        """Handle item deletion webhook."""
        try:
            # Mark the document as deleted in our system
            source_id = f"monday_{board_id}_{pulse_id}"

            # Here you would typically:
            # 1. Find the document by source_id
            # 2. Mark it as deleted or remove it
            # 3. Update any related data

            self.logger.info(
                "Item deleted via webhook",
                {"board_id": board_id, "pulse_id": pulse_id, "source_id": source_id},
            )

        except Exception as e:
            self.logger.error(
                "Failed to handle item deletion",
                {"board_id": board_id, "pulse_id": pulse_id, "error": str(e)},
            )

    async def _handle_update_created(
        self, board_id: int, pulse_id: int, payload: Dict[str, Any]
    ):
        """Handle update/comment creation webhook."""
        try:
            # Fetch the updated item data to get the new comment
            item_data = await self._fetch_item_data(board_id, pulse_id)
            if item_data:
                await self._process_item(board_id, item_data)

            self.logger.info(
                "Update created via webhook",
                {"board_id": board_id, "pulse_id": pulse_id},
            )

        except Exception as e:
            self.logger.error(
                "Failed to handle update creation",
                {"board_id": board_id, "pulse_id": pulse_id, "error": str(e)},
            )

    async def _fetch_item_data(
        self, board_id: int, pulse_id: int
    ) -> Optional[Dict[str, Any]]:
        """Fetch detailed item data from Monday.com API."""
        try:
            query = f"""
            query {{
                items(ids: [{pulse_id}]) {{
                    id
                    name
                    state
                    created_at
                    updated_at
                    creator {{
                        id
                        name
                        email
                    }}
                    column_values {{
                        id
                        type
                        text
                        value
                        column {{
                            id
                            title
                            type
                        }}
                    }}
                    subitems {{
                        id
                        name
                        column_values {{
                            id
                            type
                            text
                            value
                        }}
                    }}
                    updates(limit: 5) {{
                        id
                        body
                        created_at
                        creator {{
                            id
                            name
                        }}
                    }}
                }}
            }}
            """

            headers = self.get_auth_headers()
            headers["Content-Type"] = "application/json"

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_base_url,
                    json={"query": query},
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:

                    if response.status != 200:
                        self.logger.error(
                            "Failed to fetch item data",
                            {
                                "board_id": board_id,
                                "pulse_id": pulse_id,
                                "status": response.status,
                            },
                        )
                        return None

                    data = await response.json()

                    if "errors" in data:
                        self.logger.error(
                            "GraphQL error fetching item",
                            {
                                "board_id": board_id,
                                "pulse_id": pulse_id,
                                "errors": data["errors"],
                            },
                        )
                        return None

                    items = data.get("data", {}).get("items", [])
                    return items[0] if items else None

        except Exception as e:
            self.logger.error(
                "Exception fetching item data",
                {"board_id": board_id, "pulse_id": pulse_id, "error": str(e)},
            )
            return None
