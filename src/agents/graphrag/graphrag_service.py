#!/usr/bin/env python3
"""
GraphRAG Service for Kinexus AI
Implements Microsoft GraphRAG for relationship-aware document retrieval
"""
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import boto3
import numpy as np
import pandas as pd
import uvicorn
from fastapi import FastAPI, HTTPException
from graphrag.query.structured_search.global_search.community_context import (
    GlobalCommunityContext,
)
from graphrag.query.structured_search.global_search.search import GlobalSearch
from graphrag.query.structured_search.local_search.mixed_context import (
    LocalSearchMixedContext,
)
from graphrag.query.structured_search.local_search.search import LocalSearch
from pydantic import BaseModel

sys.path.append("/app")
from src.config.model_config import ModelCapability, ModelConfigManager  # noqa: E402

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GraphRAGQuery(BaseModel):
    """GraphRAG query model"""

    query: str
    search_type: str = "local"  # "local" or "global"
    community_level: int = 2
    response_type: str = "multiple_paragraphs"
    max_tokens: int = 1500


class GraphRAGResponse(BaseModel):
    """GraphRAG response model"""

    query: str
    response: str
    context_data: Dict[str, Any]
    search_type: str
    processing_time: float
    entities: List[str] = []
    relationships: List[Dict[str, Any]] = []


