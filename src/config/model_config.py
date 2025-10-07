#!/usr/bin/env python3
"""
Model Configuration Manager for Kinexus AI
Manages AWS Bedrock model assignments and fallback strategies
"""
import os
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class ModelCapability(Enum):
    """Model capabilities"""
    TEXT_GENERATION = "text_generation"
    IMAGE_ANALYSIS = "image_analysis"
    REASONING = "reasoning"
    CODING = "coding"
    FAST_PROCESSING = "fast_processing"
    HIGH_QUALITY = "high_quality"
    MULTIMODAL = "multimodal"

class ModelProvider(Enum):
    """Model providers"""
    ANTHROPIC = "anthropic"
    AMAZON = "amazon"
    META = "meta"
    COHERE = "cohere"

@dataclass
class ModelConfig:
    """Configuration for a specific model"""
    model_id: str
    provider: ModelProvider
    capabilities: List[ModelCapability]
    context_length: int
    cost_per_token: float
    availability_regions: List[str]
    is_available: bool = True
    fallback_model: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class ModelConfigManager:
    """
    Manages model configurations and provides intelligent model selection
    """

    def __init__(self, region: str = "us-east-1"):
        self.region = region
        self.bedrock = boto3.client('bedrock', region_name=region)

        # Initialize model catalog
        self.models: Dict[str, ModelConfig] = {}
        self.load_model_catalog()

        # Check model availability
        self.check_model_availability()

    def load_model_catalog(self):
        """Load the catalog of available models"""
        # Latest Claude models (September 2025)
        claude_models = {
            "anthropic.claude-sonnet-4-5-v2:0": ModelConfig(
                model_id="anthropic.claude-sonnet-4-5-v2:0",
                provider=ModelProvider.ANTHROPIC,
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.REASONING,
                    ModelCapability.CODING,
                    ModelCapability.HIGH_QUALITY
                ],
                context_length=1000000,  # 1M tokens
                cost_per_token=0.000015,  # Estimated
                availability_regions=["us-east-1", "us-west-2", "eu-west-1"],
                fallback_model="anthropic.claude-sonnet-4-v1:0",
                metadata={
                    "release_date": "2025-09-29",
                    "best_for": "complex reasoning, autonomous agents, coding",
                    "performance_tier": "premium"
                }
            ),
            "anthropic.claude-sonnet-4-v1:0": ModelConfig(
                model_id="anthropic.claude-sonnet-4-v1:0",
                provider=ModelProvider.ANTHROPIC,
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.REASONING,
                    ModelCapability.CODING
                ],
                context_length=1000000,
                cost_per_token=0.000012,
                availability_regions=["us-east-1", "us-west-2", "eu-west-1"],
                fallback_model="anthropic.claude-3-5-sonnet-20241022-v2:0",
                metadata={
                    "release_date": "2025-05-01",
                    "best_for": "balanced performance and cost",
                    "performance_tier": "standard"
                }
            ),
            "anthropic.claude-opus-4-1-v1:0": ModelConfig(
                model_id="anthropic.claude-opus-4-1-v1:0",
                provider=ModelProvider.ANTHROPIC,
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.REASONING,
                    ModelCapability.CODING,
                    ModelCapability.HIGH_QUALITY
                ],
                context_length=1000000,
                cost_per_token=0.000030,
                availability_regions=["us-east-1", "us-west-2"],
                fallback_model="anthropic.claude-sonnet-4-5-v2:0",
                metadata={
                    "release_date": "2025-08-05",
                    "best_for": "maximum accuracy, complex analysis",
                    "performance_tier": "premium"
                }
            ),
            # Legacy Claude models for fallback
            "anthropic.claude-3-5-sonnet-20241022-v2:0": ModelConfig(
                model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
                provider=ModelProvider.ANTHROPIC,
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.REASONING
                ],
                context_length=200000,
                cost_per_token=0.000008,
                availability_regions=["us-east-1", "us-west-2", "eu-west-1"],
                fallback_model="anthropic.claude-3-haiku-20240307-v1:0",
                metadata={
                    "release_date": "2024-10-22",
                    "best_for": "legacy support",
                    "performance_tier": "legacy"
                }
            )
        }

        # Amazon Nova models
        nova_models = {
            "amazon.nova-pro-v1:0": ModelConfig(
                model_id="amazon.nova-pro-v1:0",
                provider=ModelProvider.AMAZON,
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.IMAGE_ANALYSIS,
                    ModelCapability.MULTIMODAL,
                    ModelCapability.REASONING
                ],
                context_length=300000,
                cost_per_token=0.000008,
                availability_regions=["us-east-1", "us-west-2"],
                fallback_model="amazon.nova-lite-v1:0",
                metadata={
                    "release_date": "2024-12-03",
                    "best_for": "multimodal analysis, image processing",
                    "performance_tier": "multimodal"
                }
            ),
            "amazon.nova-lite-v1:0": ModelConfig(
                model_id="amazon.nova-lite-v1:0",
                provider=ModelProvider.AMAZON,
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.IMAGE_ANALYSIS,
                    ModelCapability.MULTIMODAL,
                    ModelCapability.FAST_PROCESSING
                ],
                context_length=300000,
                cost_per_token=0.000003,
                availability_regions=["us-east-1", "us-west-2", "us-east-2"],
                metadata={
                    "release_date": "2024-12-03",
                    "best_for": "fast multimodal processing",
                    "performance_tier": "fast"
                }
            ),
            "amazon.nova-micro-v1:0": ModelConfig(
                model_id="amazon.nova-micro-v1:0",
                provider=ModelProvider.AMAZON,
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.FAST_PROCESSING
                ],
                context_length=128000,
                cost_per_token=0.000001,
                availability_regions=["us-east-1", "us-west-2", "us-east-2"],
                metadata={
                    "release_date": "2024-12-03",
                    "best_for": "lightweight tasks, high volume",
                    "performance_tier": "ultra_fast"
                }
            )
        }

        # Combine all models
        self.models.update(claude_models)
        self.models.update(nova_models)

        logger.info(f"Loaded {len(self.models)} models into catalog")

    def check_model_availability(self):
        """Check which models are actually available in the current region"""
        try:
            # Get list of foundation models from Bedrock
            response = self.bedrock.list_foundation_models()
            available_model_ids = {model['modelId'] for model in response['modelSummaries']}

            # Update availability status
            for model_id, config in self.models.items():
                config.is_available = model_id in available_model_ids

            available_count = sum(1 for m in self.models.values() if m.is_available)
            logger.info(f"Found {available_count}/{len(self.models)} models available in {self.region}")

        except Exception as e:
            logger.warning(f"Could not check model availability: {str(e)}")
            # Assume all models are available if we can't check
            for config in self.models.values():
                config.is_available = True

    def get_best_model_for_task(self, required_capabilities: List[ModelCapability],
                              performance_preference: str = "balanced") -> Optional[str]:
        """
        Get the best model for a specific task

        Args:
            required_capabilities: List of required capabilities
            performance_preference: "fast", "balanced", "premium", "cost_optimized"
        """
        # Filter models by capabilities and availability
        suitable_models = []
        for model_id, config in self.models.items():
            if not config.is_available:
                continue

            # Check if model has all required capabilities
            if all(cap in config.capabilities for cap in required_capabilities):
                suitable_models.append((model_id, config))

        if not suitable_models:
            logger.warning(f"No suitable models found for capabilities: {required_capabilities}")
            return None

        # Sort by preference
        if performance_preference == "fast":
            # Prefer models with fast processing capability and lower cost
            suitable_models.sort(key=lambda x: (
                ModelCapability.FAST_PROCESSING in x[1].capabilities,
                -x[1].cost_per_token
            ), reverse=True)
        elif performance_preference == "premium":
            # Prefer high-quality models regardless of cost
            suitable_models.sort(key=lambda x: (
                ModelCapability.HIGH_QUALITY in x[1].capabilities,
                x[1].context_length,
                -x[1].cost_per_token
            ), reverse=True)
        elif performance_preference == "cost_optimized":
            # Prefer lowest cost models
            suitable_models.sort(key=lambda x: x[1].cost_per_token)
        else:  # balanced
            # Balance between quality and cost
            suitable_models.sort(key=lambda x: (
                ModelCapability.HIGH_QUALITY in x[1].capabilities,
                x[1].context_length,
                -x[1].cost_per_token * 0.5  # Weight cost less heavily
            ), reverse=True)

        return suitable_models[0][0]

    def get_model_with_fallback(self, preferred_model_id: str) -> str:
        """Get model with fallback if preferred model is not available"""
        preferred_config = self.models.get(preferred_model_id)

        if preferred_config and preferred_config.is_available:
            return preferred_model_id

        # Try fallback model
        if preferred_config and preferred_config.fallback_model:
            fallback_config = self.models.get(preferred_config.fallback_model)
            if fallback_config and fallback_config.is_available:
                logger.info(f"Using fallback model {preferred_config.fallback_model} for {preferred_model_id}")
                return preferred_config.fallback_model

        # Find best available model with similar capabilities
        if preferred_config:
            alternative = self.get_best_model_for_task(preferred_config.capabilities)
            if alternative:
                logger.info(f"Using alternative model {alternative} for {preferred_model_id}")
                return alternative

        # Last resort: return any available model
        for model_id, config in self.models.items():
            if config.is_available:
                logger.warning(f"Using last resort model {model_id} for {preferred_model_id}")
                return model_id

        raise RuntimeError(f"No available models found in region {self.region}")

    def get_recommended_models_for_agents(self) -> Dict[str, str]:
        """Get recommended model assignments for different agent roles"""
        recommendations = {}

        # Supervisor - needs best reasoning
        supervisor_model = self.get_best_model_for_task(
            [ModelCapability.REASONING, ModelCapability.HIGH_QUALITY],
            "premium"
        )
        recommendations["supervisor"] = supervisor_model or "anthropic.claude-sonnet-4-5-v2:0"

        # Change Analyzer - needs balanced performance
        analyzer_model = self.get_best_model_for_task(
            [ModelCapability.TEXT_GENERATION, ModelCapability.REASONING],
            "balanced"
        )
        recommendations["change_analyzer"] = analyzer_model or "anthropic.claude-sonnet-4-v1:0"

        # Content Creator - needs high quality
        creator_model = self.get_best_model_for_task(
            [ModelCapability.TEXT_GENERATION, ModelCapability.HIGH_QUALITY],
            "premium"
        )
        recommendations["content_creator"] = creator_model or "anthropic.claude-sonnet-4-5-v2:0"

        # Quality Controller - needs high quality
        quality_model = self.get_best_model_for_task(
            [ModelCapability.REASONING, ModelCapability.HIGH_QUALITY],
            "premium"
        )
        recommendations["quality_controller"] = quality_model or "anthropic.claude-sonnet-4-5-v2:0"

        # Platform Updater - needs speed
        updater_model = self.get_best_model_for_task(
            [ModelCapability.TEXT_GENERATION],
            "fast"
        )
        recommendations["platform_updater"] = updater_model or "anthropic.claude-sonnet-4-v1:0"

        # Image Analysis - needs multimodal
        image_model = self.get_best_model_for_task(
            [ModelCapability.IMAGE_ANALYSIS, ModelCapability.MULTIMODAL],
            "balanced"
        )
        recommendations["image_analyzer"] = image_model or "amazon.nova-pro-v1:0"

        return recommendations

    def get_model_info(self, model_id: str) -> Optional[ModelConfig]:
        """Get information about a specific model"""
        return self.models.get(model_id)

    def list_available_models(self) -> List[str]:
        """List all available models in current region"""
        return [model_id for model_id, config in self.models.items() if config.is_available]

    def get_model_summary(self) -> Dict[str, Any]:
        """Get summary of model availability and recommendations"""
        available_models = self.list_available_models()
        recommendations = self.get_recommended_models_for_agents()

        return {
            "region": self.region,
            "total_models": len(self.models),
            "available_models": len(available_models),
            "recommended_assignments": recommendations,
            "model_providers": {
                provider.value: len([m for m in self.models.values()
                                  if m.provider == provider and m.is_available])
                for provider in ModelProvider
            },
            "capabilities_coverage": {
                cap.value: len([m for m in self.models.values()
                              if cap in m.capabilities and m.is_available])
                for cap in ModelCapability
            }
        }

    def validate_model_configuration(self, agent_assignments: Dict[str, str]) -> Dict[str, Any]:
        """Validate a set of agent model assignments"""
        results = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "recommendations": []
        }

        for agent, model_id in agent_assignments.items():
            config = self.models.get(model_id)

            if not config:
                results["errors"].append(f"Unknown model {model_id} for {agent}")
                results["valid"] = False
                continue

            if not config.is_available:
                results["errors"].append(f"Model {model_id} not available for {agent}")
                results["valid"] = False

                # Suggest alternative
                if config.fallback_model:
                    results["recommendations"].append(
                        f"Use fallback model {config.fallback_model} for {agent}"
                    )

            # Check for cost efficiency
            if config.cost_per_token > 0.000020:  # High cost threshold
                results["warnings"].append(f"High-cost model {model_id} assigned to {agent}")

        return results

# Global model configuration instance
_model_config = None

def get_model_config(region: str = "us-east-1") -> ModelConfigManager:
    """Get global model configuration manager instance"""
    global _model_config
    if _model_config is None or _model_config.region != region:
        _model_config = ModelConfigManager(region)
    return _model_config

# Example usage
if __name__ == "__main__":
    # Test model configuration
    config_manager = ModelConfigManager()

    # Get model summary
    summary = config_manager.get_model_summary()
    print("Model Configuration Summary:")
    print(json.dumps(summary, indent=2))

    # Get recommendations
    recommendations = config_manager.get_recommended_models_for_agents()
    print("\nRecommended Model Assignments:")
    for agent, model in recommendations.items():
        print(f"  {agent}: {model}")

    # Validate configuration
    validation = config_manager.validate_model_configuration(recommendations)
    print("\nConfiguration Validation:")
    print(json.dumps(validation, indent=2))