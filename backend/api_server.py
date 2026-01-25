#!/usr/bin/env python3
"""FastAPI server for VISTA RAG system."""

import logging
import sys
import os
import time
import traceback
from pathlib import Path
from typing import Optional, List, Dict

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

from vista.config import Config
from vista.document_loader import DocumentLoader
from vista.text_chunker import TextChunker
from vista.embedding_generator import EmbeddingGenerator
from vista.vector_store import VectorStoreManager
from vista.llm_factory import LLMFactory
from vista.query_engine import QueryEngine
from vista.security import SecurityManager
from vista.health_check import HealthChecker
from vista.structured_logging import StructuredLogger, setup_structured_logging, set_request_id, get_request_id
from vista.metrics import MetricsCollector


# Configure basic logging FIRST before anything else
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


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


# Global instances
query_engine: Optional[QueryEngine] = None
security_manager: Optional[SecurityManager] = None
health_checker: Optional[HealthChecker] = None
metrics_collector: Optional[MetricsCollector] = None
structured_logger: Optional[StructuredLogger] = None


def initialize_vista() -> QueryEngine:
    """Initialize VISTA system - same as main.py but returns QueryEngine."""
    global security_manager
    
    try:
        logger.info("=" * 50)
        logger.info("STARTING VISTA INITIALIZATION")
        logger.info("=" * 50)
        
        # Load configuration
        logger.info("Loading configuration from environment...")
        config = Config.from_env()
        logger.info(f"✓ Configuration loaded successfully")
        logger.info(f"  LLM Provider: {config.llm_provider}")
        logger.info(f"  LLM Model: {config.llm_model}")
        logger.info(f"  Embedding Model: {config.embedding_model}")
        logger.info(f"  Data Directory: {config.data_directory}")
        
        # Initialize core components
        logger.info("Initializing document loader...")
        document_loader = DocumentLoader()
        logger.info("✓ Document loader initialized")
        
        logger.info("Initializing text chunker...")
        text_chunker = TextChunker(
            chunk_size=config.chunk_size,
            overlap=config.chunk_overlap
        )
        logger.info(f"✓ Text chunker initialized (chunk_size={config.chunk_size}, overlap={config.chunk_overlap})")
        
        logger.info("Initializing embedding generator...")
        embedding_generator = EmbeddingGenerator(model_name=config.embedding_model)
        logger.info("✓ Embedding generator initialized")
        
        logger.info("Initializing vector store...")
        vector_store = VectorStoreManager(
            api_key=config.pinecone_api_key,
            environment=config.pinecone_environment,
            index_name=config.pinecone_index_name,
            namespace=config.pinecone_namespace
        )
        logger.info("✓ Vector store manager initialized")
        
        logger.info("Creating/connecting to vector collection...")
        vector_store.create_collection()
        logger.info("✓ Vector collection ready")
        
        # Initialize LLM client
        logger.info(f"Initializing LLM client ({config.llm_provider})...")
        llm_client = LLMFactory.create_llm_client(
            provider=config.llm_provider,
            api_key=config.get_api_key(),
            model=config.llm_model
        )
        logger.info("✓ LLM client initialized")
        
        # Initialize query engine
        logger.info("Creating query engine...")
        engine = QueryEngine(
            vector_store=vector_store,
            embedding_gen=embedding_generator,
            llm_client=llm_client,
            max_context_tokens=config.max_context_tokens
        )
        logger.info("✓ Query engine created")
        
        # Check if knowledge base exists
        logger.info("Checking existing knowledge base...")
        existing_count = vector_store.get_collection_count()
        
        if existing_count > 0:
            logger.info(f"✓ Found existing knowledge base with {existing_count} chunks")
            logger.info("=" * 50)
            logger.info("VISTA INITIALIZATION COMPLETE")
            logger.info("=" * 50)
            return engine
        
        # Build knowledge base if needed
        logger.info("No existing knowledge base found. Building from documents...")
        
        # Check for data directory only if we need to build the KB
        data_path = Path(config.data_directory)
        if not data_path.exists():
            raise Exception(f"Cannot build knowledge base: Data directory does not exist at {config.data_directory}")
        
        logger.info(f"Loading documents from {config.data_directory}...")
        documents = document_loader.load_documents(config.data_directory)
        
        if not documents:
            raise Exception(f"No documents found in {config.data_directory}")
        
        logger.info(f"✓ Loaded {len(documents)} documents")
        
        # Chunk documents
        logger.info("Chunking documents...")
        all_chunks = []
        for i, document in enumerate(documents):
            chunks = text_chunker.chunk_document(document)
            all_chunks.extend(chunks)
            logger.info(f"  Document {i+1}/{len(documents)}: {len(chunks)} chunks")
        
        if not all_chunks:
            raise Exception("No chunks generated from documents")
        
        logger.info(f"✓ Generated {len(all_chunks)} total chunks")
        
        # Generate embeddings
        logger.info("Generating embeddings...")
        chunk_texts = [chunk.text for chunk in all_chunks]
        embeddings = embedding_generator.generate_batch_embeddings(chunk_texts)
        logger.info(f"✓ Generated embeddings for {len(embeddings)} chunks")
        
        # Store in vector database
        logger.info("Storing chunks in vector database...")
        vector_store.add_chunks(all_chunks, embeddings)
        logger.info(f"✓ Stored {len(all_chunks)} chunks")
        
        logger.info("=" * 50)
        logger.info(f"KNOWLEDGE BASE READY: {len(all_chunks)} chunks from {len(documents)} documents")
        logger.info("=" * 50)
        
        return engine
        
    except Exception as e:
        logger.error("=" * 50)
        logger.error("VISTA INITIALIZATION FAILED")
        logger.error("=" * 50)
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("Full traceback:")
        logger.error(traceback.format_exc())
        logger.error("=" * 50)
        
        # Sanitize error before re-raising
        if security_manager:
            sanitized_error = security_manager.sanitize_error_message(e)
        else:
            sanitized_error = str(e)
        
        raise Exception(f"VISTA initialization failed: {sanitized_error}") from e


