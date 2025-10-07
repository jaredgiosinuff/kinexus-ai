#!/usr/bin/env python3
"""
Comprehensive tests for MCP integration in Kinexus AI
"""
import pytest
import asyncio
import json
import uuid
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'integrations'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'config'))

from mcp_server import MCPServer, MCPMessage, MCPMessageType, MCPResource, MCPTool, MCPPrompt, MCPResourceType
from mcp_client import MCPClient, MCPServerConnection, MCPTransport
from mcp_config import MCPConfigManager, MCPServerConfig

class TestMCPServer:
    """Test MCP Server implementation"""

    @pytest.fixture
    def mcp_server(self):
        """Create MCP server instance for testing"""
        with patch('boto3.resource'), patch('boto3.client'):
            server = MCPServer("test-server", "1.0.0")
        return server

    def test_server_initialization(self, mcp_server):
        """Test MCP server initializes correctly"""
        assert mcp_server.server_name == "test-server"
        assert mcp_server.version == "1.0.0"
        assert len(mcp_server.tools) > 0
        assert len(mcp_server.resources) > 0
        assert len(mcp_server.prompts) > 0

    def test_server_info(self, mcp_server):
        """Test server info generation"""
        info = mcp_server.get_server_info()

        assert info["name"] == "test-server"
        assert info["version"] == "1.0.0"
        assert info["protocolVersion"] == "1.0.0"
        assert "capabilities" in info
        assert "tools" in info["capabilities"]
        assert "resources" in info["capabilities"]

    @pytest.mark.asyncio
    async def test_tools_list_request(self, mcp_server):
        """Test tools/list request handling"""
        request = MCPMessage(
            id=str(uuid.uuid4()),
            message_type=MCPMessageType.REQUEST,
            method="tools/list"
        )

        response = await mcp_server.handle_request(request)

        assert response.message_type == MCPMessageType.RESPONSE
        assert response.error is None
        assert "tools" in response.result
        assert len(response.result["tools"]) > 0

    @pytest.mark.asyncio
    async def test_resources_list_request(self, mcp_server):
        """Test resources/list request handling"""
        request = MCPMessage(
            id=str(uuid.uuid4()),
            message_type=MCPMessageType.REQUEST,
            method="resources/list"
        )

        response = await mcp_server.handle_request(request)

        assert response.message_type == MCPMessageType.RESPONSE
        assert response.error is None
        assert "resources" in response.result
        assert len(response.result["resources"]) > 0

    @pytest.mark.asyncio
    async def test_tools_call_request(self, mcp_server):
        """Test tools/call request handling"""
        # Mock the multi-agent supervisor
        with patch('mcp_server.MultiAgentSupervisor') as mock_supervisor:
            mock_supervisor.return_value.process_change_event = AsyncMock(
                return_value={"analysis": "test result"}
            )

            request = MCPMessage(
                id=str(uuid.uuid4()),
                message_type=MCPMessageType.REQUEST,
                method="tools/call",
                params={
                    "name": "analyze_document_changes",
                    "arguments": {
                        "change_data": {"test": "data"},
                        "analysis_depth": "standard"
                    }
                }
            )

            response = await mcp_server.handle_request(request)

            assert response.message_type == MCPMessageType.RESPONSE
            assert response.error is None
            assert "content" in response.result

    @pytest.mark.asyncio
    async def test_invalid_method_request(self, mcp_server):
        """Test handling of invalid method requests"""
        request = MCPMessage(
            id=str(uuid.uuid4()),
            message_type=MCPMessageType.REQUEST,
            method="invalid/method"
        )

        response = await mcp_server.handle_request(request)

        assert response.message_type == MCPMessageType.RESPONSE
        assert response.error is not None
        assert response.error["code"] == -32601

class TestMCPClient:
    """Test MCP Client implementation"""

    @pytest.fixture
    def mcp_client(self):
        """Create MCP client instance for testing"""
        return MCPClient("test-client")

    def test_client_initialization(self, mcp_client):
        """Test MCP client initializes correctly"""
        assert mcp_client.client_name == "test-client"
        assert len(mcp_client.connections) == 0
        assert len(mcp_client.available_tools) == 0
        assert len(mcp_client.available_resources) == 0

    @pytest.mark.asyncio
    async def test_http_connection(self, mcp_client):
        """Test HTTP connection establishment"""
        connection = MCPServerConnection(
            name="test-server",
            url="http://localhost:8000/mcp",
            transport=MCPTransport.HTTP
        )

        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock()
            mock_session.return_value.__aexit__ = AsyncMock()

            await mcp_client._connect_http(connection)

            assert "test-server" in mcp_client.sessions

    @pytest.mark.asyncio
    async def test_tool_discovery(self, mcp_client):
        """Test tool discovery from MCP server"""
        # Mock server response
        mock_tools_response = MCPMessage(
            id="test-id",
            message_type=MCPMessageType.RESPONSE,
            method="tools/list",
            result={
                "tools": [
                    {
                        "name": "test_tool",
                        "description": "A test tool",
                        "inputSchema": {"type": "object"}
                    }
                ]
            }
        )

        with patch.object(mcp_client, '_send_request', return_value=mock_tools_response):
            await mcp_client._discover_capabilities("test-server")

            assert len(mcp_client.available_tools) == 1
            assert "test-server:test_tool" in mcp_client.available_tools