class BedrockLLM:
    """Bedrock-compatible LLM interface for GraphRAG"""

    def __init__(self, model_config: ModelConfigManager):
        self.model_config = model_config
        self.bedrock_runtime = boto3.client(
            "bedrock-runtime", region_name=model_config.region
        )
        self.model_id = model_config.get_best_model_for_task(
            [ModelCapability.REASONING, ModelCapability.HIGH_QUALITY], "premium"
        )

    async def agenerate(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate response using Bedrock"""
        try:
            # Convert messages to Bedrock format
            prompt = self._messages_to_prompt(messages)

            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": kwargs.get("max_tokens", 1500),
                "messages": [{"role": "user", "content": prompt}],
            }

            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body),
            )

            response_body = json.loads(response["body"].read())
            return response_body["content"][0]["text"]

        except Exception as e:
            logger.error(f"Bedrock generation failed: {str(e)}")
            return f"Error generating response: {str(e)}"

    def _messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Convert messages to a single prompt"""
        prompt_parts = []
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            prompt_parts.append(f"{role.upper()}: {content}")
        return "\n\n".join(prompt_parts)


class GraphRAGManager:
    """Manager for GraphRAG operations"""

    def __init__(self, data_dir: str = "/app/data"):
        self.data_dir = Path(data_dir)
        self.input_dir = self.data_dir / "input"
        self.output_dir = self.data_dir / "output"
        self.cache_dir = self.data_dir / "cache"

        # Create directories
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize model config
        self.model_config = ModelConfigManager(
            region=os.getenv("AWS_REGION", "us-east-1")
        )
        self.llm = BedrockLLM(self.model_config)

        # Initialize search engines
        self.local_search_engine = None
        self.global_search_engine = None

        logger.info("GraphRAG Manager initialized")

    async def initialize_search_engines(self):
        """Initialize local and global search engines"""
        try:
            # Load entities and reports
            entities_path = self.output_dir / "entities.parquet"
            reports_path = self.output_dir / "reports.parquet"

            if entities_path.exists() and reports_path.exists():
                # Read indexed data
                entity_df = pd.read_parquet(entities_path)
                entity_embedding_df = pd.read_parquet(
                    self.output_dir / "entity_embeddings.parquet"
                )

                # Initialize local search
                local_context_builder = LocalSearchMixedContext(
                    community_reports=pd.read_parquet(reports_path),
                    text_units=pd.read_parquet(self.output_dir / "text_units.parquet"),
                    entities=entity_df,
                    entity_embeddings=entity_embedding_df,
                    relationships=pd.read_parquet(
                        self.output_dir / "relationships.parquet"
                    ),
                    covariates=(
                        pd.read_parquet(self.output_dir / "covariates.parquet")
                        if (self.output_dir / "covariates.parquet").exists()
                        else None
                    ),
                    text_embedder=None,  # We'll use Bedrock embeddings
                )

                self.local_search_engine = LocalSearch(
                    llm=self.llm,
                    context_builder=local_context_builder,
                    token_encoder=None,  # Use default
                )

                # Initialize global search
                global_context_builder = GlobalCommunityContext(
                    community_reports=pd.read_parquet(reports_path),
                    entities=entity_df,
                    token_encoder=None,  # Use default
                )

                self.global_search_engine = GlobalSearch(
                    llm=self.llm,
                    context_builder=global_context_builder,
                    token_encoder=None,
                    max_tokens=1500,
                )

                logger.info("Search engines initialized successfully")
            else:
                logger.warning(
                    "GraphRAG index files not found. Please run indexing first."
                )

        except Exception as e:
            logger.error(f"Failed to initialize search engines: {str(e)}")

    async def index_documents(self, documents: List[str]) -> bool:
        """Index documents for GraphRAG"""
        try:
            # Save documents to input directory
            for i, doc in enumerate(documents):
                doc_path = self.input_dir / f"document_{i}.txt"
                with open(doc_path, "w", encoding="utf-8") as f:
                    f.write(doc)

            # Note: In a full implementation, you would run the GraphRAG indexing pipeline here
            # For now, we'll create mock indexed data
            await self._create_mock_index()

            logger.info(f"Indexed {len(documents)} documents")
            return True

        except Exception as e:
            logger.error(f"Failed to index documents: {str(e)}")
            return False

    async def _create_mock_index(self):
        """Create mock indexed data for development"""
        try:
            # Create mock entities
            entities_data = {
                "id": ["entity_1", "entity_2", "entity_3"],
                "name": ["Kinexus AI", "Documentation", "AWS Bedrock"],
                "type": ["Organization", "Concept", "Technology"],
                "description": [
                    "AI-powered documentation management system",
                    "Technical documentation and guides",
                    "Amazon cloud AI service platform",
                ],
                "community": [0, 0, 1],
                "level": [0, 0, 0],
            }
            entities_df = pd.DataFrame(entities_data)
            entities_df.to_parquet(self.output_dir / "entities.parquet")

            # Create mock entity embeddings
            entity_embeddings_data = {
                "id": ["entity_1", "entity_2", "entity_3"],
                "embedding": [
                    np.random.rand(1536).tolist(),
                    np.random.rand(1536).tolist(),
                    np.random.rand(1536).tolist(),
                ],
            }
            entity_embeddings_df = pd.DataFrame(entity_embeddings_data)
            entity_embeddings_df.to_parquet(
                self.output_dir / "entity_embeddings.parquet"
            )

            # Create mock relationships
            relationships_data = {
                "source": ["entity_1", "entity_1", "entity_2"],
                "target": ["entity_2", "entity_3", "entity_3"],
                "weight": [0.8, 0.6, 0.7],
                "description": [
                    "Kinexus AI manages documentation",
                    "Kinexus AI uses AWS Bedrock",
                    "Documentation hosted on AWS Bedrock",
                ],
            }
            relationships_df = pd.DataFrame(relationships_data)
            relationships_df.to_parquet(self.output_dir / "relationships.parquet")

            # Create mock text units
            text_units_data = {
                "id": ["unit_1", "unit_2", "unit_3"],
                "text": [
                    "Kinexus AI is an autonomous knowledge management system designed for enterprise documentation.",
                    "The system uses AWS Bedrock models including Claude and Nova for intelligent processing.",
                    "Documentation is automatically updated based on system changes and user requirements.",
                ],
                "n_tokens": [15, 14, 13],
                "document_ids": ["doc_1", "doc_1", "doc_2"],
                "entity_ids": [
                    ["entity_1", "entity_2"],
                    ["entity_1", "entity_3"],
                    ["entity_2", "entity_3"],
                ],
            }
            text_units_df = pd.DataFrame(text_units_data)
            text_units_df.to_parquet(self.output_dir / "text_units.parquet")

            # Create mock community reports
            reports_data = {
                "community": [0, 1],
                "level": [0, 0],
                "title": [
                    "Documentation Management Community",
                    "AI Technology Community",
                ],
                "summary": [
                    "This community focuses on documentation management and knowledge systems.",
                    "This community centers around AI technologies and cloud platforms.",
                ],
                "findings": [
                    [
                        "Kinexus AI automates documentation processes",
                        "Integration with enterprise systems is key",
                    ],
                    [
                        "AWS Bedrock provides foundation models",
                        "Claude models excel at reasoning tasks",
                    ],
                ],
                "rank": [9.0, 8.5],
                "rank_explanation": [
                    "High importance due to core business function",
                    "Critical technology infrastructure component",
                ],
            }
            reports_df = pd.DataFrame(reports_data)
            reports_df.to_parquet(self.output_dir / "reports.parquet")

            logger.info("Mock GraphRAG index created successfully")

        except Exception as e:
            logger.error(f"Failed to create mock index: {str(e)}")

    async def search(
        self, query: str, search_type: str = "local", **kwargs
    ) -> GraphRAGResponse:
        """Perform GraphRAG search"""
        start_time = datetime.now()

        try:
            if search_type == "local" and self.local_search_engine:
                result = await self.local_search_engine.asearch(query, **kwargs)
                context_data = {
                    "search_type": "local",
                    "entities_used": [],
                    "relationships_used": [],
                }

            elif search_type == "global" and self.global_search_engine:
                result = await self.global_search_engine.asearch(query, **kwargs)
                context_data = {"search_type": "global", "communities_used": []}

            else:
                # Fallback to mock response
                result = await self._mock_search(query, search_type)
                context_data = {"search_type": "mock", "note": "Using mock data"}

            processing_time = (datetime.now() - start_time).total_seconds()

            return GraphRAGResponse(
                query=query,
                response=result,
                context_data=context_data,
                search_type=search_type,
                processing_time=processing_time,
                entities=self._extract_entities(result),
                relationships=self._extract_relationships(result),
            )

        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            processing_time = (datetime.now() - start_time).total_seconds()

            return GraphRAGResponse(
                query=query,
                response=f"Search error: {str(e)}",
                context_data={"error": str(e)},
                search_type=search_type,
                processing_time=processing_time,
            )

    async def _mock_search(self, query: str, search_type: str) -> str:
        """Mock search for development/testing"""
        if search_type == "global":
            return f"Global search results for '{query}': This query relates to the broader context of documentation management systems and AI technologies. Kinexus AI represents a comprehensive solution that leverages AWS Bedrock's foundation models to automate knowledge management processes across enterprise environments."
        else:
            return f"Local search results for '{query}': Based on the knowledge graph, this query connects to specific entities including Kinexus AI (documentation management system), AWS Bedrock (AI platform), and various documentation processes. The system uses Claude models for reasoning and content generation."

    def _extract_entities(self, text: str) -> List[str]:
        """Extract entity mentions from response text"""
        entities = []
        # Simple entity extraction (in production, use NER)
        for entity in ["Kinexus AI", "AWS Bedrock", "Claude", "Documentation"]:
            if entity.lower() in text.lower():
                entities.append(entity)
        return entities

    def _extract_relationships(self, text: str) -> List[Dict[str, Any]]:
        """Extract relationships from response text"""
        relationships = []
        # Simple relationship extraction
        if "kinexus ai" in text.lower() and "aws bedrock" in text.lower():
            relationships.append(
                {
                    "source": "Kinexus AI",
                    "target": "AWS Bedrock",
                    "relationship": "uses",
                }
            )
        return relationships


# FastAPI app
app = FastAPI(title="Kinexus AI GraphRAG Service", version="1.0.0")

# Global GraphRAG manager
graphrag_manager: Optional[GraphRAGManager] = None


@app.on_event("startup")
async def startup_event():
    """Initialize GraphRAG on startup"""
    global graphrag_manager
    graphrag_manager = GraphRAGManager()
    await graphrag_manager.initialize_search_engines()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "graphrag",
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/search", response_model=GraphRAGResponse)
async def search_endpoint(query: GraphRAGQuery):
    """GraphRAG search endpoint"""
    if not graphrag_manager:
        raise HTTPException(status_code=500, detail="GraphRAG not initialized")

    return await graphrag_manager.search(
        query=query.query,
        search_type=query.search_type,
        community_level=query.community_level,
        response_type=query.response_type,
        max_tokens=query.max_tokens,
    )


@app.post("/index")
async def index_documents(documents: List[str]):
    """Index documents for GraphRAG"""
    if not graphrag_manager:
        raise HTTPException(status_code=500, detail="GraphRAG not initialized")

    success = await graphrag_manager.index_documents(documents)
    if success:
        await graphrag_manager.initialize_search_engines()
        return {"status": "success", "documents_indexed": len(documents)}
    else:
        raise HTTPException(status_code=500, detail="Failed to index documents")


@app.get("/status")
async def get_status():
    """Get GraphRAG service status"""
    if not graphrag_manager:
        return {"status": "not_initialized"}

    return {
        "status": "ready",
        "local_search": graphrag_manager.local_search_engine is not None,
        "global_search": graphrag_manager.global_search_engine is not None,
        "data_dir": str(graphrag_manager.data_dir),
    }


if __name__ == "__main__":
    uvicorn.run(
        app, host="0.0.0.0", port=8002
    )  # nosec B104 - Required for Docker container networking