# Create FastAPI app
app = FastAPI(title="VISTA API", description="Personal RAG Chatbot API")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    global query_engine, security_manager, health_checker, metrics_collector, structured_logger
    
    # Startup
    logger.info("FastAPI lifespan startup initiated")
    
    try:
        logger.info("Loading configuration...")
        config = Config.from_env()
        
        logger.info("Setting up structured logging...")
        setup_structured_logging(config.log_level)
        structured_logger = StructuredLogger(__name__)
        logger.info("✓ Structured logging configured")
        
        logger.info(f"Initializing security manager with {len(config.allowed_origins)} allowed origins...")
        security_manager = SecurityManager(config.allowed_origins)
        logger.info("✓ Security manager initialized")
        
        logger.info("Initializing metrics collector...")
        metrics_collector = MetricsCollector()
        logger.info("✓ Metrics collector initialized")
        
        # Initialize VISTA
        logger.info("Starting VISTA initialization...")
        query_engine = initialize_vista()
        logger.info("✓ VISTA initialized successfully")
        
        # Initialize health checker
        logger.info("Initializing health checker...")
        vector_store = None
        llm_client = None
        
        # Extract components from query engine
        if query_engine:
            vector_store = query_engine.vector_store
            llm_client = query_engine.llm_client
        
        health_checker = HealthChecker(
            query_engine=query_engine,
            vector_store=vector_store,
            llm_client=llm_client
        )
        logger.info("✓ Health checker initialized")
        
        logger.info("=" * 50)
        logger.info("VISTA API SERVER READY!")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error("=" * 50)
        logger.error("FASTAPI STARTUP FAILED")
        logger.error("=" * 50)
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("Full traceback:")
        logger.error(traceback.format_exc())
        logger.error("=" * 50)
        # Don't exit in production - let health checks fail instead
        # This allows the container to stay up for debugging
        if os.getenv("ENVIRONMENT") != "production":
            sys.exit(1)
    
    yield
    
    # Shutdown
    logger.info("VISTA API Server shutting down...")


# Recreate app with lifespan
app = FastAPI(title="VISTA API", description="Personal RAG Chatbot API", lifespan=lifespan)


# CORS validation middleware
async def cors_validation_middleware(request: Request, call_next):
    """Validate CORS origin before processing request."""
    global security_manager, metrics_collector, structured_logger
    
    # Generate or get request ID
    request_id = request.headers.get("x-request-id", get_request_id())
    set_request_id(request_id)
    
    # Log incoming request
    if structured_logger:
        structured_logger.log_request(request.method, request.url.path)
    
    # Get origin from request
    origin = request.headers.get("origin")
    
    # If origin is present, validate it
    if origin and security_manager:
        if not security_manager.validate_origin(origin):
            if structured_logger:
                structured_logger.log_security_event("cors_rejection", {"origin": origin})
            return JSONResponse(
                status_code=403,
                content={"detail": "Origin not allowed"}
            )
    
    # Record request start time
    start_time = time.time()
    
    try:
        response = await call_next(request)
        
        # Record metrics
        duration_ms = (time.time() - start_time) * 1000
        if metrics_collector:
            metrics_collector.record_request(
                endpoint=request.url.path,
                duration_ms=duration_ms,
                status_code=response.status_code
            )
        
        # Log response
        if structured_logger:
            structured_logger.log_response(response.status_code, duration_ms, request.url.path)
        
        return response
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        
        # Record error metrics
        if metrics_collector:
            metrics_collector.record_request(
                endpoint=request.url.path,
                duration_ms=duration_ms,
                status_code=500,
                error=str(type(e).__name__)
            )
        
        # Log error
        if structured_logger:
            structured_logger.log_error(e, {"path": request.url.path})
        
        raise


