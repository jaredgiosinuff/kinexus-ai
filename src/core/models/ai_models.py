"""
AI Models and Provider System for Kinexus AI
Supports multiple providers and model types with optimized configurations
"""

import asyncio
import json
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Union, AsyncIterator
from dataclasses import dataclass

import boto3
import httpx
from pydantic import BaseModel, Field

from ..config import get_settings


class ModelProvider(Enum):
    """Supported AI model providers"""
    BEDROCK = "bedrock"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE = "azure"
    LOCAL = "local"


class AIModelType(Enum):
    """Supported AI model types"""
    # Claude Models
    CLAUDE_4_OPUS = "claude-4-opus-4.1"
    CLAUDE_4_SONNET = "claude-4-sonnet"
    CLAUDE_3_OPUS = "claude-3-opus-20240229"
    CLAUDE_3_SONNET = "claude-3-sonnet-20240229"
    CLAUDE_3_HAIKU = "claude-3-haiku-20240307"

    # Amazon Nova Models
    NOVA_PRO = "amazon.nova-pro-v1:0"
    NOVA_LITE = "amazon.nova-lite-v1:0"
    NOVA_MICRO = "amazon.nova-micro-v1:0"

    # OpenAI Models
    GPT_4_TURBO = "gpt-4-turbo-preview"
    GPT_4 = "gpt-4"
    GPT_3_5_TURBO = "gpt-3.5-turbo"

    # Local/Custom Models
    LOCAL_MODEL = "local-model"


class ModelCapability(Enum):
    """Model capabilities"""
    TEXT_GENERATION = "text_generation"
    TEXT_ANALYSIS = "text_analysis"
    CODE_GENERATION = "code_generation"
    REASONING = "reasoning"
    MULTIMODAL = "multimodal"
    FUNCTION_CALLING = "function_calling"
    STREAMING = "streaming"
    LARGE_CONTEXT = "large_context"


@dataclass
class ModelLimits:
    """Rate limits and quotas for models"""
    max_tokens_per_request: int = 4000
    max_requests_per_minute: int = 60
    max_tokens_per_minute: int = 40000
    max_context_length: int = 100000
    cost_per_input_token: float = 0.0
    cost_per_output_token: float = 0.0


class ModelResponse(BaseModel):
    """Standardized response from AI models"""
    content: str
    reasoning: Optional[str] = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    usage: Dict[str, int] = Field(default_factory=dict)
    model_used: str = ""
    response_time: float = 0.0
    cost: float = 0.0


class ModelRequest(BaseModel):
    """Standardized request to AI models"""
    prompt: str
    system_prompt: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, gt=0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    stop_sequences: List[str] = Field(default_factory=list)
    stream: bool = False


class BaseModelProvider(ABC):
    """Base class for AI model providers"""

    def __init__(self, provider_type: ModelProvider, config: Dict[str, Any]):
        self.provider_type = provider_type
        self.config = config
        self.settings = get_settings()

    @abstractmethod
    async def generate_response(
        self,
        model_type: AIModelType,
        request: ModelRequest
    ) -> ModelResponse:
        """Generate a response using the specified model"""
        pass

    @abstractmethod
    async def stream_response(
        self,
        model_type: AIModelType,
        request: ModelRequest
    ) -> AsyncIterator[str]:
        """Stream a response using the specified model"""
        pass

    @abstractmethod
    def get_model_limits(self, model_type: AIModelType) -> ModelLimits:
        """Get rate limits and quotas for the specified model"""
        pass

    @abstractmethod
    def get_supported_models(self) -> List[AIModelType]:
        """Get list of supported models for this provider"""
        pass

    @abstractmethod
    def get_model_capabilities(self, model_type: AIModelType) -> List[ModelCapability]:
        """Get capabilities for the specified model"""
        pass


