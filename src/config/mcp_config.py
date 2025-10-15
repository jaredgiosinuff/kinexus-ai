#!/usr/bin/env python3
"""
MCP Configuration Management for Kinexus AI
Manages MCP server connections and tool registrations
"""
import json
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """MCP Server configuration"""

    name: str
    url: str
    transport: str = "http"
    auth_token: Optional[str] = None
    enabled: bool = True
    timeout: int = 30
    retry_attempts: int = 3
    capabilities: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []
        if self.metadata is None:
            self.metadata = {}


class MCPConfigManager:
    """
    Manages MCP server configurations for Kinexus AI
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._get_default_config_path()
        self.server_configs: Dict[str, MCPServerConfig] = {}
        self.environment_overrides = self._load_environment_overrides()

        # Load configuration
        self._load_configuration()

    def _get_default_config_path(self) -> str:
        """Get default configuration file path"""
        # Look for config in multiple locations
        possible_paths = [
            ".kinexus/mcp-config.yaml",
            "config/mcp-config.yaml",
            "/etc/kinexus/mcp-config.yaml",
            os.path.expanduser("~/.kinexus/mcp-config.yaml"),
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path

        # Return the first path as default (will be created if needed)
        return possible_paths[0]

    def _load_environment_overrides(self) -> Dict[str, Any]:
        """Load MCP configuration from environment variables"""
        overrides = {}

        # Parse environment variables for MCP configuration
        # Format: KINEXUS_MCP_<SERVER_NAME>_<PROPERTY>=value
        for key, value in os.environ.items():
            if key.startswith("KINEXUS_MCP_"):
                parts = key.split("_")[2:]  # Remove KINEXUS_MCP prefix
                if len(parts) >= 2:
                    server_name = parts[0].lower()
                    property_name = "_".join(parts[1:]).lower()

                    if server_name not in overrides:
                        overrides[server_name] = {}

                    # Parse boolean and numeric values
                    if value.lower() in ["true", "false"]:
                        value = value.lower() == "true"
                    elif value.isdigit():
                        value = int(value)

                    overrides[server_name][property_name] = value

        return overrides

    def _load_configuration(self):
        """Load MCP configuration from file and environment"""
        try:
            # Load from file if it exists
            if os.path.exists(self.config_path):
                with open(self.config_path, "r") as f:
                    if self.config_path.endswith(".yaml") or self.config_path.endswith(
                        ".yml"
                    ):
                        config_data = yaml.safe_load(f)
                    else:
                        config_data = json.load(f)

                # Parse server configurations
                servers = config_data.get("mcp_servers", [])
                for server_config in servers:
                    server = MCPServerConfig(**server_config)
                    self.server_configs[server.name] = server

            # Apply environment overrides
            for server_name, overrides in self.environment_overrides.items():
                if server_name in self.server_configs:
                    # Update existing server config
                    for key, value in overrides.items():
                        setattr(self.server_configs[server_name], key, value)
                else:
                    # Create new server config from environment
                    if "url" in overrides:  # URL is required
                        server = MCPServerConfig(
                            name=server_name,
                            url=overrides["url"],
                            **{k: v for k, v in overrides.items() if k != "url"},
                        )
                        self.server_configs[server_name] = server

            logger.info(f"Loaded {len(self.server_configs)} MCP server configurations")

        except Exception as e:
            logger.error(f"Error loading MCP configuration: {str(e)}")
            # Load default configuration
            self._load_default_configuration()

    def _load_default_configuration(self):
        """Load default MCP server configurations"""
        logger.info("Loading default MCP configuration")

        # Default configurations for common MCP servers
        defaults = [
            {
                "name": "claude-desktop",
                "url": "http://localhost:3000/mcp",
                "transport": "http",
                "enabled": False,  # Disabled by default, enable via config
                "capabilities": ["tools", "resources", "prompts"],
                "metadata": {
                    "description": "Claude Desktop MCP server",
                    "provider": "Anthropic",
                },
            },
            {
                "name": "kinexus-local",
                "url": "http://localhost:8000/mcp",
                "transport": "http",
                "enabled": True,
                "capabilities": ["tools", "resources"],
                "metadata": {
                    "description": "Kinexus AI local MCP server",
                    "provider": "Kinexus AI",
                },
            },
        ]

        for config in defaults:
            server = MCPServerConfig(**config)
            self.server_configs[server.name] = server

    def get_enabled_servers(self) -> List[MCPServerConfig]:
        """Get list of enabled MCP servers"""
        return [server for server in self.server_configs.values() if server.enabled]

    def get_server_config(self, server_name: str) -> Optional[MCPServerConfig]:
        """Get configuration for a specific server"""
        return self.server_configs.get(server_name)

    def add_server_config(self, server_config: MCPServerConfig) -> bool:
        """Add a new server configuration"""
        try:
            self.server_configs[server_config.name] = server_config
            logger.info(f"Added MCP server configuration: {server_config.name}")
            return True
        except Exception as e:
            logger.error(f"Error adding server configuration: {str(e)}")
            return False

    def remove_server_config(self, server_name: str) -> bool:
        """Remove a server configuration"""
        if server_name in self.server_configs:
            del self.server_configs[server_name]
            logger.info(f"Removed MCP server configuration: {server_name}")
            return True
        return False

    def update_server_config(self, server_name: str, updates: Dict[str, Any]) -> bool:
        """Update a server configuration"""
        if server_name in self.server_configs:
            server = self.server_configs[server_name]
            for key, value in updates.items():
                if hasattr(server, key):
                    setattr(server, key, value)
            logger.info(f"Updated MCP server configuration: {server_name}")
            return True
        return False

    def save_configuration(self) -> bool:
        """Save current configuration to file"""
        try:
            # Create directory if it doesn't exist
            config_dir = os.path.dirname(self.config_path)
            if config_dir:
                os.makedirs(config_dir, exist_ok=True)

            # Prepare configuration data
            config_data = {
                "version": "1.0.0",
                "description": "Kinexus AI MCP Server Configuration",
                "mcp_servers": [
                    asdict(server) for server in self.server_configs.values()
                ],
            }

            # Save to file
            with open(self.config_path, "w") as f:
                if self.config_path.endswith(".yaml") or self.config_path.endswith(
                    ".yml"
                ):
                    yaml.dump(config_data, f, default_flow_style=False, indent=2)
                else:
                    json.dump(config_data, f, indent=2)

            logger.info(f"Saved MCP configuration to: {self.config_path}")
            return True

        except Exception as e:
            logger.error(f"Error saving MCP configuration: {str(e)}")
            return False

    def validate_configuration(self) -> Dict[str, Any]:
        """Validate MCP server configurations"""
        validation_results = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "server_results": {},
        }

        for server_name, server in self.server_configs.items():
            server_validation = {"valid": True, "warnings": [], "errors": []}

            # Validate required fields
            if not server.url:
                server_validation["errors"].append("URL is required")
                server_validation["valid"] = False

            # Validate URL format
            if server.url and not (
                server.url.startswith("http://") or server.url.startswith("https://")
            ):
                server_validation["warnings"].append(
                    "URL should start with http:// or https://"
                )

            # Validate transport
            if server.transport not in ["http", "websocket", "stdio"]:
                server_validation["errors"].append(
                    f"Invalid transport: {server.transport}"
                )
                server_validation["valid"] = False

            # Validate timeout
            if server.timeout <= 0:
                server_validation["warnings"].append("Timeout should be greater than 0")

            validation_results["server_results"][server_name] = server_validation

            if not server_validation["valid"]:
                validation_results["valid"] = False
                validation_results["errors"].extend(
                    [f"{server_name}: {error}" for error in server_validation["errors"]]
                )

            validation_results["warnings"].extend(
                [
                    f"{server_name}: {warning}"
                    for warning in server_validation["warnings"]
                ]
            )

        return validation_results

    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get summary of current MCP configuration"""
        enabled_servers = self.get_enabled_servers()

        return {
            "total_servers": len(self.server_configs),
            "enabled_servers": len(enabled_servers),
            "config_path": self.config_path,
            "environment_overrides": len(self.environment_overrides),
            "server_summary": {
                server.name: {
                    "enabled": server.enabled,
                    "transport": server.transport,
                    "capabilities": server.capabilities,
                }
                for server in self.server_configs.values()
            },
        }

    def create_sample_config(self, output_path: str) -> bool:
        """Create a sample configuration file"""
        try:
            sample_config = {
                "version": "1.0.0",
                "description": "Kinexus AI MCP Server Configuration",
                "mcp_servers": [
                    {
                        "name": "claude-desktop",
                        "url": "http://localhost:3000/mcp",
                        "transport": "http",
                        "enabled": True,
                        "timeout": 30,
                        "retry_attempts": 3,
                        "capabilities": ["tools", "resources", "prompts"],
                        "metadata": {
                            "description": "Claude Desktop MCP server",
                            "provider": "Anthropic",
                            "documentation": "https://docs.claude.com/mcp",
                        },
                    },
                    {
                        "name": "github-integration",
                        "url": "https://api.github.com/mcp",
                        "transport": "http",
                        "auth_token": "${GITHUB_MCP_TOKEN}",
                        "enabled": False,
                        "timeout": 45,
                        "retry_attempts": 5,
                        "capabilities": ["tools", "resources"],
                        "metadata": {
                            "description": "GitHub MCP integration",
                            "provider": "GitHub",
                            "documentation": "https://docs.github.com/mcp",
                        },
                    },
                ],
            }

            with open(output_path, "w") as f:
                if output_path.endswith(".yaml") or output_path.endswith(".yml"):
                    yaml.dump(sample_config, f, default_flow_style=False, indent=2)
                else:
                    json.dump(sample_config, f, indent=2)

            logger.info(f"Created sample MCP configuration: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error creating sample configuration: {str(e)}")
            return False


# Global configuration instance
_config_manager = None


def get_mcp_config() -> MCPConfigManager:
    """Get global MCP configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = MCPConfigManager()
    return _config_manager


# Example usage
if __name__ == "__main__":
    # Test configuration management
    config_manager = MCPConfigManager()

    # Print configuration summary
    summary = config_manager.get_configuration_summary()
    print("MCP Configuration Summary:")
    print(json.dumps(summary, indent=2))

    # Create sample configuration
    config_manager.create_sample_config("sample-mcp-config.yaml")

    # Validate configuration
    validation = config_manager.validate_configuration()
    print("\nValidation Results:")
    print(json.dumps(validation, indent=2))
