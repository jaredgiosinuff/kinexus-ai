#!/usr/bin/env python3
"""
Configuration management for Self-Corrective RAG (CRAG) system
"""
import json
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class CRAGMode(Enum):
    """Operating modes for CRAG system"""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class QualityProfile(Enum):
    """Predefined quality profiles"""

    FAST = "fast"  # Fast processing, lower quality thresholds
    BALANCED = "balanced"  # Balanced speed and quality
    THOROUGH = "thorough"  # Highest quality, slower processing


@dataclass
class CRAGSystemConfig:
    """Main configuration for CRAG system"""

    # Core CRAG settings
    quality_threshold: float = 0.75
    max_iterations: int = 3
    improvement_threshold: float = 0.05

    # Processing settings
    parallel_processing_limit: int = 5
    processing_timeout_seconds: int = 300

    # Model settings
    primary_model: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    assessment_model: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    fallback_model: str = "anthropic.claude-3-haiku-20240307-v1:0"

    # Feature flags
    enable_metrics_collection: bool = True
    enable_learning_feedback: bool = True
    enable_cross_validation: bool = True
    enable_temporal_validation: bool = True

    # Quality metric weights
    quality_weights: Dict[str, float] = field(
        default_factory=lambda: {
            "relevance": 0.25,
            "accuracy": 0.20,
            "completeness": 0.15,
            "coherence": 0.15,
            "factual_consistency": 0.15,
            "source_reliability": 0.05,
            "temporal_validity": 0.05,
        }
    )

    # Correction settings
    correction_strategies: List[str] = field(
        default_factory=lambda: [
            "retrieve_more",
            "refine_query",
            "validate_sources",
            "cross_reference",
            "fact_check",
            "synthesize_better",
            "temporal_update",
        ]
    )

    # Storage settings
    feedback_table: str = "kinexus-crag-feedback"
    metrics_table: str = "kinexus-crag-metrics"
    cache_table: str = "kinexus-crag-cache"

    # AWS settings
    aws_region: str = "us-east-1"
    bedrock_region: str = "us-east-1"


@dataclass
class DocumentProcessingConfig:
    """Configuration for document processing with CRAG"""

    # Document type specific settings
    max_document_size: int = 1000000  # 1MB
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # Retrieval settings
    default_max_results: int = 10
    min_confidence_threshold: float = 0.6

    # Processing modes per document type
    document_type_configs: Dict[str, Dict[str, Any]] = field(
        default_factory=lambda: {
            "api_docs": {
                "quality_threshold": 0.8,
                "max_iterations": 2,
                "preferred_corrections": ["fact_check", "cross_reference"],
            },
            "user_guides": {
                "quality_threshold": 0.75,
                "max_iterations": 3,
                "preferred_corrections": ["completeness_check", "clarity_improvement"],
            },
            "technical_specs": {
                "quality_threshold": 0.85,
                "max_iterations": 2,
                "preferred_corrections": ["accuracy_validation", "technical_review"],
            },
        }
    )


@dataclass
class PerformanceConfig:
    """Performance and optimization configuration"""

    # Caching settings
    enable_result_caching: bool = True
    cache_ttl_seconds: int = 3600  # 1 hour
    max_cache_entries: int = 10000

    # Rate limiting
    max_requests_per_minute: int = 100
    max_concurrent_requests: int = 20

    # Resource limits
    max_memory_usage_mb: int = 2048
    max_processing_time_seconds: int = 300

    # Optimization settings
    enable_query_optimization: bool = True
    enable_source_deduplication: bool = True
    enable_smart_chunking: bool = True


