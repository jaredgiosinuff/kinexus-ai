#!/usr/bin/env python3
"""
Persistent Agent Memory System - 2024-2025 Agentic AI Pattern
Implements multi-tier memory architecture for learning and continuous improvement
"""
import asyncio
import base64
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import boto3

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Handle numpy import gracefully
try:
    import numpy as np

    NUMPY_AVAILABLE = True
except ImportError:
    logger.warning("NumPy not available, using basic similarity calculations")
    NUMPY_AVAILABLE = False


class MemoryType(Enum):
    SEMANTIC = "semantic"  # Facts about repositories, APIs, patterns
    EPISODIC = "episodic"  # Past experiences and outcomes
    PROCEDURAL = "procedural"  # Learned procedures and strategies
    WORKING = "working"  # Temporary context for current session


class ExperienceType(Enum):
    DOCUMENTATION_UPDATE = "documentation_update"
    CHANGE_ANALYSIS = "change_analysis"
    PLATFORM_INTEGRATION = "platform_integration"
    ERROR_RESOLUTION = "error_resolution"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"


@dataclass
class MemoryEntry:
    memory_id: str
    memory_type: MemoryType
    content: Dict[str, Any]
    embeddings: Optional[List[float]] = None
    confidence_score: float = 0.0
    access_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Experience:
    experience_id: str
    experience_type: ExperienceType
    input_context: Dict[str, Any]
    actions_taken: List[Dict[str, Any]]
    outcomes: Dict[str, Any]
    success_metrics: Dict[str, float]
    lessons_learned: List[str]
    agent_participants: List[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    confidence_score: float = 0.0


@dataclass
class Procedure:
    procedure_id: str
    name: str
    description: str
    steps: List[Dict[str, Any]]
    conditions: Dict[str, Any]
    success_rate: float = 0.0
    usage_count: int = 0
    last_updated: datetime = field(default_factory=datetime.utcnow)
    tags: List[str] = field(default_factory=list)


class VectorStore:
    """Vector storage and similarity search for semantic memory"""

    def __init__(self, region: str = "us-east-1"):
        self.bedrock = boto3.client("bedrock-runtime", region_name=region)
        self.dynamodb = boto3.resource("dynamodb", region_name=region)
        self.embedding_model = "amazon.titan-embed-text-v1"

        # Ensure tables exist
        self._ensure_tables()

    def _ensure_tables(self):
        """Ensure DynamoDB tables exist for vector storage"""
        table_configs = [
            {
                "TableName": "kinexus-semantic-memory",
                "AttributeDefinitions": [
                    {"AttributeName": "memory_id", "AttributeType": "S"},
                    {"AttributeName": "memory_type", "AttributeType": "S"},
                ],
                "KeySchema": [
                    {"AttributeName": "memory_id", "KeyType": "HASH"},
                    {"AttributeName": "memory_type", "KeyType": "RANGE"},
                ],
            },
            {
                "TableName": "kinexus-episodic-memory",
                "AttributeDefinitions": [
                    {"AttributeName": "experience_id", "AttributeType": "S"},
                    {"AttributeName": "experience_type", "AttributeType": "S"},
                ],
                "KeySchema": [
                    {"AttributeName": "experience_id", "KeyType": "HASH"},
                    {"AttributeName": "experience_type", "KeyType": "RANGE"},
                ],
            },
            {
                "TableName": "kinexus-procedural-memory",
                "AttributeDefinitions": [
                    {"AttributeName": "procedure_id", "AttributeType": "S"}
                ],
                "KeySchema": [{"AttributeName": "procedure_id", "KeyType": "HASH"}],
            },
        ]

        dynamodb_client = boto3.client("dynamodb")

        for config in table_configs:
            try:
                dynamodb_client.describe_table(TableName=config["TableName"])
                logger.info(f"Table {config['TableName']} already exists")
            except dynamodb_client.exceptions.ResourceNotFoundException:
                try:
                    config["BillingMode"] = "PAY_PER_REQUEST"
                    dynamodb_client.create_table(**config)
                    logger.info(f"Created table {config['TableName']}")
                except Exception as e:
                    logger.warning(f"Could not create table {config['TableName']}: {e}")

    async def get_embeddings(self, text: str) -> List[float]:
        """Get embeddings for text using Bedrock Titan"""
        try:
            request_body = {"inputText": text}

            response = self.bedrock.invoke_model(
                modelId=self.embedding_model,
                body=json.dumps(request_body),
                contentType="application/json",
            )

            response_body = json.loads(response["body"].read())
            return response_body["embedding"]

        except Exception as e:
            logger.error(f"Failed to get embeddings: {str(e)}")
            # Return zero vector as fallback
            return [0.0] * 1536  # Titan embedding dimension

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            if NUMPY_AVAILABLE:
                np_vec1 = np.array(vec1)
                np_vec2 = np.array(vec2)

                dot_product = np.dot(np_vec1, np_vec2)
                norm1 = np.linalg.norm(np_vec1)
                norm2 = np.linalg.norm(np_vec2)

                if norm1 == 0 or norm2 == 0:
                    return 0.0

                return dot_product / (norm1 * norm2)
            else:
                # Basic similarity calculation without numpy
                if len(vec1) != len(vec2):
                    return 0.0

                dot_product = sum(a * b for a, b in zip(vec1, vec2))
                norm1 = sum(a * a for a in vec1) ** 0.5
                norm2 = sum(b * b for b in vec2) ** 0.5

                if norm1 == 0 or norm2 == 0:
                    return 0.0

                return dot_product / (norm1 * norm2)
        except Exception:
            return 0.0


class SemanticMemory:
    """Stores factual knowledge about systems, patterns, and relationships"""

    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.table = vector_store.dynamodb.Table("kinexus-semantic-memory")

    async def store_knowledge(
        self, content: Dict[str, Any], tags: List[str] = None
    ) -> str:
        """Store semantic knowledge with vector embeddings"""

        # Create searchable text from content
        searchable_text = self._create_searchable_text(content)

        # Generate embeddings
        embeddings = await self.vector_store.get_embeddings(searchable_text)

        # Create memory entry
        memory_id = hashlib.md5(searchable_text.encode()).hexdigest()

        entry = MemoryEntry(
            memory_id=memory_id,
            memory_type=MemoryType.SEMANTIC,
            content=content,
            embeddings=embeddings,
            confidence_score=0.9,  # High confidence for explicitly stored facts
            tags=tags or [],
            metadata={"searchable_text": searchable_text},
        )

        # Store in DynamoDB
        try:
            item = {
                "memory_id": entry.memory_id,
                "memory_type": entry.memory_type.value,
                "content": json.dumps(entry.content),
                "embeddings": base64.b64encode(
                    json.dumps(entry.embeddings).encode()
                ).decode(),
                "confidence_score": entry.confidence_score,
                "access_count": entry.access_count,
                "created_at": entry.created_at.isoformat(),
                "last_accessed": entry.last_accessed.isoformat(),
                "tags": entry.tags,
                "metadata": json.dumps(entry.metadata),
            }

            self.table.put_item(Item=item)
            logger.info(f"Stored semantic memory: {memory_id}")
            return memory_id

        except Exception as e:
            logger.error(f"Failed to store semantic memory: {str(e)}")
            return None

    async def search_knowledge(
        self, query: str, limit: int = 5, min_similarity: float = 0.7
    ) -> List[MemoryEntry]:
        """Search for relevant knowledge using vector similarity"""

        try:
            # Get query embeddings
            query_embeddings = await self.vector_store.get_embeddings(query)

            # Scan all semantic memories (in production, use vector database)
            response = self.table.scan(
                FilterExpression="memory_type = :mt",
                ExpressionAttributeValues={":mt": MemoryType.SEMANTIC.value},
            )

            results = []
            for item in response["Items"]:
                try:
                    # Decode embeddings
                    item_embeddings = json.loads(
                        base64.b64decode(item["embeddings"]).decode()
                    )

                    # Calculate similarity
                    similarity = self.vector_store.cosine_similarity(
                        query_embeddings, item_embeddings
                    )

                    if similarity >= min_similarity:
                        entry = MemoryEntry(
                            memory_id=item["memory_id"],
                            memory_type=MemoryType(item["memory_type"]),
                            content=json.loads(item["content"]),
                            embeddings=item_embeddings,
                            confidence_score=float(item["confidence_score"]),
                            access_count=int(item["access_count"]),
                            created_at=datetime.fromisoformat(item["created_at"]),
                            last_accessed=datetime.fromisoformat(item["last_accessed"]),
                            tags=item.get("tags", []),
                            metadata=json.loads(item.get("metadata", "{}")),
                        )

                        results.append((entry, similarity))

                except Exception as e:
                    logger.warning(f"Error processing memory item: {e}")
                    continue

            # Sort by similarity and return top results
            results.sort(key=lambda x: x[1], reverse=True)
            return [entry for entry, _ in results[:limit]]

        except Exception as e:
            logger.error(f"Failed to search semantic memory: {str(e)}")
            return []

    def _create_searchable_text(self, content: Dict[str, Any]) -> str:
        """Create searchable text representation of content"""
        text_parts = []

        def extract_text(obj, prefix=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, (str, int, float)):
                        text_parts.append(f"{prefix}{key}: {value}")
                    elif isinstance(value, (dict, list)):
                        extract_text(value, f"{prefix}{key}.")
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    extract_text(item, f"{prefix}[{i}].")
            else:
                text_parts.append(str(obj))

        extract_text(content)
        return " ".join(text_parts)


class EpisodicMemory:
    """Stores experiences, outcomes, and lessons learned"""

    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.table = vector_store.dynamodb.Table("kinexus-episodic-memory")

    async def store_experience(self, experience: Experience) -> str:
        """Store an experience with its outcomes and lessons"""

        try:
            item = {
                "experience_id": experience.experience_id,
                "experience_type": experience.experience_type.value,
                "input_context": json.dumps(experience.input_context),
                "actions_taken": json.dumps(experience.actions_taken),
                "outcomes": json.dumps(experience.outcomes),
                "success_metrics": json.dumps(experience.success_metrics),
                "lessons_learned": experience.lessons_learned,
                "agent_participants": experience.agent_participants,
                "timestamp": experience.timestamp.isoformat(),
                "confidence_score": experience.confidence_score,
            }

            self.table.put_item(Item=item)
            logger.info(f"Stored experience: {experience.experience_id}")
            return experience.experience_id

        except Exception as e:
            logger.error(f"Failed to store experience: {str(e)}")
            return None

    async def find_similar_experiences(
        self,
        context: Dict[str, Any],
        experience_type: ExperienceType = None,
        limit: int = 5,
    ) -> List[Experience]:
        """Find similar past experiences based on context"""

        try:
            filter_expression = None
            expression_values = {}

            if experience_type:
                filter_expression = "experience_type = :et"
                expression_values[":et"] = experience_type.value

            if filter_expression:
                response = self.table.scan(
                    FilterExpression=filter_expression,
                    ExpressionAttributeValues=expression_values,
                )
            else:
                response = self.table.scan()

            experiences = []
            for item in response["Items"]:
                try:
                    experience = Experience(
                        experience_id=item["experience_id"],
                        experience_type=ExperienceType(item["experience_type"]),
                        input_context=json.loads(item["input_context"]),
                        actions_taken=json.loads(item["actions_taken"]),
                        outcomes=json.loads(item["outcomes"]),
                        success_metrics=json.loads(item["success_metrics"]),
                        lessons_learned=item["lessons_learned"],
                        agent_participants=item["agent_participants"],
                        timestamp=datetime.fromisoformat(item["timestamp"]),
                        confidence_score=float(item["confidence_score"]),
                    )

                    # Calculate context similarity (simplified)
                    similarity = self._calculate_context_similarity(
                        context, experience.input_context
                    )
                    experiences.append((experience, similarity))

                except Exception as e:
                    logger.warning(f"Error processing experience item: {e}")
                    continue

            # Sort by similarity and return top results
            experiences.sort(key=lambda x: x[1], reverse=True)
            return [exp for exp, _ in experiences[:limit]]

        except Exception as e:
            logger.error(f"Failed to find similar experiences: {str(e)}")
            return []

    def _calculate_context_similarity(
        self, context1: Dict[str, Any], context2: Dict[str, Any]
    ) -> float:
        """Calculate similarity between two contexts (simplified heuristic)"""

        # Compare key fields
        common_keys = set(context1.keys()) & set(context2.keys())
        if not common_keys:
            return 0.0

        matches = 0
        total = len(common_keys)

        for key in common_keys:
            val1, val2 = context1[key], context2[key]

            if isinstance(val1, str) and isinstance(val2, str):
                # String similarity (simplified)
                if val1.lower() == val2.lower():
                    matches += 1
                elif val1.lower() in val2.lower() or val2.lower() in val1.lower():
                    matches += 0.5
            elif val1 == val2:
                matches += 1

        return matches / total if total > 0 else 0.0


class ProceduralMemory:
    """Stores learned procedures and strategies"""

    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.table = vector_store.dynamodb.Table("kinexus-procedural-memory")

    async def store_procedure(self, procedure: Procedure) -> str:
        """Store a learned procedure"""

        try:
            item = {
                "procedure_id": procedure.procedure_id,
                "name": procedure.name,
                "description": procedure.description,
                "steps": json.dumps(procedure.steps),
                "conditions": json.dumps(procedure.conditions),
                "success_rate": procedure.success_rate,
                "usage_count": procedure.usage_count,
                "last_updated": procedure.last_updated.isoformat(),
                "tags": procedure.tags,
            }

            self.table.put_item(Item=item)
            logger.info(f"Stored procedure: {procedure.procedure_id}")
            return procedure.procedure_id

        except Exception as e:
            logger.error(f"Failed to store procedure: {str(e)}")
            return None

    async def find_applicable_procedures(
        self, conditions: Dict[str, Any], min_success_rate: float = 0.7
    ) -> List[Procedure]:
        """Find procedures applicable to current conditions"""

        try:
            response = self.table.scan()

            applicable_procedures = []
            for item in response["Items"]:
                try:
                    procedure = Procedure(
                        procedure_id=item["procedure_id"],
                        name=item["name"],
                        description=item["description"],
                        steps=json.loads(item["steps"]),
                        conditions=json.loads(item["conditions"]),
                        success_rate=float(item["success_rate"]),
                        usage_count=int(item["usage_count"]),
                        last_updated=datetime.fromisoformat(item["last_updated"]),
                        tags=item.get("tags", []),
                    )

                    # Check if procedure conditions match current conditions
                    if (
                        procedure.success_rate >= min_success_rate
                        and self._conditions_match(conditions, procedure.conditions)
                    ):
                        applicable_procedures.append(procedure)

                except Exception as e:
                    logger.warning(f"Error processing procedure item: {e}")
                    continue

            # Sort by success rate and usage count
            applicable_procedures.sort(
                key=lambda p: (p.success_rate, p.usage_count), reverse=True
            )

            return applicable_procedures

        except Exception as e:
            logger.error(f"Failed to find applicable procedures: {str(e)}")
            return []

    def _conditions_match(
        self, current: Dict[str, Any], required: Dict[str, Any]
    ) -> bool:
        """Check if current conditions match required conditions"""

        for key, required_value in required.items():
            if key not in current:
                return False

            current_value = current[key]

            # Exact match
            if current_value == required_value:
                continue

            # Range or pattern matching could be added here
            # For now, use simple string containment for strings
            if isinstance(current_value, str) and isinstance(required_value, str):
                if required_value.lower() in current_value.lower():
                    continue

            return False

        return True


class PersistentMemorySystem:
    """
    Main coordinator for the persistent memory system
    Integrates semantic, episodic, and procedural memory
    """

    def __init__(self, region: str = "us-east-1"):
        self.vector_store = VectorStore(region)
        self.semantic_memory = SemanticMemory(self.vector_store)
        self.episodic_memory = EpisodicMemory(self.vector_store)
        self.procedural_memory = ProceduralMemory(self.vector_store)
        self.working_memory = {}  # Temporary session context

    async def initialize_knowledge_base(self):
        """Initialize with foundational knowledge about documentation systems"""

        foundational_knowledge = [
            {
                "type": "documentation_pattern",
                "pattern": "api_documentation",
                "typical_sections": [
                    "overview",
                    "authentication",
                    "endpoints",
                    "examples",
                    "errors",
                ],
                "update_triggers": ["api_changes", "new_endpoints", "breaking_changes"],
                "priority": "high",
            },
            {
                "type": "documentation_pattern",
                "pattern": "integration_guide",
                "typical_sections": [
                    "prerequisites",
                    "setup",
                    "configuration",
                    "testing",
                ],
                "update_triggers": ["dependency_changes", "setup_process_changes"],
                "priority": "medium",
            },
            {
                "type": "platform_characteristics",
                "platform": "github",
                "file_formats": ["markdown", "rst"],
                "update_method": "file_commits",
                "api_rate_limits": {"requests_per_hour": 5000},
            },
            {
                "type": "platform_characteristics",
                "platform": "confluence",
                "file_formats": ["html", "storage_format"],
                "update_method": "rest_api",
                "api_rate_limits": {"requests_per_second": 10},
            },
        ]

        for knowledge in foundational_knowledge:
            await self.semantic_memory.store_knowledge(
                knowledge, tags=knowledge.get("type", "").split("_")
            )

        logger.info("Initialized foundational knowledge base")

    async def learn_from_experience(self, experience: Experience):
        """Learn from a completed experience and update memories"""

        # Store the experience
        await self.episodic_memory.store_experience(experience)

        # Extract lessons as semantic knowledge
        for lesson in experience.lessons_learned:
            lesson_knowledge = {
                "type": "learned_pattern",
                "lesson": lesson,
                "context": experience.input_context,
                "success_metrics": experience.success_metrics,
                "experience_id": experience.experience_id,
            }

            await self.semantic_memory.store_knowledge(
                lesson_knowledge, tags=["lesson", experience.experience_type.value]
            )

        # Update or create procedures based on successful patterns
        if experience.success_metrics.get("overall_success", 0) > 0.8:
            await self._extract_successful_procedure(experience)

    async def _extract_successful_procedure(self, experience: Experience):
        """Extract a reusable procedure from a successful experience"""

        procedure_id = f"proc_{experience.experience_type.value}_{hash(str(experience.input_context))}"

        procedure = Procedure(
            procedure_id=procedure_id,
            name=f"Successful {experience.experience_type.value} procedure",
            description=f"Procedure extracted from successful experience {experience.experience_id}",
            steps=experience.actions_taken,
            conditions=experience.input_context,
            success_rate=experience.success_metrics.get("overall_success", 0.0),
            usage_count=1,
            tags=[experience.experience_type.value, "auto_extracted"],
        )

        await self.procedural_memory.store_procedure(procedure)

    async def get_contextual_insights(
        self, current_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get relevant insights from all memory types for current context"""

        insights = {
            "semantic_knowledge": [],
            "similar_experiences": [],
            "applicable_procedures": [],
            "recommendations": [],
        }

        # Search semantic memory
        context_query = self._context_to_query(current_context)
        semantic_results = await self.semantic_memory.search_knowledge(
            context_query, limit=3
        )
        insights["semantic_knowledge"] = [
            {
                "content": entry.content,
                "confidence": entry.confidence_score,
                "tags": entry.tags,
            }
            for entry in semantic_results
        ]

        # Find similar experiences
        similar_experiences = await self.episodic_memory.find_similar_experiences(
            current_context, limit=3
        )
        insights["similar_experiences"] = [
            {
                "experience_id": exp.experience_id,
                "experience_type": exp.experience_type.value,
                "outcomes": exp.outcomes,
                "success_metrics": exp.success_metrics,
                "lessons_learned": exp.lessons_learned,
            }
            for exp in similar_experiences
        ]

        # Find applicable procedures
        applicable_procedures = await self.procedural_memory.find_applicable_procedures(
            current_context, min_success_rate=0.6
        )
        insights["applicable_procedures"] = [
            {
                "procedure_id": proc.procedure_id,
                "name": proc.name,
                "description": proc.description,
                "success_rate": proc.success_rate,
                "steps": proc.steps,
            }
            for proc in applicable_procedures
        ]

        # Generate recommendations based on memory
        insights["recommendations"] = self._generate_recommendations(insights)

        return insights

    def _context_to_query(self, context: Dict[str, Any]) -> str:
        """Convert context dictionary to search query"""
        query_parts = []

        for key, value in context.items():
            if isinstance(value, str):
                query_parts.append(f"{key} {value}")
            elif isinstance(value, (int, float)):
                query_parts.append(f"{key} {value}")
            elif isinstance(value, list):
                query_parts.append(f"{key} {' '.join(str(v) for v in value)}")

        return " ".join(query_parts)

    def _generate_recommendations(self, insights: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on memory insights"""
        recommendations = []

        # Recommendations from similar experiences
        for exp in insights["similar_experiences"]:
            if exp["success_metrics"].get("overall_success", 0) > 0.8:
                recommendations.extend(exp["lessons_learned"])

        # Recommendations from applicable procedures
        for proc in insights["applicable_procedures"]:
            if proc["success_rate"] > 0.8:
                recommendations.append(f"Consider using procedure: {proc['name']}")

        # Recommendations from semantic knowledge
        for knowledge in insights["semantic_knowledge"]:
            if "recommendation" in knowledge["content"]:
                recommendations.append(knowledge["content"]["recommendation"])

        return list(set(recommendations))  # Remove duplicates


# Integration function for the multi-agent supervisor
async def enhance_with_persistent_memory(
    agent_context: Dict[str, Any], memory_system: PersistentMemorySystem
) -> Dict[str, Any]:
    """
    Enhance agent processing with persistent memory insights
    Called by agents to access memory and learn from experiences
    """
    try:
        # Get contextual insights
        insights = await memory_system.get_contextual_insights(agent_context)

        return {
            "memory_enhanced": True,
            "memory_insights": insights,
            "memory_system_status": "operational",
            "enhancement_version": "2024-2025-persistent-memory",
        }

    except Exception as e:
        logger.error(f"Memory enhancement failed: {str(e)}")
        return {
            "memory_enhanced": False,
            "error": str(e),
            "fallback_recommendation": "Proceed without memory enhancement",
        }


if __name__ == "__main__":
    # Test the persistent memory system
    import asyncio

    async def test_memory_system():
        memory_system = PersistentMemorySystem()
        await memory_system.initialize_knowledge_base()

        # Test storing and retrieving knowledge
        test_context = {
            "change_type": "api_modification",
            "repository": "kinexusai/kinexus-ai",
            "affected_files": ["routes/auth.py", "docs/api.md"],
        }

        insights = await memory_system.get_contextual_insights(test_context)
        print(json.dumps(insights, indent=2))

    asyncio.run(test_memory_system())
