# Kinexus AI: Development Guide

## Table of Contents
- [Development Environment Setup](#development-environment-setup)
- [Project Structure](#project-structure)
- [Architecture Patterns](#architecture-patterns)
- [Agent Development](#agent-development)
- [Integration Development](#integration-development)
- [Testing Strategy](#testing-strategy)
- [Code Quality & Standards](#code-quality--standards)
- [Deployment Pipeline](#deployment-pipeline)
- [Monitoring & Debugging](#monitoring--debugging)
- [Contributing Guidelines](#contributing-guidelines)

## Development Environment Setup

### Prerequisites

#### Required Software
```bash
# Core tools
Node.js >= 18.0.0
Python >= 3.11
Docker >= 20.0.0
AWS CLI >= 2.0.0
Git >= 2.30.0

# Development tools
AWS CDK >= 2.90.0
Terraform >= 1.5.0 (optional)
PostgreSQL >= 14.0 (local testing)
Redis >= 6.0 (local testing)
```

#### AWS Account Setup
```bash
# Configure AWS CLI
aws configure

# Verify Bedrock access
aws bedrock list-foundation-models --region us-east-1

# Bootstrap CDK (one-time setup)
npx cdk bootstrap
```

#### Environment Variables
```bash
# .env.development
AWS_REGION=us-east-1
AWS_PROFILE=kinexus-dev
LOG_LEVEL=DEBUG

# Database
DATABASE_URL=postgresql://localhost:5432/kinexus_dev
REDIS_URL=redis://localhost:6379

# AI Models
CLAUDE_4_OPUS_MODEL=anthropic.claude-4-opus-4.1-v1:0
CLAUDE_4_SONNET_MODEL=anthropic.claude-4-sonnet-v1:0
NOVA_PRO_MODEL=amazon.nova-pro-v1:0

# Development features
ENABLE_DEBUG_TOOLS=true
MOCK_EXTERNAL_APIS=true
ENABLE_HOT_RELOAD=true
```

### Local Development Setup

#### 1. Clone and Install Dependencies
```bash
# Clone repository
git clone https://github.com/kinexusai/kinexus-ai.git
cd kinexus-ai

# Install Python dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install Node.js dependencies
npm install

# Install pre-commit hooks
pre-commit install
```

#### 2. Start Local Services
```bash
# Start local infrastructure
docker-compose up -d postgres redis localstack

# Run database migrations
alembic upgrade head

# Seed development data
python scripts/seed_dev_data.py
```

#### 3. Start Development Server
```bash
# Start API server
uvicorn src.api.main:app --reload --port 8000

# Start agent workers (separate terminals)
python src/agents/orchestrator.py --dev
python src/agents/change_analyzer.py --dev
python src/agents/content_creator.py --dev

# Start frontend (if developing UI)
cd frontend && npm run dev
```

### IDE Configuration

#### VS Code Setup
```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": true,
  "python.testing.pytestEnabled": true,
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    ".venv": true
  }
}
```

#### Recommended Extensions
- Python
- AWS Toolkit
- Docker
- GitLens
- Pylance
- Thunder Client (API testing)

## Project Structure

### Repository Layout
```
kinexus-ai/
├── src/                    # Source code
│   ├── agents/            # AI agent implementations
│   ├── api/               # REST API
│   ├── core/              # Core business logic
│   ├── integrations/      # External system integrations
│   ├── models/            # Data models
│   └── utils/             # Utility functions
├── infrastructure/        # Infrastructure as Code
│   ├── aws-cdk/          # CDK stacks
│   ├── terraform/        # Terraform modules
│   └── scripts/          # Deployment scripts
├── tests/                 # Test suite
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── e2e/              # End-to-end tests
├── docs/                  # Documentation
├── frontend/              # Web UI (React/TypeScript)
├── docker/                # Docker configurations
├── scripts/               # Utility scripts
└── config/                # Configuration files
```

### Core Module Architecture
```python
# src/core/
core/
├── __init__.py
├── domain/                # Domain models and business logic
│   ├── document.py       # Document entity
│   ├── change.py         # Change entity
│   ├── agent.py          # Agent entity
│   └── quality.py        # Quality metrics
├── services/              # Business services
│   ├── document_service.py
│   ├── change_service.py
│   ├── quality_service.py
│   └── notification_service.py
├── repositories/          # Data access layer
│   ├── document_repository.py
│   ├── change_repository.py
│   └── base_repository.py
└── interfaces/            # Abstractions and protocols
    ├── agent_interface.py
    ├── integration_interface.py
    └── storage_interface.py
```

## Architecture Patterns

### Domain-Driven Design (DDD)

#### Domain Entities
```python
# src/core/domain/document.py
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from enum import Enum

class DocumentStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    UNDER_REVIEW = "under_review"

class DocumentType(Enum):
    API_DOCUMENTATION = "api_doc"
    RUNBOOK = "runbook"
    GUIDE = "guide"
    POLICY = "policy"

@dataclass
class QualityMetrics:
    overall_score: float
    accuracy: float
    completeness: float
    readability: float
    freshness: float
    compliance: float

@dataclass
class Document:
    id: str
    title: str
    content: str
    document_type: DocumentType
    status: DocumentStatus
    quality_metrics: QualityMetrics
    metadata: dict
    created_at: datetime
    updated_at: datetime
    author_id: str
    team_id: str
    tags: List[str]
    
    def update_content(self, new_content: str, author_id: str) -> None:
        """Update document content with audit trail"""
        self.content = new_content
        self.updated_at = datetime.utcnow()
        self.author_id = author_id
        # Trigger quality assessment
        self._recalculate_quality_metrics()
    
    def _recalculate_quality_metrics(self) -> None:
        """Trigger quality metric recalculation"""
        # Implementation would call quality service
        pass
    
    def is_stale(self, threshold_days: int = 90) -> bool:
        """Check if document is considered stale"""
        days_since_update = (datetime.utcnow() - self.updated_at).days
        return days_since_update > threshold_days
```

#### Repository Pattern
```python
# src/core/repositories/base_repository.py
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional

T = TypeVar('T')

class BaseRepository(Generic[T], ABC):
    @abstractmethod
    async def save(self, entity: T) -> T:
        pass
    
    @abstractmethod
    async def find_by_id(self, id: str) -> Optional[T]:
        pass
    
    @abstractmethod
    async def find_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        pass
    
    @abstractmethod
    async def delete(self, id: str) -> bool:
        pass

# src/core/repositories/document_repository.py
from typing import List, Optional
from src.core.domain.document import Document, DocumentStatus, DocumentType
from src.core.repositories.base_repository import BaseRepository

class DocumentRepository(BaseRepository[Document]):
    def __init__(self, db_session):
        self.db = db_session
    
    async def save(self, document: Document) -> Document:
        """Save document to database"""
        # Implementation would use SQLAlchemy or similar
        pass
    
    async def find_by_id(self, id: str) -> Optional[Document]:
        """Find document by ID"""
        pass
    
    async def find_by_status(self, status: DocumentStatus) -> List[Document]:
        """Find documents by status"""
        pass
    
    async def find_by_type(self, doc_type: DocumentType) -> List[Document]:
        """Find documents by type"""
        pass
    
    async def find_stale_documents(self, threshold_days: int = 90) -> List[Document]:
        """Find documents that haven't been updated recently"""
        pass
    
    async def search(self, query: str, filters: dict = None) -> List[Document]:
        """Full-text search with optional filters"""
        pass
```

### Service Layer Pattern
```python
# src/core/services/document_service.py
from typing import List, Optional
import logging
from src.core.domain.document import Document, DocumentStatus
from src.core.repositories.document_repository import DocumentRepository
from src.core.services.quality_service import QualityService
from src.core.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

class DocumentService:
    def __init__(
        self,
        document_repo: DocumentRepository,
        quality_service: QualityService,
        notification_service: NotificationService
    ):
        self.document_repo = document_repo
        self.quality_service = quality_service
        self.notification_service = notification_service
    
    async def create_document(
        self,
        title: str,
        content: str,
        author_id: str,
        document_type: str,
        metadata: dict = None
    ) -> Document:
        """Create a new document"""
        
        # Validate input
        if not title or not content:
            raise ValueError("Title and content are required")
        
        # Create document entity
        document = Document(
            id=self._generate_id(),
            title=title,
            content=content,
            document_type=DocumentType(document_type),
            status=DocumentStatus.DRAFT,
            quality_metrics=await self.quality_service.assess_content(content),
            metadata=metadata or {},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            author_id=author_id,
            team_id=await self._get_author_team(author_id),
            tags=self._extract_tags(content, metadata)
        )
        
        # Save to repository
        saved_document = await self.document_repo.save(document)
        
        # Send notifications
        await self.notification_service.send_document_created(saved_document)
        
        logger.info(f"Created document {saved_document.id}")
        return saved_document
    
    async def update_document(
        self,
        document_id: str,
        content: str,
        author_id: str
    ) -> Document:
        """Update existing document"""
        
        # Get existing document
        document = await self.document_repo.find_by_id(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        # Check permissions
        if not await self._can_edit_document(document, author_id):
            raise PermissionError("User cannot edit this document")
        
        # Update document
        old_content = document.content
        document.update_content(content, author_id)
        
        # Reassess quality
        document.quality_metrics = await self.quality_service.assess_content(content)
        
        # Save changes
        updated_document = await self.document_repo.save(document)
        
        # Send notifications if significant changes
        if await self._is_significant_change(old_content, content):
            await self.notification_service.send_document_updated(updated_document)
        
        logger.info(f"Updated document {document_id}")
        return updated_document
    
    async def find_documents_needing_review(self) -> List[Document]:
        """Find documents that need human review"""
        documents = await self.document_repo.find_by_status(DocumentStatus.UNDER_REVIEW)
        return [doc for doc in documents if await self._needs_review(doc)]
    
    async def _needs_review(self, document: Document) -> bool:
        """Determine if document needs human review"""
        # Complex business logic for review requirements
        if document.quality_metrics.overall_score < 0.8:
            return True
        if document.quality_metrics.compliance < 0.9:
            return True
        if any(tag in ['security', 'compliance'] for tag in document.tags):
            return True
        return False
```

## Agent Development

### Agent Base Class
```python
# src/agents/base_agent.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List
import asyncio
import logging
from dataclasses import dataclass
from enum import Enum

class AgentStatus(Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    ERROR = "error"
    DISABLED = "disabled"

@dataclass
class AgentTask:
    id: str
    type: str
    data: Dict[str, Any]
    priority: int = 1
    created_at: datetime
    max_retries: int = 3
    retry_count: int = 0

class BaseAgent(ABC):
    def __init__(self, agent_id: str, config: Dict[str, Any]):
        self.agent_id = agent_id
        self.config = config
        self.status = AgentStatus.IDLE
        self.current_task = None
        self.task_queue = asyncio.Queue()
        self.logger = logging.getLogger(f"agent.{agent_id}")
        
    async def start(self):
        """Start the agent processing loop"""
        self.logger.info(f"Starting agent {self.agent_id}")
        self.status = AgentStatus.IDLE
        
        while True:
            try:
                # Get next task from queue
                task = await self.task_queue.get()
                await self._process_task(task)
            except Exception as e:
                self.logger.error(f"Error processing task: {e}")
                self.status = AgentStatus.ERROR
                await asyncio.sleep(5)  # Brief pause before retrying
                self.status = AgentStatus.IDLE
    
    async def _process_task(self, task: AgentTask):
        """Process a single task"""
        self.current_task = task
        self.status = AgentStatus.PROCESSING
        
        try:
            self.logger.info(f"Processing task {task.id} of type {task.type}")
            result = await self.process_task(task)
            await self._handle_task_success(task, result)
        except Exception as e:
            self.logger.error(f"Task {task.id} failed: {e}")
            await self._handle_task_failure(task, e)
        finally:
            self.current_task = None
            self.status = AgentStatus.IDLE
    
    @abstractmethod
    async def process_task(self, task: AgentTask) -> Dict[str, Any]:
        """Process a specific task - must be implemented by subclasses"""
        pass
    
    async def submit_task(self, task: AgentTask):
        """Submit a task for processing"""
        await self.task_queue.put(task)
        self.logger.debug(f"Queued task {task.id}")
    
    async def _handle_task_success(self, task: AgentTask, result: Dict[str, Any]):
        """Handle successful task completion"""
        self.logger.info(f"Task {task.id} completed successfully")
        # Emit success event
        await self._emit_event("task_completed", {
            "task_id": task.id,
            "agent_id": self.agent_id,
            "result": result
        })
    
    async def _handle_task_failure(self, task: AgentTask, error: Exception):
        """Handle task failure with retry logic"""
        task.retry_count += 1
        
        if task.retry_count < task.max_retries:
            self.logger.warning(f"Retrying task {task.id} ({task.retry_count}/{task.max_retries})")
            await asyncio.sleep(2 ** task.retry_count)  # Exponential backoff
            await self.submit_task(task)
        else:
            self.logger.error(f"Task {task.id} failed after {task.max_retries} retries")
            await self._emit_event("task_failed", {
                "task_id": task.id,
                "agent_id": self.agent_id,
                "error": str(error),
                "retry_count": task.retry_count
            })
    
    async def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit events for monitoring and coordination"""
        # Implementation would use EventBridge or similar
        pass
```

### Content Creator Agent Implementation
```python
# src/agents/content_creator.py
import asyncio
from typing import Dict, Any
import boto3
from src.agents.base_agent import BaseAgent, AgentTask
from src.core.services.document_service import DocumentService
from src.integrations.bedrock_client import BedrockClient

class ContentCreatorAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any]):
        super().__init__("content-creator", config)
        self.bedrock_client = BedrockClient()
        self.document_service = DocumentService()
        
    async def process_task(self, task: AgentTask) -> Dict[str, Any]:
        """Process content creation tasks"""
        
        task_type = task.type
        
        if task_type == "create_document":
            return await self._create_document(task.data)
        elif task_type == "update_document":
            return await self._update_document(task.data)
        elif task_type == "improve_quality":
            return await self._improve_quality(task.data)
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    
    async def _create_document(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new documentation based on change event"""
        
        change_data = data.get("change_event")
        document_type = data.get("document_type", "guide")
        
        # Analyze the change to understand what documentation is needed
        analysis = await self._analyze_documentation_needs(change_data)
        
        # Generate content using Claude 4 Sonnet
        content = await self._generate_content(analysis, document_type)
        
        # Create the document
        document = await self.document_service.create_document(
            title=analysis["suggested_title"],
            content=content,
            author_id="kinexus-ai",
            document_type=document_type,
            metadata={
                "source_change": change_data.get("id"),
                "ai_generated": True,
                "generation_model": "claude-4-sonnet"
            }
        )
        
        return {
            "document_id": document.id,
            "title": document.title,
            "quality_score": document.quality_metrics.overall_score
        }
    
    async def _update_document(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing document based on changes"""
        
        document_id = data.get("document_id")
        change_data = data.get("change_event")
        
        # Get existing document
        document = await self.document_service.find_by_id(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        # Determine what changes are needed
        update_analysis = await self._analyze_required_updates(document, change_data)
        
        # Generate updated content
        updated_content = await self._update_content(
            document.content,
            update_analysis,
            change_data
        )
        
        # Update the document
        updated_document = await self.document_service.update_document(
            document_id=document_id,
            content=updated_content,
            author_id="kinexus-ai"
        )
        
        return {
            "document_id": updated_document.id,
            "changes_made": update_analysis["changes"],
            "quality_score": updated_document.quality_metrics.overall_score
        }
    
    async def _generate_content(self, analysis: Dict[str, Any], document_type: str) -> str:
        """Generate documentation content using Claude 4"""
        
        prompt = self._build_generation_prompt(analysis, document_type)
        
        response = await self.bedrock_client.invoke_claude_4_sonnet(
            prompt=prompt,
            max_tokens=4000,
            temperature=0.3
        )
        
        return response["content"]
    
    def _build_generation_prompt(self, analysis: Dict[str, Any], document_type: str) -> str:
        """Build prompt for content generation"""
        
        base_prompt = f"""
        You are a technical writer creating {document_type} documentation.
        
        Context:
        {analysis.get('context', '')}
        
        Requirements:
        - Clear, concise technical writing
        - Include code examples where appropriate
        - Follow standard documentation structure
        - Ensure accuracy and completeness
        
        Topic: {analysis.get('topic', '')}
        
        Generate comprehensive documentation covering:
        {chr(10).join(f"- {req}" for req in analysis.get('requirements', []))}
        """
        
        return base_prompt
    
    async def _analyze_documentation_needs(self, change_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze what documentation is needed for a change"""
        
        analysis_prompt = f"""
        Analyze this system change and determine what documentation is needed:
        
        Change Details:
        {change_data}
        
        Provide analysis in JSON format:
        {{
            "suggested_title": "Document title",
            "topic": "Main topic to document",
            "requirements": ["list", "of", "requirements"],
            "context": "Additional context",
            "urgency": "high|medium|low"
        }}
        """
        
        response = await self.bedrock_client.invoke_claude_4_opus(
            prompt=analysis_prompt,
            max_tokens=1000,
            temperature=0.1
        )
        
        return json.loads(response["content"])
```

### Agent Testing Framework
```python
# tests/agents/test_content_creator.py
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from src.agents.content_creator import ContentCreatorAgent
from src.agents.base_agent import AgentTask

class TestContentCreatorAgent:
    @pytest.fixture
    async def agent(self):
        config = {
            "bedrock_region": "us-east-1",
            "max_concurrent_tasks": 5
        }
        agent = ContentCreatorAgent(config)
        # Mock external dependencies
        agent.bedrock_client = Mock()
        agent.document_service = Mock()
        return agent
    
    @pytest.mark.asyncio
    async def test_create_document_task(self, agent):
        """Test document creation task processing"""
        
        # Setup mocks
        agent.bedrock_client.invoke_claude_4_opus = AsyncMock(
            return_value={"content": '{"suggested_title": "Test Doc", "requirements": []}'}
        )
        agent.bedrock_client.invoke_claude_4_sonnet = AsyncMock(
            return_value={"content": "Generated documentation content"}
        )
        agent.document_service.create_document = AsyncMock(
            return_value=Mock(id="doc123", title="Test Doc", quality_metrics=Mock(overall_score=0.85))
        )
        
        # Create task
        task = AgentTask(
            id="task123",
            type="create_document",
            data={
                "change_event": {"id": "change123", "type": "feature_added"},
                "document_type": "guide"
            },
            created_at=datetime.utcnow()
        )
        
        # Process task
        result = await agent.process_task(task)
        
        # Verify results
        assert result["document_id"] == "doc123"
        assert result["title"] == "Test Doc"
        assert result["quality_score"] == 0.85
        
        # Verify mocks were called
        agent.bedrock_client.invoke_claude_4_opus.assert_called_once()
        agent.bedrock_client.invoke_claude_4_sonnet.assert_called_once()
        agent.document_service.create_document.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_agent_retry_logic(self, agent):
        """Test agent retry logic on failure"""
        
        # Setup mock to fail then succeed
        call_count = 0
        async def failing_mock(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Temporary failure")
            return {"content": "Success"}
        
        agent.bedrock_client.invoke_claude_4_opus = failing_mock
        agent.bedrock_client.invoke_claude_4_sonnet = AsyncMock(
            return_value={"content": "Content"}
        )
        agent.document_service.create_document = AsyncMock(
            return_value=Mock(id="doc123", title="Test", quality_metrics=Mock(overall_score=0.85))
        )
        
        # Create task with retry capability
        task = AgentTask(
            id="task123",
            type="create_document",
            data={"change_event": {"id": "change123"}},
            created_at=datetime.utcnow(),
            max_retries=3
        )
        
        # Start agent processing
        agent_task = asyncio.create_task(agent.start())
        await agent.submit_task(task)
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Verify retry occurred
        assert call_count == 2
        
        # Cleanup
        agent_task.cancel()
```

## Integration Development

### Integration Base Class
```python
# src/integrations/base_integration.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import aiohttp
import asyncio
from dataclasses import dataclass
from enum import Enum

class IntegrationStatus(Enum):
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"
    CONFIGURING = "configuring"

@dataclass
class IntegrationEvent:
    id: str
    source: str
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime
    processed: bool = False

class BaseIntegration(ABC):
    def __init__(self, integration_id: str, config: Dict[str, Any]):
        self.integration_id = integration_id
        self.config = config
        self.status = IntegrationStatus.CONFIGURING
        self.session = None
        self.webhook_handlers = {}
        
    async def initialize(self):
        """Initialize the integration"""
        self.session = aiohttp.ClientSession()
        await self.setup_authentication()
        await self.validate_connection()
        await self.setup_webhooks()
        self.status = IntegrationStatus.ACTIVE
        
    async def shutdown(self):
        """Clean shutdown of integration"""
        if self.session:
            await self.session.close()
        await self.cleanup_webhooks()
        
    @abstractmethod
    async def setup_authentication(self):
        """Setup authentication for the external service"""
        pass
        
    @abstractmethod
    async def validate_connection(self):
        """Validate connection to external service"""
        pass
        
    @abstractmethod
    async def setup_webhooks(self):
        """Setup webhooks for real-time event delivery"""
        pass
        
    @abstractmethod
    async def cleanup_webhooks(self):
        """Clean up webhooks on shutdown"""
        pass
        
    @abstractmethod
    async def process_webhook(self, payload: Dict[str, Any]) -> Optional[IntegrationEvent]:
        """Process incoming webhook payload"""
        pass
        
    async def handle_webhook(self, event_type: str, payload: Dict[str, Any]):
        """Handle incoming webhook"""
        try:
            event = await self.process_webhook(payload)
            if event:
                await self._emit_integration_event(event)
        except Exception as e:
            logger.error(f"Error processing webhook {event_type}: {e}")
            self.status = IntegrationStatus.ERROR
```

### Jira Integration Implementation
```python
# src/integrations/jira_integration.py
import aiohttp
import base64
from typing import Dict, Any, Optional
from src.integrations.base_integration import BaseIntegration, IntegrationEvent

class JiraIntegration(BaseIntegration):
    def __init__(self, config: Dict[str, Any]):
        super().__init__("jira", config)
        self.base_url = config["base_url"]
        self.auth_token = config["auth_token"]
        self.projects = config.get("projects", [])
        self.events = config.get("events", ["issue_created", "issue_updated"])
        
    async def setup_authentication(self):
        """Setup Jira authentication headers"""
        auth_string = f":{self.auth_token}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        self.session.headers.update({
            'Authorization': f'Basic {auth_b64}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
    async def validate_connection(self):
        """Validate Jira connection"""
        url = f"{self.base_url}/rest/api/3/myself"
        
        async with self.session.get(url) as response:
            if response.status != 200:
                raise Exception(f"Jira connection failed: {response.status}")
            
            user_data = await response.json()
            logger.info(f"Connected to Jira as {user_data.get('displayName')}")
            
    async def setup_webhooks(self):
        """Setup Jira webhooks"""
        webhook_url = f"{self.config['kinexus_webhook_base']}/webhooks/jira"
        
        webhook_data = {
            "name": "Kinexus AI Webhook",
            "url": webhook_url,
            "events": self.events,
            "filters": {
                "issue-related-events-section": f"project in ({','.join(self.projects)})"
            }
        }
        
        url = f"{self.base_url}/rest/webhooks/1.0/webhook"
        
        async with self.session.post(url, json=webhook_data) as response:
            if response.status not in [200, 201]:
                error_text = await response.text()
                raise Exception(f"Failed to create Jira webhook: {error_text}")
            
            webhook_result = await response.json()
            self.config["webhook_id"] = webhook_result["self"]
            logger.info(f"Created Jira webhook: {webhook_result['self']}")
            
    async def cleanup_webhooks(self):
        """Remove Jira webhooks"""
        if webhook_id := self.config.get("webhook_id"):
            url = f"{self.base_url}/rest/webhooks/1.0/webhook/{webhook_id}"
            
            async with self.session.delete(url) as response:
                if response.status == 204:
                    logger.info("Removed Jira webhook")
                else:
                    logger.warning(f"Failed to remove Jira webhook: {response.status}")
                    
    async def process_webhook(self, payload: Dict[str, Any]) -> Optional[IntegrationEvent]:
        """Process Jira webhook payload"""
        
        webhook_event = payload.get("webhookEvent")
        if not webhook_event:
            return None
            
        # Extract issue data
        issue = payload.get("issue", {})
        issue_key = issue.get("key")
        
        if not issue_key:
            return None
            
        # Create integration event
        event = IntegrationEvent(
            id=f"jira_{issue_key}_{int(time.time())}",
            source="jira",
            event_type=self._map_webhook_event(webhook_event),
            data={
                "issue_key": issue_key,
                "summary": issue.get("fields", {}).get("summary"),
                "issue_type": issue.get("fields", {}).get("issuetype", {}).get("name"),
                "status": issue.get("fields", {}).get("status", {}).get("name"),
                "project": issue.get("fields", {}).get("project", {}).get("key"),
                "assignee": self._extract_assignee(issue),
                "labels": issue.get("fields", {}).get("labels", []),
                "components": [c.get("name") for c in issue.get("fields", {}).get("components", [])],
                "raw_payload": payload
            },
            timestamp=datetime.utcnow()
        )
        
        return event
        
    def _map_webhook_event(self, webhook_event: str) -> str:
        """Map Jira webhook events to internal event types"""
        mapping = {
            "jira:issue_created": "issue_created",
            "jira:issue_updated": "issue_updated",
            "jira:issue_deleted": "issue_deleted"
        }
        return mapping.get(webhook_event, "unknown")
        
    def _extract_assignee(self, issue: Dict[str, Any]) -> Optional[str]:
        """Extract assignee from issue data"""
        assignee = issue.get("fields", {}).get("assignee")
        if assignee:
            return assignee.get("emailAddress") or assignee.get("displayName")
        return None
        
    async def get_issue_details(self, issue_key: str) -> Dict[str, Any]:
        """Get detailed issue information"""
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}"
        
        async with self.session.get(url) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(f"Failed to get issue {issue_key}: {response.status}")
```

### Integration Testing
```python
# tests/integrations/test_jira_integration.py
import pytest
import aioresponses
from src.integrations.jira_integration import JiraIntegration

class TestJiraIntegration:
    @pytest.fixture
    def jira_config(self):
        return {
            "base_url": "https://test.atlassian.net",
            "auth_token": "test_token",
            "projects": ["TEST", "DEMO"],
            "events": ["issue_created", "issue_updated"],
            "kinexus_webhook_base": "https://api.kinexusai.com"
        }
    
    @pytest.fixture
    async def jira_integration(self, jira_config):
        integration = JiraIntegration(jira_config)
        await integration.initialize()
        yield integration
        await integration.shutdown()
    
    @pytest.mark.asyncio
    async def test_webhook_processing(self, jira_integration):
        """Test Jira webhook payload processing"""
        
        webhook_payload = {
            "webhookEvent": "jira:issue_created",
            "issue": {
                "key": "TEST-123",
                "fields": {
                    "summary": "Test issue",
                    "issuetype": {"name": "Story"},
                    "status": {"name": "To Do"},
                    "project": {"key": "TEST"},
                    "assignee": {"emailAddress": "test@example.com"},
                    "labels": ["documentation", "api"],
                    "components": [{"name": "API"}]
                }
            }
        }
        
        event = await jira_integration.process_webhook(webhook_payload)
        
        assert event is not None
        assert event.source == "jira"
        assert event.event_type == "issue_created"
        assert event.data["issue_key"] == "TEST-123"
        assert event.data["summary"] == "Test issue"
        assert event.data["project"] == "TEST"
        assert "documentation" in event.data["labels"]
    
    @pytest.mark.asyncio
    async def test_connection_validation(self, jira_config):
        """Test Jira connection validation"""
        
        with aioresponses.aioresponses() as m:
            # Mock successful auth check
            m.get(
                f"{jira_config['base_url']}/rest/api/3/myself",
                payload={"displayName": "Test User"}
            )
            
            integration = JiraIntegration(jira_config)
            await integration.setup_authentication()
            await integration.validate_connection()
            
            assert integration.status != IntegrationStatus.ERROR
```

## Testing Strategy

### Test Structure
```
tests/
├── unit/                  # Unit tests
│   ├── test_agents/      # Agent unit tests
│   ├── test_services/    # Service unit tests
│   ├── test_models/      # Model unit tests
│   └── test_utils/       # Utility unit tests
├── integration/          # Integration tests
│   ├── test_api/         # API integration tests
│   ├── test_agents/      # Agent integration tests
│   └── test_integrations/ # External integration tests
├── e2e/                  # End-to-end tests
│   ├── test_workflows/   # Complete workflow tests
│   └── test_scenarios/   # User scenario tests
├── performance/          # Performance tests
│   ├── load_tests/       # Load testing
│   └── stress_tests/     # Stress testing
└── fixtures/             # Test data and fixtures
```

### Testing Configuration
```python
# tests/conftest.py
import pytest
import asyncio
import os
from unittest.mock import Mock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.core.database import Base
from src.api.main import create_app

# Test database setup
TEST_DATABASE_URL = "postgresql://test:test@localhost:5432/kinexus_test"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine"""
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)

@pytest.fixture
async def test_db_session(test_engine):
    """Create test database session"""
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()

@pytest.fixture
async def test_client():
    """Create test API client"""
    app = create_app(testing=True)
    async with app.test_client() as client:
        yield client

@pytest.fixture
def mock_bedrock_client():
    """Mock Bedrock client for testing"""
    mock_client = Mock()
    mock_client.invoke_claude_4_opus = Mock(return_value={"content": "Test response"})
    mock_client.invoke_claude_4_sonnet = Mock(return_value={"content": "Test content"})
    return mock_client
```

### Unit Test Examples
```python
# tests/unit/test_services/test_document_service.py
import pytest
from unittest.mock import Mock, AsyncMock
from src.core.services.document_service import DocumentService
from src.core.domain.document import Document, DocumentStatus, DocumentType

class TestDocumentService:
    @pytest.fixture
    def document_service(self):
        mock_repo = Mock()
        mock_quality_service = Mock()
        mock_notification_service = Mock()
        
        return DocumentService(
            document_repo=mock_repo,
            quality_service=mock_quality_service,
            notification_service=mock_notification_service
        )
    
    @pytest.mark.asyncio
    async def test_create_document_success(self, document_service):
        """Test successful document creation"""
        
        # Setup mocks
        document_service.quality_service.assess_content = AsyncMock(
            return_value=Mock(overall_score=0.85)
        )
        document_service.document_repo.save = AsyncMock(
            return_value=Mock(id="doc123", title="Test Doc")
        )
        document_service.notification_service.send_document_created = AsyncMock()
        
        # Create document
        result = await document_service.create_document(
            title="Test Document",
            content="Test content",
            author_id="user123",
            document_type="guide"
        )
        
        # Verify calls
        document_service.quality_service.assess_content.assert_called_once()
        document_service.document_repo.save.assert_called_once()
        document_service.notification_service.send_document_created.assert_called_once()
        
        assert result.id == "doc123"
        assert result.title == "Test Doc"
    
    @pytest.mark.asyncio
    async def test_create_document_validation_error(self, document_service):
        """Test document creation with validation error"""
        
        with pytest.raises(ValueError, match="Title and content are required"):
            await document_service.create_document(
                title="",  # Empty title should trigger validation error
                content="Test content",
                author_id="user123",
                document_type="guide"
            )
```

### Integration Test Examples
```python
# tests/integration/test_api/test_documents_api.py
import pytest
from fastapi.testclient import TestClient

class TestDocumentsAPI:
    @pytest.mark.asyncio
    async def test_create_document_endpoint(self, test_client):
        """Test document creation API endpoint"""
        
        document_data = {
            "title": "Test API Document",
            "content": "This is test content",
            "document_type": "api_doc",
            "tags": ["api", "test"]
        }
        
        response = await test_client.post("/api/v1/documents", json=document_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test API Document"
        assert data["document_type"] == "api_doc"
        assert "id" in data
    
    @pytest.mark.asyncio
    async def test_get_documents_list(self, test_client):
        """Test getting documents list"""
        
        response = await test_client.get("/api/v1/documents")
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)
    
    @pytest.mark.asyncio
    async def test_document_quality_metrics(self, test_client):
        """Test document quality metrics endpoint"""
        
        # First create a document
        document_data = {
            "title": "Quality Test Document",
            "content": "This is content for quality testing",
            "document_type": "guide"
        }
        
        create_response = await test_client.post("/api/v1/documents", json=document_data)
        document_id = create_response.json()["id"]
        
        # Get quality metrics
        response = await test_client.get(f"/api/v1/documents/{document_id}/quality")
        
        assert response.status_code == 200
        data = response.json()
        assert "overall_score" in data
        assert "accuracy" in data
        assert "completeness" in data
```

## Code Quality & Standards

### Code Style Configuration
```python
# pyproject.toml
[tool.black]
line-length = 100
target-version = ['py311']
include = '\.pyi?$'
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
)/
'''

[tool.isort]
profile = "black"
multi_line_output = 3
line_length = 100
known_first_party = ["src", "tests"]

[tool.flake8]
max-line-length = 100
extend-ignore = ["E203", "W503"]
exclude = [
    ".git",
    "__pycache__",
    ".venv",
    "build",
    "dist"
]

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short --strict-markers"
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "e2e: End-to-end tests",
    "slow: Slow running tests"
]
```

### Pre-commit Configuration
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-json
      - id: check-merge-conflict
      - id: debug-statements

  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.3.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]

  - repo: https://github.com/pycqa/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: ['-r', 'src/']

  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v3.0.0
    hooks:
      - id: prettier
        files: \.(js|ts|jsx|tsx|json|yaml|yml|md)$
```

### Documentation Standards
```python
# src/core/services/example_service.py
"""
Example service demonstrating documentation standards.

This module contains the ExampleService class which provides
business logic for managing example entities in the Kinexus AI system.
"""

from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ExampleService:
    """
    Service for managing example entities.
    
    This service provides high-level business operations for example entities,
    including creation, retrieval, updating, and deletion. It coordinates
    between the repository layer and external services.
    
    Attributes:
        repository: The repository for data persistence
        notification_service: Service for sending notifications
        
    Example:
        >>> service = ExampleService(repo, notification_service)
        >>> example = await service.create_example("test", {"key": "value"})
        >>> print(example.id)
        "example_123"
    """
    
    def __init__(self, repository: ExampleRepository, notification_service: NotificationService):
        """
        Initialize the example service.
        
        Args:
            repository: Repository for example data persistence
            notification_service: Service for sending notifications
            
        Raises:
            ValueError: If repository or notification_service is None
        """
        if not repository:
            raise ValueError("Repository is required")
        if not notification_service:
            raise ValueError("Notification service is required")
            
        self.repository = repository
        self.notification_service = notification_service
        
    async def create_example(
        self,
        name: str,
        metadata: Dict[str, Any],
        author_id: str
    ) -> Example:
        """
        Create a new example entity.
        
        Creates a new example with the provided name and metadata,
        performs validation, saves to the repository, and sends
        notifications to relevant stakeholders.
        
        Args:
            name: The name for the example (must be unique)
            metadata: Additional metadata for the example
            author_id: ID of the user creating the example
            
        Returns:
            The created example entity with assigned ID
            
        Raises:
            ValueError: If name is empty or already exists
            PermissionError: If author doesn't have creation permissions
            
        Example:
            >>> example = await service.create_example(
            ...     "My Example",
            ...     {"category": "test"},
            ...     "user_123"
            ... )
            >>> print(example.name)
            "My Example"
        """
        # Validation
        if not name or not name.strip():
            raise ValueError("Example name cannot be empty")
            
        if await self.repository.exists_by_name(name):
            raise ValueError(f"Example with name '{name}' already exists")
            
        if not await self._can_create_example(author_id):
            raise PermissionError("User does not have permission to create examples")
        
        # Create entity
        example = Example(
            id=self._generate_id(),
            name=name.strip(),
            metadata=metadata or {},
            author_id=author_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Save to repository
        saved_example = await self.repository.save(example)
        
        # Send notifications
        await self.notification_service.send_example_created(saved_example)
        
        logger.info(f"Created example {saved_example.id} with name '{name}'")
        return saved_example
```

This comprehensive development guide provides all the tools, patterns, and practices needed to contribute effectively to Kinexus AI, ensuring high-quality, maintainable code that leverages the latest AWS AI capabilities.