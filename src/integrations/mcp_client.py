#!/usr/bin/env python3
"""
Model Context Protocol (MCP) Client Implementation for Kinexus AI
Connects to external MCP servers and integrates with our multi-agent system
"""
import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import aiohttp
import websockets
from mcp_server import MCPMessage, MCPMessageType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MCPTransport(Enum):
    """MCP transport types"""

    HTTP = "http"
    WEBSOCKET = "websocket"
    STDIO = "stdio"


@dataclass
class MCPServerConnection:
    """MCP Server connection configuration"""

    name: str
    url: str
    transport: MCPTransport
    auth_token: Optional[str] = None
    capabilities: Dict[str, Any] = None


class MCPClient:
    """
    Model Context Protocol Client for Kinexus AI
    Connects to external MCP servers and integrates tools/resources
    """

    def __init__(self, client_name: str = "kinexus-ai-mcp-client"):
        self.client_name = client_name
        self.connections: Dict[str, MCPServerConnection] = {}
        self.server_capabilities: Dict[str, Dict[str, Any]] = {}
        self.available_tools: Dict[str, Dict[str, Any]] = {}
        self.available_resources: Dict[str, Dict[str, Any]] = {}

        # Session management
        self.sessions: Dict[str, aiohttp.ClientSession] = {}
        self.websockets: Dict[str, websockets.WebSocketServerProtocol] = {}

    async def connect_to_server(self, connection: MCPServerConnection) -> bool:
        """Connect to an MCP server"""
        try:
            logger.info(
                f"Connecting to MCP server: {connection.name} at {connection.url}"
            )

            if connection.transport == MCPTransport.HTTP:
                await self._connect_http(connection)
            elif connection.transport == MCPTransport.WEBSOCKET:
                await self._connect_websocket(connection)
            else:
                logger.error(f"Unsupported transport: {connection.transport}")
                return False

            self.connections[connection.name] = connection

            # Perform handshake and discovery
            await self._perform_handshake(connection.name)
            await self._discover_capabilities(connection.name)

            logger.info(f"Successfully connected to MCP server: {connection.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to MCP server {connection.name}: {str(e)}")
            return False

    async def _connect_http(self, connection: MCPServerConnection):
        """Establish HTTP connection to MCP server"""
        session = aiohttp.ClientSession(
            headers={
                "Content-Type": "application/json",
                "User-Agent": f"{self.client_name}/1.0.0",
            }
        )

        if connection.auth_token:
            session.headers["Authorization"] = f"Bearer {connection.auth_token}"

        self.sessions[connection.name] = session

    async def _connect_websocket(self, connection: MCPServerConnection):
        """Establish WebSocket connection to MCP server"""
        headers = {"User-Agent": f"{self.client_name}/1.0.0"}

        if connection.auth_token:
            headers["Authorization"] = f"Bearer {connection.auth_token}"

        websocket = await websockets.connect(connection.url, extra_headers=headers)
        self.websockets[connection.name] = websocket

    async def _perform_handshake(self, server_name: str):
        """Perform MCP handshake with server"""
        handshake_message = MCPMessage(
            id=str(uuid.uuid4()),
            message_type=MCPMessageType.REQUEST,
            method="initialize",
            params={
                "protocolVersion": "1.0.0",
                "clientInfo": {
                    "name": self.client_name,
                    "version": "1.0.0",
                    "description": "Kinexus AI MCP Client for autonomous documentation management",
                },
            },
        )

        response = await self._send_request(server_name, handshake_message)

        if response and not response.error:
            logger.info(f"Handshake successful with {server_name}")
            self.server_capabilities[server_name] = response.result
        else:
            logger.error(
                f"Handshake failed with {server_name}: {response.error if response else 'No response'}"
            )

    async def _discover_capabilities(self, server_name: str):
        """Discover tools and resources from MCP server"""
        # Discover tools
        tools_request = MCPMessage(
            id=str(uuid.uuid4()),
            message_type=MCPMessageType.REQUEST,
            method="tools/list",
        )

        tools_response = await self._send_request(server_name, tools_request)
        if tools_response and not tools_response.error:
            tools = tools_response.result.get("tools", [])
            for tool in tools:
                tool_key = f"{server_name}:{tool['name']}"
                self.available_tools[tool_key] = {"server": server_name, "tool": tool}
            logger.info(f"Discovered {len(tools)} tools from {server_name}")

        # Discover resources
        resources_request = MCPMessage(
            id=str(uuid.uuid4()),
            message_type=MCPMessageType.REQUEST,
            method="resources/list",
        )

        resources_response = await self._send_request(server_name, resources_request)
        if resources_response and not resources_response.error:
            resources = resources_response.result.get("resources", [])
            for resource in resources:
                resource_key = f"{server_name}:{resource['uri']}"
                self.available_resources[resource_key] = {
                    "server": server_name,
                    "resource": resource,
                }
            logger.info(f"Discovered {len(resources)} resources from {server_name}")

    async def _send_request(
        self, server_name: str, message: MCPMessage
    ) -> Optional[MCPMessage]:
        """Send request to MCP server"""
        connection = self.connections.get(server_name)
        if not connection:
            logger.error(f"No connection to server: {server_name}")
            return None

        try:
            if connection.transport == MCPTransport.HTTP:
                return await self._send_http_request(server_name, message)
            elif connection.transport == MCPTransport.WEBSOCKET:
                return await self._send_websocket_request(server_name, message)
        except Exception as e:
            logger.error(f"Error sending request to {server_name}: {str(e)}")
            return None

    async def _send_http_request(
        self, server_name: str, message: MCPMessage
    ) -> Optional[MCPMessage]:
        """Send HTTP request to MCP server"""
        session = self.sessions.get(server_name)
        connection = self.connections.get(server_name)

        if not session or not connection:
            return None

        message_data = {
            "jsonrpc": "2.0",
            "id": message.id,
            "method": message.method,
            "params": message.params,
        }

        async with session.post(connection.url, json=message_data) as response:
            if response.status == 200:
                result = await response.json()
                return MCPMessage(
                    id=result.get("id"),
                    message_type=MCPMessageType.RESPONSE,
                    method=message.method,
                    result=result.get("result"),
                    error=result.get("error"),
                )
            else:
                logger.error(f"HTTP error {response.status} from {server_name}")
                return None

    async def _send_websocket_request(
        self, server_name: str, message: MCPMessage
    ) -> Optional[MCPMessage]:
        """Send WebSocket request to MCP server"""
        websocket = self.websockets.get(server_name)
        if not websocket:
            return None

        message_data = {
            "jsonrpc": "2.0",
            "id": message.id,
            "method": message.method,
            "params": message.params,
        }

        await websocket.send(json.dumps(message_data))
        response_data = await websocket.recv()
        result = json.loads(response_data)

        return MCPMessage(
            id=result.get("id"),
            message_type=MCPMessageType.RESPONSE,
            method=message.method,
            result=result.get("result"),
            error=result.get("error"),
        )

    async def call_tool(
        self, tool_key: str, arguments: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Call a tool on an MCP server"""
        if tool_key not in self.available_tools:
            logger.error(f"Tool not found: {tool_key}")
            return None

        tool_info = self.available_tools[tool_key]
        server_name = tool_info["server"]
        tool_name = tool_info["tool"]["name"]

        request = MCPMessage(
            id=str(uuid.uuid4()),
            message_type=MCPMessageType.REQUEST,
            method="tools/call",
            params={"name": tool_name, "arguments": arguments},
        )

        response = await self._send_request(server_name, request)
        if response and not response.error:
            return response.result
        else:
            logger.error(
                f"Tool call failed for {tool_key}: {response.error if response else 'No response'}"
            )
            return None

    async def read_resource(self, resource_key: str) -> Optional[str]:
        """Read a resource from an MCP server"""
        if resource_key not in self.available_resources:
            logger.error(f"Resource not found: {resource_key}")
            return None

        resource_info = self.available_resources[resource_key]
        server_name = resource_info["server"]
        resource_uri = resource_info["resource"]["uri"]

        request = MCPMessage(
            id=str(uuid.uuid4()),
            message_type=MCPMessageType.REQUEST,
            method="resources/read",
            params={"uri": resource_uri},
        )

        response = await self._send_request(server_name, request)
        if response and not response.error:
            contents = response.result.get("contents", [])
            if contents:
                return contents[0].get("text", "")
        else:
            logger.error(
                f"Resource read failed for {resource_key}: {response.error if response else 'No response'}"
            )

        return None

    async def list_available_tools(self) -> Dict[str, Any]:
        """List all available tools from connected servers"""
        return {
            "total_tools": len(self.available_tools),
            "tools": {
                key: {
                    "name": info["tool"]["name"],
                    "description": info["tool"]["description"],
                    "server": info["server"],
                }
                for key, info in self.available_tools.items()
            },
        }

    async def list_available_resources(self) -> Dict[str, Any]:
        """List all available resources from connected servers"""
        return {
            "total_resources": len(self.available_resources),
            "resources": {
                key: {
                    "uri": info["resource"]["uri"],
                    "name": info["resource"]["name"],
                    "description": info["resource"]["description"],
                    "server": info["server"],
                }
                for key, info in self.available_resources.items()
            },
        }

    async def disconnect_from_server(self, server_name: str):
        """Disconnect from an MCP server"""
        if server_name in self.sessions:
            await self.sessions[server_name].close()
            del self.sessions[server_name]

        if server_name in self.websockets:
            await self.websockets[server_name].close()
            del self.websockets[server_name]

        if server_name in self.connections:
            del self.connections[server_name]

        # Remove tools and resources from this server
        self.available_tools = {
            k: v for k, v in self.available_tools.items() if v["server"] != server_name
        }
        self.available_resources = {
            k: v
            for k, v in self.available_resources.items()
            if v["server"] != server_name
        }

        logger.info(f"Disconnected from MCP server: {server_name}")

    async def disconnect_all(self):
        """Disconnect from all MCP servers"""
        for server_name in list(self.connections.keys()):
            await self.disconnect_from_server(server_name)


# Integration with Kinexus AI Multi-Agent System
class MCPIntegratedAgent:
    """
    Enhanced agent that integrates MCP capabilities
    """

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.mcp_client = MCPClient(f"kinexus-{agent_name}-mcp-client")

    async def initialize_mcp_connections(self, server_configs: List[Dict[str, Any]]):
        """Initialize connections to MCP servers"""
        for config in server_configs:
            connection = MCPServerConnection(
                name=config["name"],
                url=config["url"],
                transport=MCPTransport(config.get("transport", "http")),
                auth_token=config.get("auth_token"),
            )
            await self.mcp_client.connect_to_server(connection)

    async def execute_task_with_mcp(
        self, task_description: str, task_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a task using available MCP tools and resources"""
        logger.info(f"Executing task with MCP integration: {task_description}")

        # Get available tools and resources
        available_tools = await self.mcp_client.list_available_tools()
        available_resources = await self.mcp_client.list_available_resources()

        # Basic task routing based on description
        result = {
            "task_description": task_description,
            "mcp_integration": True,
            "available_tools": available_tools["total_tools"],
            "available_resources": available_resources["total_resources"],
            "execution_result": {},
        }

        # Example: Use documentation analysis tool if available
        doc_analysis_tool = None
        for tool_key, tool_info in available_tools["tools"].items():
            if (
                "analyze" in tool_info["name"].lower()
                or "document" in tool_info["name"].lower()
            ):
                doc_analysis_tool = tool_key
                break

        if doc_analysis_tool and "analyze" in task_description.lower():
            logger.info(f"Using MCP tool for analysis: {doc_analysis_tool}")
            tool_result = await self.mcp_client.call_tool(doc_analysis_tool, task_data)
            result["execution_result"]["mcp_tool_result"] = tool_result

        return result


# Example usage and testing
async def test_mcp_integration():
    """Test MCP integration"""
    logger.info("Testing MCP Integration")

    # Initialize MCP client
    _client = MCPClient()

    # Test connecting to our own MCP server (for self-integration testing)
    _local_connection = MCPServerConnection(
        name="kinexus-local",
        url="http://localhost:8000/mcp",  # Hypothetical local MCP endpoint
        transport=MCPTransport.HTTP,
    )

    # In a real scenario, you would connect to external MCP servers
    # await client.connect_to_server(local_connection)

    logger.info("MCP integration test setup complete")


if __name__ == "__main__":
    asyncio.run(test_mcp_integration())