class CRAGConfigManager:
    """Manages CRAG system configuration across environments"""

    def __init__(
        self,
        mode: CRAGMode = CRAGMode.DEVELOPMENT,
        profile: QualityProfile = QualityProfile.BALANCED,
    ):
        self.mode = mode
        self.profile = profile
        self._config = self._load_config()

    def _load_config(self) -> CRAGSystemConfig:
        """Load configuration based on mode and profile"""

        # Start with base configuration
        config = CRAGSystemConfig()

        # Apply mode-specific settings
        config = self._apply_mode_settings(config)

        # Apply profile-specific settings
        config = self._apply_profile_settings(config)

        # Apply environment variable overrides
        config = self._apply_env_overrides(config)

        return config

    def _apply_mode_settings(self, config: CRAGSystemConfig) -> CRAGSystemConfig:
        """Apply mode-specific configuration"""

        if self.mode == CRAGMode.DEVELOPMENT:
            config.quality_threshold = 0.7  # Lower threshold for faster iteration
            config.max_iterations = 2
            config.enable_metrics_collection = True
            config.parallel_processing_limit = 3

        elif self.mode == CRAGMode.STAGING:
            config.quality_threshold = 0.75
            config.max_iterations = 3
            config.enable_metrics_collection = True
            config.parallel_processing_limit = 5

        elif self.mode == CRAGMode.PRODUCTION:
            config.quality_threshold = 0.8
            config.max_iterations = 3
            config.enable_metrics_collection = True
            config.enable_learning_feedback = True
            config.parallel_processing_limit = 10

        return config

    def _apply_profile_settings(self, config: CRAGSystemConfig) -> CRAGSystemConfig:
        """Apply quality profile settings"""

        if self.profile == QualityProfile.FAST:
            config.quality_threshold = 0.65
            config.max_iterations = 1
            config.improvement_threshold = 0.1
            config.processing_timeout_seconds = 60

        elif self.profile == QualityProfile.BALANCED:
            config.quality_threshold = 0.75
            config.max_iterations = 2
            config.improvement_threshold = 0.05
            config.processing_timeout_seconds = 180

        elif self.profile == QualityProfile.THOROUGH:
            config.quality_threshold = 0.85
            config.max_iterations = 4
            config.improvement_threshold = 0.02
            config.processing_timeout_seconds = 600
            config.enable_cross_validation = True
            config.enable_temporal_validation = True

        return config

    def _apply_env_overrides(self, config: CRAGSystemConfig) -> CRAGSystemConfig:
        """Apply environment variable overrides"""

        # Quality settings
        if os.getenv("CRAG_QUALITY_THRESHOLD"):
            config.quality_threshold = float(os.getenv("CRAG_QUALITY_THRESHOLD"))

        if os.getenv("CRAG_MAX_ITERATIONS"):
            config.max_iterations = int(os.getenv("CRAG_MAX_ITERATIONS"))

        # Model settings
        if os.getenv("CRAG_PRIMARY_MODEL"):
            config.primary_model = os.getenv("CRAG_PRIMARY_MODEL")

        # Feature flags
        if os.getenv("CRAG_ENABLE_METRICS"):
            config.enable_metrics_collection = (
                os.getenv("CRAG_ENABLE_METRICS").lower() == "true"
            )

        if os.getenv("CRAG_ENABLE_LEARNING"):
            config.enable_learning_feedback = (
                os.getenv("CRAG_ENABLE_LEARNING").lower() == "true"
            )

        # AWS settings
        if os.getenv("AWS_DEFAULT_REGION"):
            config.aws_region = os.getenv("AWS_DEFAULT_REGION")
            config.bedrock_region = os.getenv("AWS_DEFAULT_REGION")

        return config

    def get_config(self) -> CRAGSystemConfig:
        """Get the current configuration"""
        return self._config

    def get_document_config(self) -> DocumentProcessingConfig:
        """Get document processing configuration"""
        doc_config = DocumentProcessingConfig()

        # Apply mode-specific document settings
        if self.mode == CRAGMode.DEVELOPMENT:
            doc_config.max_document_size = 500000  # 500KB for dev
            doc_config.default_max_results = 5

        elif self.mode == CRAGMode.PRODUCTION:
            doc_config.max_document_size = 2000000  # 2MB for prod
            doc_config.default_max_results = 15

        return doc_config

    def get_performance_config(self) -> PerformanceConfig:
        """Get performance configuration"""
        perf_config = PerformanceConfig()

        # Apply mode-specific performance settings
        if self.mode == CRAGMode.DEVELOPMENT:
            perf_config.max_requests_per_minute = 50
            perf_config.max_concurrent_requests = 5
            perf_config.enable_result_caching = False  # Disable caching in dev

        elif self.mode == CRAGMode.STAGING:
            perf_config.max_requests_per_minute = 100
            perf_config.max_concurrent_requests = 10

        elif self.mode == CRAGMode.PRODUCTION:
            perf_config.max_requests_per_minute = 500
            perf_config.max_concurrent_requests = 50
            perf_config.enable_query_optimization = True

        return perf_config

    def update_config(self, updates: Dict[str, Any]) -> None:
        """Update configuration with new values"""
        for key, value in updates.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)

    def export_config(self, file_path: str) -> None:
        """Export current configuration to file"""
        config_dict = {
            "mode": self.mode.value,
            "profile": self.profile.value,
            "system_config": self._config.__dict__,
            "document_config": self.get_document_config().__dict__,
            "performance_config": self.get_performance_config().__dict__,
        }

        with open(file_path, "w") as f:
            json.dump(config_dict, f, indent=2, default=str)

    def import_config(self, file_path: str) -> None:
        """Import configuration from file"""
        with open(file_path, "r") as f:
            config_dict = json.load(f)

        # Update mode and profile
        if "mode" in config_dict:
            self.mode = CRAGMode(config_dict["mode"])
        if "profile" in config_dict:
            self.profile = QualityProfile(config_dict["profile"])

        # Update system config
        if "system_config" in config_dict:
            for key, value in config_dict["system_config"].items():
                if hasattr(self._config, key):
                    setattr(self._config, key, value)