class BedrockProvider(BaseModelProvider):
    """AWS Bedrock model provider"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(ModelProvider.BEDROCK, config)
        self.client = boto3.client(
            'bedrock-runtime',
            region_name=config.get('region', 'us-east-1'),
            aws_access_key_id=config.get('access_key'),
            aws_secret_access_key=config.get('secret_key')
        )

    async def generate_response(
        self,
        model_type: AIModelType,
        request: ModelRequest
    ) -> ModelResponse:
        """Generate response using Bedrock models"""
        start_time = time.time()

        try:
            # Map model type to Bedrock model ID
            model_id = self._get_bedrock_model_id(model_type)

            # Build request body based on model family
            if model_type in [AIModelType.CLAUDE_4_OPUS, AIModelType.CLAUDE_4_SONNET,
                             AIModelType.CLAUDE_3_OPUS, AIModelType.CLAUDE_3_SONNET,
                             AIModelType.CLAUDE_3_HAIKU]:
                body = self._build_claude_request(request)
            elif model_type in [AIModelType.NOVA_PRO, AIModelType.NOVA_LITE, AIModelType.NOVA_MICRO]:
                body = self._build_nova_request(request)
            else:
                raise ValueError(f"Unsupported model type for Bedrock: {model_type}")

            # Make API call
            response = self.client.invoke_model(
                modelId=model_id,
                body=json.dumps(body),
                contentType='application/json'
            )

            # Parse response
            response_body = json.loads(response['body'].read())

            # Extract content based on model family
            if 'claude' in model_id:
                content = self._parse_claude_response(response_body)
            elif 'nova' in model_id:
                content = self._parse_nova_response(response_body)
            else:
                content = response_body.get('completion', '')

            # Calculate cost
            usage = response_body.get('usage', {})
            cost = self._calculate_cost(model_type, usage)

            return ModelResponse(
                content=content,
                metadata={
                    "model_id": model_id,
                    "bedrock_response": response_body
                },
                usage=usage,
                model_used=f"bedrock:{model_type.value}",
                response_time=time.time() - start_time,
                cost=cost
            )

        except Exception as e:
            return ModelResponse(
                content=f"Error: {str(e)}",
                metadata={"error": str(e)},
                model_used=f"bedrock:{model_type.value}",
                response_time=time.time() - start_time
            )

    async def stream_response(
        self,
        model_type: AIModelType,
        request: ModelRequest
    ) -> AsyncIterator[str]:
        """Stream response from Bedrock models"""
        try:
            model_id = self._get_bedrock_model_id(model_type)

            if model_type in [AIModelType.CLAUDE_4_OPUS, AIModelType.CLAUDE_4_SONNET,
                             AIModelType.CLAUDE_3_OPUS, AIModelType.CLAUDE_3_SONNET,
                             AIModelType.CLAUDE_3_HAIKU]:
                body = self._build_claude_request(request)
            else:
                raise ValueError(f"Streaming not supported for model: {model_type}")

            response = self.client.invoke_model_with_response_stream(
                modelId=model_id,
                body=json.dumps(body),
                contentType='application/json'
            )

            for chunk in response['body']:
                chunk_data = json.loads(chunk['chunk']['bytes'])
                if 'delta' in chunk_data:
                    yield chunk_data['delta'].get('text', '')

        except Exception as e:
            yield f"Stream error: {str(e)}"

    def get_model_limits(self, model_type: AIModelType) -> ModelLimits:
        """Get limits for Bedrock models"""
        # Claude 4 Opus limits
        if model_type == AIModelType.CLAUDE_4_OPUS:
            return ModelLimits(
                max_tokens_per_request=4000,
                max_requests_per_minute=60,
                max_tokens_per_minute=40000,
                max_context_length=200000,
                cost_per_input_token=0.000015,
                cost_per_output_token=0.000075
            )

        # Claude 4 Sonnet limits
        elif model_type == AIModelType.CLAUDE_4_SONNET:
            return ModelLimits(
                max_tokens_per_request=4000,
                max_requests_per_minute=120,
                max_tokens_per_minute=80000,
                max_context_length=200000,
                cost_per_input_token=0.000003,
                cost_per_output_token=0.000015
            )

        # Nova Pro limits
        elif model_type == AIModelType.NOVA_PRO:
            return ModelLimits(
                max_tokens_per_request=5000,
                max_requests_per_minute=100,
                max_tokens_per_minute=100000,
                max_context_length=300000,
                cost_per_input_token=0.000008,
                cost_per_output_token=0.000032
            )

        # Default limits
        return ModelLimits()

    def get_supported_models(self) -> List[AIModelType]:
        """Get supported Bedrock models"""
        return [
            AIModelType.CLAUDE_4_OPUS,
            AIModelType.CLAUDE_4_SONNET,
            AIModelType.CLAUDE_3_OPUS,
            AIModelType.CLAUDE_3_SONNET,
            AIModelType.CLAUDE_3_HAIKU,
            AIModelType.NOVA_PRO,
            AIModelType.NOVA_LITE,
            AIModelType.NOVA_MICRO
        ]

    def get_model_capabilities(self, model_type: AIModelType) -> List[ModelCapability]:
        """Get capabilities for Bedrock models"""
        if model_type == AIModelType.CLAUDE_4_OPUS:
            return [
                ModelCapability.TEXT_GENERATION,
                ModelCapability.TEXT_ANALYSIS,
                ModelCapability.CODE_GENERATION,
                ModelCapability.REASONING,
                ModelCapability.FUNCTION_CALLING,
                ModelCapability.STREAMING,
                ModelCapability.LARGE_CONTEXT
            ]
        elif model_type in [AIModelType.NOVA_PRO, AIModelType.NOVA_LITE]:
            return [
                ModelCapability.TEXT_GENERATION,
                ModelCapability.TEXT_ANALYSIS,
                ModelCapability.MULTIMODAL,
                ModelCapability.REASONING,
                ModelCapability.STREAMING
            ]
        else:
            return [
                ModelCapability.TEXT_GENERATION,
                ModelCapability.TEXT_ANALYSIS,
                ModelCapability.STREAMING
            ]

    def _get_bedrock_model_id(self, model_type: AIModelType) -> str:
        """Map model type to Bedrock model ID"""
        model_mapping = {
            AIModelType.CLAUDE_4_OPUS: "anthropic.claude-3-opus-20240229-v1:0",
            AIModelType.CLAUDE_4_SONNET: "anthropic.claude-3-sonnet-20240229-v1:0",
            AIModelType.CLAUDE_3_OPUS: "anthropic.claude-3-opus-20240229-v1:0",
            AIModelType.CLAUDE_3_SONNET: "anthropic.claude-3-sonnet-20240229-v1:0",
            AIModelType.CLAUDE_3_HAIKU: "anthropic.claude-3-haiku-20240307-v1:0",
            AIModelType.NOVA_PRO: "amazon.nova-pro-v1:0",
            AIModelType.NOVA_LITE: "amazon.nova-lite-v1:0",
            AIModelType.NOVA_MICRO: "amazon.nova-micro-v1:0"
        }
        return model_mapping.get(model_type, model_type.value)

    def _build_claude_request(self, request: ModelRequest) -> Dict[str, Any]:
        """Build request body for Claude models"""
        messages = []

        if request.system_prompt:
            messages.append({
                "role": "system",
                "content": request.system_prompt
            })

        messages.append({
            "role": "user",
            "content": request.prompt
        })

        return {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "messages": messages,
            "stop_sequences": request.stop_sequences
        }

    def _build_nova_request(self, request: ModelRequest) -> Dict[str, Any]:
        """Build request body for Nova models"""
        return {
            "inputText": request.prompt,
            "textGenerationConfig": {
                "maxTokenCount": request.max_tokens,
                "temperature": request.temperature,
                "topP": request.top_p,
                "stopSequences": request.stop_sequences
            }
        }

    def _parse_claude_response(self, response_body: Dict[str, Any]) -> str:
        """Parse Claude model response"""
        content = response_body.get('content', [])
        if content and isinstance(content, list):
            return content[0].get('text', '')
        return response_body.get('completion', '')

    def _parse_nova_response(self, response_body: Dict[str, Any]) -> str:
        """Parse Nova model response"""
        results = response_body.get('results', [])
        if results:
            return results[0].get('outputText', '')
        return ''

    def _calculate_cost(self, model_type: AIModelType, usage: Dict[str, Any]) -> float:
        """Calculate cost based on token usage"""
        limits = self.get_model_limits(model_type)
        input_tokens = usage.get('input_tokens', 0)
        output_tokens = usage.get('output_tokens', 0)

        return (
            input_tokens * limits.cost_per_input_token +
            output_tokens * limits.cost_per_output_token
        )


class ModelManager:
    """Central manager for all AI model providers and operations"""

    def __init__(self):
        self.providers: Dict[ModelProvider, BaseModelProvider] = {}
        self.settings = get_settings()
        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize available model providers"""
        # Initialize Bedrock provider
        if self.settings.AWS_ACCESS_KEY_ID:
            bedrock_config = {
                'region': self.settings.AWS_DEFAULT_REGION,
                'access_key': self.settings.AWS_ACCESS_KEY_ID,
                'secret_key': self.settings.AWS_SECRET_ACCESS_KEY
            }
            self.providers[ModelProvider.BEDROCK] = BedrockProvider(bedrock_config)

        # Add other providers as needed
        # self.providers[ModelProvider.OPENAI] = OpenAIProvider(openai_config)

    async def generate_response(
        self,
        model_type: AIModelType,
        request: ModelRequest,
        provider: Optional[ModelProvider] = None
    ) -> ModelResponse:
        """Generate response using the specified model"""
        # Auto-select provider if not specified
        if provider is None:
            provider = self._get_optimal_provider(model_type)

        if provider not in self.providers:
            raise ValueError(f"Provider {provider} not available")

        provider_instance = self.providers[provider]

        if model_type not in provider_instance.get_supported_models():
            raise ValueError(f"Model {model_type} not supported by provider {provider}")

        return await provider_instance.generate_response(model_type, request)

    async def stream_response(
        self,
        model_type: AIModelType,
        request: ModelRequest,
        provider: Optional[ModelProvider] = None
    ) -> AsyncIterator[str]:
        """Stream response using the specified model"""
        if provider is None:
            provider = self._get_optimal_provider(model_type)

        if provider not in self.providers:
            raise ValueError(f"Provider {provider} not available")

        provider_instance = self.providers[provider]

        async for chunk in provider_instance.stream_response(model_type, request):
            yield chunk

    def get_available_models(self) -> Dict[ModelProvider, List[AIModelType]]:
        """Get all available models by provider"""
        available_models = {}
        for provider_type, provider in self.providers.items():
            available_models[provider_type] = provider.get_supported_models()
        return available_models

    def get_model_info(self, model_type: AIModelType) -> Dict[str, Any]:
        """Get comprehensive information about a model"""
        provider = self._get_optimal_provider(model_type)

        if provider not in self.providers:
            return {"error": f"Provider {provider} not available"}

        provider_instance = self.providers[provider]

        return {
            "model_type": model_type.value,
            "provider": provider.value,
            "capabilities": [cap.value for cap in provider_instance.get_model_capabilities(model_type)],
            "limits": provider_instance.get_model_limits(model_type).__dict__
        }

    def get_optimal_model_for_task(self, task_type: str, capabilities_needed: List[ModelCapability] = None) -> AIModelType:
        """Get the optimal model for a specific task"""
        capabilities_needed = capabilities_needed or []

        # Define optimal models for different task types
        task_model_mapping = {
            "reasoning": AIModelType.CLAUDE_4_OPUS,
            "analysis": AIModelType.CLAUDE_4_SONNET,
            "multimodal": AIModelType.NOVA_PRO,
            "fast_processing": AIModelType.CLAUDE_3_HAIKU,
            "code_generation": AIModelType.CLAUDE_4_OPUS,
            "general": AIModelType.CLAUDE_4_SONNET
        }

        return task_model_mapping.get(task_type, AIModelType.CLAUDE_4_SONNET)

    def _get_optimal_provider(self, model_type: AIModelType) -> ModelProvider:
        """Get the optimal provider for a model type"""
        # Check which providers support this model
        for provider_type, provider in self.providers.items():
            if model_type in provider.get_supported_models():
                return provider_type

        # Default to Bedrock if available
        if ModelProvider.BEDROCK in self.providers:
            return ModelProvider.BEDROCK

        raise ValueError(f"No provider available for model {model_type}")

    def get_provider_status(self) -> Dict[ModelProvider, Dict[str, Any]]:
        """Get status of all providers"""
        status = {}
        for provider_type, provider in self.providers.items():
            status[provider_type] = {
                "available": True,
                "supported_models": [model.value for model in provider.get_supported_models()],
                "config": provider.config
            }
        return status


# Global model manager instance
model_manager = ModelManager()