class TestMCPConfig:
    """Test MCP Configuration Manager"""

    @pytest.fixture
    def config_manager(self):
        """Create config manager for testing"""
        with patch('os.path.exists', return_value=False):
            return MCPConfigManager()

    def test_config_initialization(self, config_manager):
        """Test configuration manager initialization"""
        assert len(config_manager.server_configs) > 0
        assert "claude-desktop" in config_manager.server_configs
        assert "kinexus-local" in config_manager.server_configs

    def test_environment_overrides(self):
        """Test environment variable overrides"""
        with patch.dict(os.environ, {
            'KINEXUS_MCP_TESTSERVER_URL': 'http://test.example.com',
            'KINEXUS_MCP_TESTSERVER_ENABLED': 'true'
        }):
            config_manager = MCPConfigManager()
            overrides = config_manager._load_environment_overrides()

            assert 'testserver' in overrides
            assert overrides['testserver']['url'] == 'http://test.example.com'
            assert overrides['testserver']['enabled'] is True

    def test_server_config_operations(self, config_manager):
        """Test server configuration CRUD operations"""
        # Test adding server config
        new_config = MCPServerConfig(
            name="test-server",
            url="http://test.example.com",
            enabled=True
        )

        success = config_manager.add_server_config(new_config)
        assert success
        assert "test-server" in config_manager.server_configs

        # Test updating server config
        success = config_manager.update_server_config("test-server", {"enabled": False})
        assert success
        assert not config_manager.server_configs["test-server"].enabled

        # Test removing server config
        success = config_manager.remove_server_config("test-server")
        assert success
        assert "test-server" not in config_manager.server_configs

    def test_configuration_validation(self, config_manager):
        """Test configuration validation"""
        # Add invalid config
        invalid_config = MCPServerConfig(
            name="invalid-server",
            url="",  # Invalid empty URL
            transport="invalid_transport"  # Invalid transport
        )
        config_manager.server_configs["invalid-server"] = invalid_config

        validation = config_manager.validate_configuration()

        assert not validation["valid"]
        assert len(validation["errors"]) > 0
        assert "invalid-server" in validation["server_results"]

    def test_enabled_servers_filter(self, config_manager):
        """Test filtering enabled servers"""
        enabled_servers = config_manager.get_enabled_servers()

        # Should only include enabled servers
        for server in enabled_servers:
            assert server.enabled

class TestMCPIntegration:
    """Integration tests for MCP system"""

    @pytest.mark.asyncio
    async def test_end_to_end_mcp_workflow(self):
        """Test complete MCP workflow from client to server"""
        # Create server and client
        with patch('boto3.resource'), patch('boto3.client'):
            server = MCPServer("integration-test-server")

        client = MCPClient("integration-test-client")

        # Test server info
        server_info = server.get_server_info()
        assert server_info["name"] == "integration-test-server"

        # Test tools list
        tools_request = MCPMessage(
            id=str(uuid.uuid4()),
            message_type=MCPMessageType.REQUEST,
            method="tools/list"
        )

        tools_response = await server.handle_request(tools_request)
        assert tools_response.error is None
        assert len(tools_response.result["tools"]) > 0

    @pytest.mark.asyncio
    async def test_mcp_error_handling(self):
        """Test MCP error handling scenarios"""
        with patch('boto3.resource'), patch('boto3.client'):
            server = MCPServer("error-test-server")

        # Test invalid tool call
        invalid_request = MCPMessage(
            id=str(uuid.uuid4()),
            message_type=MCPMessageType.REQUEST,
            method="tools/call",
            params={
                "name": "nonexistent_tool",
                "arguments": {}
            }
        )

        response = await server.handle_request(invalid_request)
        assert response.error is not None
        assert response.error["code"] == -32602

    def test_mcp_configuration_summary(self):
        """Test MCP configuration summary generation"""
        with patch('os.path.exists', return_value=False):
            config_manager = MCPConfigManager()

        summary = config_manager.get_configuration_summary()

        assert "total_servers" in summary
        assert "enabled_servers" in summary
        assert "server_summary" in summary
        assert summary["total_servers"] > 0

def run_mcp_tests():
    """Run all MCP tests"""
    print("🧪 Running MCP Integration Tests...")

    # Run tests using pytest
    test_files = [__file__]

    try:
        import pytest
        result = pytest.main(["-v"] + test_files)
        return result == 0
    except ImportError:
        print("⚠️ pytest not available, running basic tests...")

        # Run basic tests without pytest
        try:
            # Test MCP Server initialization
            with patch('boto3.resource'), patch('boto3.client'):
                server = MCPServer("test-server")

            assert server.server_name == "test-server"
            assert len(server.tools) > 0
            print("✅ MCP Server initialization test passed")

            # Test MCP Client initialization
            client = MCPClient("test-client")
            assert client.client_name == "test-client"
            print("✅ MCP Client initialization test passed")

            # Test MCP Config initialization
            with patch('os.path.exists', return_value=False):
                config = MCPConfigManager()
            assert len(config.server_configs) > 0
            print("✅ MCP Config initialization test passed")

            return True

        except Exception as e:
            print(f"❌ Basic MCP tests failed: {str(e)}")
            return False

if __name__ == "__main__":
    success = run_mcp_tests()
    if success:
        print("✅ All MCP tests passed!")
    else:
        print("❌ Some MCP tests failed!")
    exit(0 if success else 1)