# Configuration validation
class CRAGConfigValidator:
    """Validates CRAG configuration for common issues"""

    @staticmethod
    def validate_config(config: CRAGSystemConfig) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []

        # Validate thresholds
        if not 0.0 <= config.quality_threshold <= 1.0:
            issues.append("Quality threshold must be between 0.0 and 1.0")

        if config.improvement_threshold < 0.0:
            issues.append("Improvement threshold must be non-negative")

        # Validate iterations
        if config.max_iterations < 1:
            issues.append("Max iterations must be at least 1")

        if config.max_iterations > 10:
            issues.append("Max iterations should not exceed 10 for performance")

        # Validate parallel processing
        if config.parallel_processing_limit < 1:
            issues.append("Parallel processing limit must be at least 1")

        # Validate timeout
        if config.processing_timeout_seconds < 30:
            issues.append("Processing timeout should be at least 30 seconds")

        # Validate quality weights
        weight_sum = sum(config.quality_weights.values())
        if abs(weight_sum - 1.0) > 0.01:
            issues.append(f"Quality weights should sum to 1.0, got {weight_sum}")

        return issues

    @staticmethod
    def validate_environment() -> List[str]:
        """Validate environment setup for CRAG"""
        issues = []

        # Check AWS credentials
        if not os.getenv("AWS_ACCESS_KEY_ID") and not os.getenv("AWS_PROFILE"):
            issues.append("AWS credentials not configured")

        # Check required environment variables
        required_vars = ["AWS_DEFAULT_REGION"]
        for var in required_vars:
            if not os.getenv(var):
                issues.append(f"Required environment variable {var} not set")

        return issues


# Configuration factory
class CRAGConfigFactory:
    """Factory for creating CRAG configurations"""

    @staticmethod
    def create_development_config() -> CRAGConfigManager:
        """Create development configuration"""
        return CRAGConfigManager(CRAGMode.DEVELOPMENT, QualityProfile.FAST)

    @staticmethod
    def create_staging_config() -> CRAGConfigManager:
        """Create staging configuration"""
        return CRAGConfigManager(CRAGMode.STAGING, QualityProfile.BALANCED)

    @staticmethod
    def create_production_config() -> CRAGConfigManager:
        """Create production configuration"""
        return CRAGConfigManager(CRAGMode.PRODUCTION, QualityProfile.THOROUGH)

    @staticmethod
    def create_custom_config(
        mode: CRAGMode,
        profile: QualityProfile,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> CRAGConfigManager:
        """Create custom configuration"""
        config_manager = CRAGConfigManager(mode, profile)

        if overrides:
            config_manager.update_config(overrides)

        return config_manager


# Example usage
def main():
    """Example configuration usage"""

    # Create development configuration
    config_manager = CRAGConfigFactory.create_development_config()
    config = config_manager.get_config()

    print("CRAG Configuration:")
    print(f"- Mode: {config_manager.mode.value}")
    print(f"- Profile: {config_manager.profile.value}")
    print(f"- Quality Threshold: {config.quality_threshold}")
    print(f"- Max Iterations: {config.max_iterations}")
    print(f"- Primary Model: {config.primary_model}")

    # Validate configuration
    validator = CRAGConfigValidator()
    config_issues = validator.validate_config(config)
    env_issues = validator.validate_environment()

    if config_issues or env_issues:
        print("\nConfiguration Issues:")
        for issue in config_issues + env_issues:
            print(f"- {issue}")
    else:
        print("\n✅ Configuration is valid")

    # Export configuration
    config_manager.export_config("crag_config.json")
    print("\n📄 Configuration exported to crag_config.json")


if __name__ == "__main__":
    main()