# Add CORS validation middleware
app.middleware("http")(cors_validation_middleware)

# Add CORS middleware to allow frontend to communicate
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
allowed_origins = [origin.strip() for origin in allowed_origins if origin.strip()]

logger.info(f"CORS allowed origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint."""
    logger.info("Root endpoint called")
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
    global security_manager, structured_logger
    
    if not query_engine:
        logger.error("Chat request failed: VISTA not initialized")
        raise HTTPException(status_code=503, detail="VISTA not initialized")
    
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    try:
        logger.info(f"Processing query: {request.message[:100]}...")
        
        # If a specific LLM provider is requested, create a new LLM client
        if request.llm_provider:
            logger.info(f"Using LLM provider: {request.llm_provider}")
            config = Config.from_env()
            
            # Get the API key and model for the requested provider
            if request.llm_provider == "openai":
                api_key = config.openai_api_key
                model = os.getenv("OpenAI_MODEL", "gpt-4o-mini")
            elif request.llm_provider == "gemini":
                api_key = config.gemini_api_key
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
        if hasattr(result, 'answer'):
            response_text = result.answer
            sources = None
            if hasattr(result, 'sources') and result.sources:
                sources = [
                    SourceDocument(
                        text=src.text if hasattr(src, 'text') else str(src),
                        source=src.source if hasattr(src, 'source') else None
                    )
                    for src in result.sources
                ]
        elif isinstance(result, str):
            response_text = result
            sources = None
        elif isinstance(result, dict):
            response_text = result.get('answer') or result.get('response') or str(result)
            sources = None
        else:
            response_text = str(result)
            sources = None
        
        logger.info("Query processed successfully")
        
        return ChatResponse(
            response=response_text,
            sources=sources
        )
        
    except Exception as e:
        logger.error(f"Error processing query: {type(e).__name__}: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Sanitize error message before sending to client
        sanitized_error = security_manager.sanitize_error_message(e) if security_manager else str(e)
        
        raise HTTPException(status_code=500, detail=f"Error processing query: {sanitized_error}")


@app.get("/health")
async def health():
    """Basic health check - always returns 200 if server is running."""
    logger.info("Health check endpoint called")
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "vista_initialized": query_engine is not None
        }
    )


@app.get("/ready")
async def readiness_check():
    """Detailed readiness check endpoint."""
    global health_checker
    
    logger.info("Readiness check endpoint called")
    
    if not health_checker:
        logger.warning("Readiness check: Health checker not initialized")
        return JSONResponse(
            status_code=200,  # Return 200 for Render, but indicate not ready in body
            content={
                "status": "degraded",
                "message": "Health checker not initialized",
                "ready": False
            }
        )
    
    try:
        health_status = health_checker.check_health()
        logger.info(f"Health status: {health_status.status}")
        
        # Always return 200 for Render health checks
        return JSONResponse(
            status_code=200,
            content={
                **health_status.to_dict(),
                "ready": health_status.status == "healthy"
            }
        )
    except Exception as e:
        logger.error(f"Error in readiness check: {e}")
        return JSONResponse(
            status_code=200,
            content={
                "status": "error",
                "message": str(e),
                "ready": False
            }
        )


@app.get("/metrics")
async def get_metrics():
    """Metrics endpoint for monitoring."""
    global metrics_collector
    
    if not metrics_collector:
        return JSONResponse(
            status_code=503,
            content={"error": "Metrics collector not initialized"}
        )
    
    metrics = metrics_collector.get_metrics()
    
    return JSONResponse(
        status_code=200,
        content={
            "total_requests": metrics.total_requests,
            "total_errors": metrics.total_errors,
            "average_response_time_ms": metrics.average_response_time_ms,
            "p50_response_time_ms": metrics.p50_response_time_ms,
            "p95_response_time_ms": metrics.p95_response_time_ms,
            "p99_response_time_ms": metrics.p99_response_time_ms,
            "error_rate": metrics.error_rate,
            "uptime_seconds": metrics.uptime_seconds,
            "requests_by_endpoint": metrics.requests_by_endpoint,
            "errors_by_type": metrics.errors_by_type
        }
    )


if __name__ == "__main__":
    # Log startup info
    logger.info("=" * 50)
    logger.info("STARTING UVICORN SERVER")
    logger.info("=" * 50)
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"Port: {os.getenv('PORT', '8000')}")
    logger.info(f"Log Level: {os.getenv('LOG_LEVEL', 'info')}")
    logger.info("=" * 50)
    
    # Run the server
    is_production = os.getenv("ENVIRONMENT", "development") == "production"
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=not is_production,
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )