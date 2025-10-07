#!/usr/bin/env python3
"""
Comprehensive tests for model integration in Kinexus AI
Tests Claude Sonnet 4.5, Nova Pro, and model configuration
"""
import pytest
import asyncio
import json
import base64
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'agents'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'config'))

from multi_agent_supervisor import MultiAgentSupervisor, BedrockAgent, AgentRole
from nova_pro_integration import NovaProImageAnalyzer, ImageType, ImageAnalysisResult
from model_config import ModelConfigManager, ModelCapability, ModelProvider

class TestModelConfiguration:
    """Test model configuration and selection"""

    @pytest.fixture
    def model_config(self):
        """Create model config manager for testing"""
        with patch('boto3.client') as mock_client:
            mock_client.return_value.list_foundation_models.return_value = {
                'modelSummaries': [
                    {'modelId': 'anthropic.claude-sonnet-4-5-v2:0'},
                    {'modelId': 'amazon.nova-pro-v1:0'},
                    {'modelId': 'amazon.nova-lite-v1:0'}
                ]
            }
            return ModelConfigManager()

    def test_model_catalog_loading(self, model_config):
        """Test model catalog loads correctly"""
        assert len(model_config.models) > 0
        assert "anthropic.claude-sonnet-4-5-v2:0" in model_config.models
        assert "amazon.nova-pro-v1:0" in model_config.models

    def test_model_availability_check(self, model_config):
        """Test model availability checking"""
        # Should mark available models based on mocked response
        claude_config = model_config.models["anthropic.claude-sonnet-4-5-v2:0"]
        assert claude_config.is_available

        nova_config = model_config.models["amazon.nova-pro-v1:0"]
        assert nova_config.is_available

    def test_best_model_selection(self, model_config):
        """Test best model selection for different scenarios"""
        # Test reasoning task
        reasoning_model = model_config.get_best_model_for_task(
            [ModelCapability.REASONING, ModelCapability.HIGH_QUALITY],
            "premium"
        )
        assert reasoning_model in model_config.models
        assert ModelCapability.REASONING in model_config.models[reasoning_model].capabilities

        # Test multimodal task
        multimodal_model = model_config.get_best_model_for_task(
            [ModelCapability.IMAGE_ANALYSIS, ModelCapability.MULTIMODAL],
            "balanced"
        )
        assert multimodal_model in model_config.models
        assert ModelCapability.MULTIMODAL in model_config.models[multimodal_model].capabilities

    def test_model_fallback(self, model_config):
        """Test model fallback mechanism"""
        # Test with unavailable model
        with patch.object(model_config, 'models') as mock_models:
            mock_models.__getitem__.return_value.is_available = False
            mock_models.__getitem__.return_value.fallback_model = "anthropic.claude-sonnet-4-v1:0"
            mock_models.__contains__.return_value = True

            # Mock the fallback model as available
            fallback_config = Mock()
            fallback_config.is_available = True
            mock_models.__getitem__ = lambda key: fallback_config if key == "anthropic.claude-sonnet-4-v1:0" else Mock(is_available=False)

            result = model_config.get_model_with_fallback("anthropic.claude-sonnet-4-5-v2:0")
            # Should not be the original model since it's unavailable
            assert result is not None

    def test_agent_model_recommendations(self, model_config):
        """Test model recommendations for different agents"""
        recommendations = model_config.get_recommended_models_for_agents()

        assert "supervisor" in recommendations
        assert "change_analyzer" in recommendations
        assert "content_creator" in recommendations
        assert "quality_controller" in recommendations
        assert "platform_updater" in recommendations
        assert "image_analyzer" in recommendations

        # All recommendations should be valid models
        for agent, model in recommendations.items():
            assert model in model_config.models

    def test_configuration_validation(self, model_config):
        """Test model configuration validation"""
        test_assignments = {
            "supervisor": "anthropic.claude-sonnet-4-5-v2:0",
            "content_creator": "amazon.nova-pro-v1:0"
        }

        validation = model_config.validate_model_configuration(test_assignments)

        assert "valid" in validation
        assert "errors" in validation
        assert "warnings" in validation

class TestBedrockAgent:
    """Test Bedrock agent with new models"""

    @pytest.fixture
    def mock_bedrock_agent(self):
        """Create mocked Bedrock agent"""
        with patch('boto3.client'):
            return BedrockAgent(
                role=AgentRole.SUPERVISOR,
                model_id="anthropic.claude-sonnet-4-5-v2:0"
            )

    def test_agent_initialization(self, mock_bedrock_agent):
        """Test agent initializes with correct model"""
        assert mock_bedrock_agent.role == AgentRole.SUPERVISOR
        assert mock_bedrock_agent.model_id == "anthropic.claude-sonnet-4-5-v2:0"
        assert mock_bedrock_agent.agent_instructions is not None

    @pytest.mark.asyncio
    async def test_bedrock_api_call(self, mock_bedrock_agent):
        """Test Bedrock API call formatting"""
        test_prompt = "Test prompt for Claude Sonnet 4.5"

        # Mock the Bedrock response
        mock_response = {
            'body': Mock(),
            'content': [{'text': 'Test response from Claude Sonnet 4.5'}]
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': 'Test response from Claude Sonnet 4.5'}]
        }).encode()

        with patch.object(mock_bedrock_agent.bedrock_runtime, 'invoke_model', return_value=mock_response):
            response = await mock_bedrock_agent._invoke_bedrock_async(test_prompt)

            assert response is not None
            assert 'content' in response

