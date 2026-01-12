#!/usr/bin/env python3
"""FastAPI server for VISTA RAG system."""

import logging
import sys
import os
from pathlib import Path
from typing import Optional, List, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from vista.config import Config
from vista.document_loader import DocumentLoader
from vista.text_chunker import TextChunker
from vista.embedding_generator import EmbeddingGenerator
from vista.vector_store import VectorStoreManager
from vista.llm_factory import LLMFactory
from vista.query_engine import QueryEngine


# Request/Response models
class ChatRequest(BaseModel):
    message: str
    llm_provider: Optional[str] = None  # Optional LLM provider override
    
class SourceDocument(BaseModel):
    text: str
    source: Optional[str] = None
    
class ChatResponse(BaseModel):
    response: str
    sources: Optional[List[SourceDocument]] = None


# Global query engine instance
query_engine: Optional[QueryEngine] = None


def setup_logging() -> None:
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def initialize_vista() -> QueryEngine:
    """Initialize VISTA system - same as main.py but returns QueryEngine."""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting Vista API Server...")
        
        # Load configuration
        config = Config.from_env()
        logger.info(f"Using LLM Provider: {config.llm_provider}")
        logger.info(f"Using LLM Model: {config.llm_model}")
        
        # Validate data directory
        data_path = Path(config.data_directory)
        if not data_path.exists():
            raise Exception(f"Data directory does not exist: {config.data_directory}")
        
        # Initialize core components
        document_loader = DocumentLoader()
        text_chunker = TextChunker(
            chunk_size=config.chunk_size,
            overlap=config.chunk_overlap
        )
        embedding_generator = EmbeddingGenerator(model_name=config.embedding_model)
        vector_store = VectorStoreManager(persist_directory=config.persist_directory)
        vector_store.create_collection("personal_knowledge")
        
        # Initialize LLM client
        llm_client = LLMFactory.create_llm_client(
            provider=config.llm_provider,
            api_key=config.get_api_key(),
            model=config.llm_model
        )
        
        # Initialize query engine
        engine = QueryEngine(
            vector_store=vector_store,
            embedding_gen=embedding_generator,
            llm_client=llm_client,
            max_context_tokens=config.max_context_tokens
        )
        
        # Check if knowledge base exists
        existing_count = vector_store.get_collection_count()
        if existing_count > 0:
            logger.info(f"Found existing knowledge base with {existing_count} chunks")
            return engine
        
        # Build knowledge base if needed
        logger.info("Building knowledge base from documents...")
        documents = document_loader.load_documents(config.data_directory)
        
        if not documents:
            raise Exception(f"No documents found in {config.data_directory}")
        
        logger.info(f"Loaded {len(documents)} documents")
        
        # Chunk documents
        all_chunks = []
        for document in documents:
            chunks = text_chunker.chunk_document(document)
            all_chunks.extend(chunks)
        
        if not all_chunks:
            raise Exception("No chunks generated from documents")
        
        logger.info(f"Generated {len(all_chunks)} chunks")
        
        # Generate embeddings
        chunk_texts = [chunk.text for chunk in all_chunks]
        embeddings = embedding_generator.generate_batch_embeddings(chunk_texts)
        
        # Store in vector database
        vector_store.add_chunks(all_chunks, embeddings)
        
        logger.info(f"Knowledge base ready with {len(all_chunks)} chunks from {len(documents)} documents")
        
        return engine
        
    except Exception as e:
        logger.error(f"VISTA initialization failed: {e}")
        raise


# Create FastAPI app
app = FastAPI(title="VISTA API", description="Personal RAG Chatbot API")

# Add CORS middleware to allow frontend to communicate
# In production, restrict to your specific domain
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize VISTA when server starts."""
    global query_engine
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        query_engine = initialize_vista()
        logger.info("VISTA API Server ready!")
    except Exception as e:
        logger.error(f"Failed to initialize VISTA: {e}")
        sys.exit(1)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "online",
        "message": "VISTA API Server is running",
        "version": "1.0.0"
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Handle chat requests from the frontend.
    
    Args:
        request: ChatRequest with user message and optional llm_provider
        
    Returns:
        ChatResponse with AI response and optional sources
    """
    if not query_engine:
        raise HTTPException(status_code=503, detail="VISTA not initialized")
    
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    try:
        logger = logging.getLogger(__name__)
        logger.info(f"Processing query: {request.message}")
        
        # If a specific LLM provider is requested, create a new LLM client
        if request.llm_provider:
            logger.info(f"Using LLM provider: {request.llm_provider}")
            config = Config.from_env()
            
            # Get the API key and model for the requested provider
            if request.llm_provider == "openai":
                api_key = config.openai_api_key
                # Use OpenAI model from env or default
                model = os.getenv("OpenAI_MODEL", "gpt-4o-mini")
            elif request.llm_provider == "gemini":
                api_key = config.gemini_api_key
                # Use Gemini model from env or default
                model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
            else:
                raise ValueError(f"Unknown LLM provider: {request.llm_provider}")
            
            if not api_key:
                raise ValueError(f"API key not configured for provider: {request.llm_provider}")
            
            # Create LLM client for the requested provider
            llm_client = LLMFactory.create_llm_client(
                provider=request.llm_provider,
                api_key=api_key,
                model=model
            )
            
            # Temporarily update the query engine's LLM client
            original_llm = query_engine.llm_client
            query_engine.llm_client = llm_client
        
        # Use your existing query engine to get the response
        result = query_engine.query(request.message)
        
        # Restore original LLM client if we switched providers
        if request.llm_provider:
            query_engine.llm_client = original_llm
        
        # Handle different possible return types
        # Case 1: result is a QueryResponse object with .answer attribute
        if hasattr(result, 'answer'):
            response_text = result.answer
            # Extract sources if available
            sources = None
            if hasattr(result, 'sources') and result.sources:
                sources = [
                    SourceDocument(
                        text=src.text if hasattr(src, 'text') else str(src),
                        source=src.source if hasattr(src, 'source') else None
                    )
                    for src in result.sources
                ]
        # Case 2: result is just a string
        elif isinstance(result, str):
            response_text = result
            sources = None
        # Case 3: result is a dict
        elif isinstance(result, dict):
            response_text = result.get('answer') or result.get('response') or str(result)
            sources = None
        # Fallback: convert to string
        else:
            response_text = str(result)
            sources = None
        
        logger.info("Query processed successfully")
        
        return ChatResponse(
            response=response_text,
            sources=sources
        )
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy" if query_engine else "initializing",
        "vista_ready": query_engine is not None
    }


if __name__ == "__main__":
    # Run the server
    # Use reload=False in production, reload=True for development
    is_production = os.getenv("ENVIRONMENT", "development") == "production"
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=not is_production,
        log_level=os.getenv("LOG_LEVEL", "info")
    )