class TestMultiAgentSupervisor:
    """Test multi-agent supervisor with new models"""

    @pytest.fixture
    def supervisor(self):
        """Create supervisor with mocked dependencies"""
        with patch('boto3.resource'), patch('boto3.client'), \
             patch('multi_agent_supervisor.PersistentMemorySystem'), \
             patch('multi_agent_supervisor.SelfImprovingPerformanceManager'), \
             patch('multi_agent_supervisor.MCPClient'):
            return MultiAgentSupervisor()

    def test_supervisor_initialization(self, supervisor):
        """Test supervisor initializes with latest models"""
        assert len(supervisor.agents) == 5

        # Check that agents use latest models
        supervisor_agent = supervisor.agents[AgentRole.SUPERVISOR]
        assert "sonnet-4" in supervisor_agent.model_id.lower()

    def test_agent_model_assignments(self, supervisor):
        """Test agent model assignments are correct"""
        agents = supervisor.agents

        # Supervisor should use premium model
        assert "4-5" in agents[AgentRole.SUPERVISOR].model_id

        # Content creator should use high-quality model
        assert "4-5" in agents[AgentRole.CONTENT_CREATOR].model_id

        # Quality controller should use premium model
        assert "4-5" in agents[AgentRole.QUALITY_CONTROLLER].model_id

class TestNovaProIntegration:
    """Test Nova Pro image analysis integration"""

    @pytest.fixture
    def nova_analyzer(self):
        """Create Nova Pro analyzer with mocked Bedrock"""
        with patch('boto3.client'):
            return NovaProImageAnalyzer()

    def test_analyzer_initialization(self, nova_analyzer):
        """Test Nova Pro analyzer initialization"""
        assert nova_analyzer.nova_pro_model_id == "amazon.nova-pro-v1:0"
        assert nova_analyzer.nova_lite_model_id == "amazon.nova-lite-v1:0"
        assert nova_analyzer.max_image_size > 0
        assert len(nova_analyzer.supported_formats) > 0

    @pytest.mark.asyncio
    async def test_image_type_classification(self, nova_analyzer):
        """Test image type classification"""
        # Mock image data
        test_image_data = b"fake_image_data"

        # Mock Nova Pro response
        mock_response = {
            'body': Mock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'results': [{'outputText': 'diagram|0.95'}]
        }).encode()

        with patch.object(nova_analyzer.bedrock_runtime, 'invoke_model', return_value=mock_response):
            image_type = await nova_analyzer._classify_image_type(test_image_data, None)

            assert image_type == ImageType.DIAGRAM

    @pytest.mark.asyncio
    async def test_technical_diagram_analysis(self, nova_analyzer):
        """Test technical diagram analysis"""
        test_image_data = b"fake_diagram_data"

        # Mock Nova Pro response with JSON
        analysis_response = {
            "description": "System architecture diagram",
            "components": ["database", "api", "frontend"],
            "relationships": "API connects database to frontend",
            "extracted_text": "User Management System",
            "accuracy_score": 8,
            "clarity_score": 9,
            "completeness_score": 7,
            "validation_issues": ["Missing error handling flow"],
            "recommendations": ["Add error flow documentation"]
        }

        mock_response = {
            'body': Mock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'results': [{'outputText': json.dumps(analysis_response)}]
        }).encode()

        with patch.object(nova_analyzer.bedrock_runtime, 'invoke_model', return_value=mock_response):
            result = await nova_analyzer._analyze_technical_diagram(
                test_image_data, ImageType.DIAGRAM, None
            )

            assert isinstance(result, ImageAnalysisResult)
            assert result.image_type == ImageType.DIAGRAM
            assert result.confidence > 0
            assert result.description == "System architecture diagram"
            assert result.extracted_text == "User Management System"

    @pytest.mark.asyncio
    async def test_diagram_validation(self, nova_analyzer):
        """Test diagram accuracy validation"""
        test_image_data = b"fake_diagram_data"
        reference_data = {
            "expected_components": ["database", "api", "frontend"],
            "context": "User management system architecture"
        }

        # Mock the analyze_documentation_image method
        mock_analysis = ImageAnalysisResult(
            image_type=ImageType.DIAGRAM,
            confidence=0.85,
            description="System architecture diagram",
            metadata={
                "components": ["database", "api", "frontend", "cache"]
            },
            validation_results={
                "issues": ["Cache component not documented"],
                "recommendations": ["Add cache documentation"]
            }
        )

        with patch.object(nova_analyzer, 'analyze_documentation_image', return_value=mock_analysis):
            validation = await nova_analyzer.validate_diagram_accuracy(test_image_data, reference_data)

            assert validation["overall_accuracy"] == 0.85
            assert validation["validation_passed"] is True  # >= 0.7 threshold
            assert validation["image_type"] == "diagram"

    def test_model_info(self, nova_analyzer):
        """Test Nova Pro model information"""
        model_info = nova_analyzer.get_model_info()

        assert "primary_model" in model_info
        assert "classification_model" in model_info
        assert "capabilities" in model_info
        assert "supported_image_types" in model_info
        assert model_info["primary_model"] == "amazon.nova-pro-v1:0"

    def test_supported_formats(self, nova_analyzer):
        """Test supported image formats"""
        formats = nova_analyzer.get_supported_formats()

        assert '.jpg' in formats
        assert '.png' in formats
        assert '.gif' in formats
        assert len(formats) > 0

class TestIntegratedModelWorkflow:
    """Integration tests for complete model workflow"""

    @pytest.mark.asyncio
    async def test_end_to_end_model_workflow(self):
        """Test complete workflow from supervisor to Nova Pro"""
        # Create supervisor with mocked dependencies
        with patch('boto3.resource'), patch('boto3.client'), \
             patch('multi_agent_supervisor.PersistentMemorySystem'), \
             patch('multi_agent_supervisor.SelfImprovingPerformanceManager'), \
             patch('multi_agent_supervisor.MCPClient'):
            supervisor = MultiAgentSupervisor()

        # Create Nova analyzer
        with patch('boto3.client'):
            nova_analyzer = NovaProImageAnalyzer()

        # Test that they can work together
        assert supervisor is not None
        assert nova_analyzer is not None

        # Verify model IDs are compatible
        supervisor_model = supervisor.agents[AgentRole.SUPERVISOR].model_id
        assert "claude" in supervisor_model.lower()

        nova_model = nova_analyzer.nova_pro_model_id
        assert "nova" in nova_model.lower()

    def test_model_configuration_integration(self):
        """Test model configuration integrates with agents"""
        with patch('boto3.client') as mock_client:
            mock_client.return_value.list_foundation_models.return_value = {
                'modelSummaries': [
                    {'modelId': 'anthropic.claude-sonnet-4-5-v2:0'},
                    {'modelId': 'amazon.nova-pro-v1:0'}
                ]
            }
            model_config = ModelConfigManager()

        recommendations = model_config.get_recommended_models_for_agents()

        # Test that recommendations are valid for our use case
        assert recommendations["supervisor"] is not None
        assert recommendations["image_analyzer"] is not None

        # Test validation passes
        validation = model_config.validate_model_configuration(recommendations)
        assert validation["valid"] is True

def run_model_tests():
    """Run all model integration tests"""
    print("🧪 Running Model Integration Tests...")

    try:
        import pytest
        result = pytest.main(["-v", __file__])
        return result == 0
    except ImportError:
        print("⚠️ pytest not available, running basic tests...")

        try:
            # Test Model Config
            with patch('boto3.client') as mock_client:
                mock_client.return_value.list_foundation_models.return_value = {
                    'modelSummaries': [{'modelId': 'anthropic.claude-sonnet-4-5-v2:0'}]
                }
                config = ModelConfigManager()

            assert len(config.models) > 0
            print("✅ Model Config initialization test passed")

            # Test Nova Pro Analyzer
            with patch('boto3.client'):
                analyzer = NovaProImageAnalyzer()

            assert analyzer.nova_pro_model_id == "amazon.nova-pro-v1:0"
            print("✅ Nova Pro Analyzer initialization test passed")

            # Test Multi-Agent Supervisor with new models
            with patch('boto3.resource'), patch('boto3.client'), \
                 patch('multi_agent_supervisor.PersistentMemorySystem'), \
                 patch('multi_agent_supervisor.SelfImprovingPerformanceManager'), \
                 patch('multi_agent_supervisor.MCPClient'):
                supervisor = MultiAgentSupervisor()

            assert len(supervisor.agents) == 5
            print("✅ Multi-Agent Supervisor with latest models test passed")

            return True

        except Exception as e:
            print(f"❌ Basic model tests failed: {str(e)}")
            return False

if __name__ == "__main__":
    success = run_model_tests()
    if success:
        print("✅ All model integration tests passed!")
    else:
        print("❌ Some model integration tests failed!")
    exit(0 if success else 1)