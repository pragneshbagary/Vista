#!/usr/bin/env python3
"""FastAPI server for VISTA RAG system."""

import logging
import sys
import os
import time
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
    logger = structured_logger or logging.getLogger(__name__)
    global security_manager
    
    try:
        logger.log_request("INIT", "/startup") if hasattr(logger, 'log_request') else None
        logger.info("Starting Vista API Server...") if not hasattr(logger, 'log_request') else None
        
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
        vector_store = VectorStoreManager(
            api_key=config.pinecone_api_key,
            environment=config.pinecone_environment,
            index_name=config.pinecone_index_name,
            namespace=config.pinecone_namespace
        )
        vector_store.create_collection()
        
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
        # Sanitize error before logging
        if security_manager:
            sanitized_error = security_manager.sanitize_error_message(e)
        else:
            sanitized_error = str(e)
        logger.error(f"VISTA initialization failed: {sanitized_error}")
        raise


# Create FastAPI app
app = FastAPI(title="VISTA API", description="Personal RAG Chatbot API")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    global query_engine, security_manager, health_checker, metrics_collector, structured_logger
    
    # Startup
    config = Config.from_env()
    setup_structured_logging(config.log_level)
    structured_logger = StructuredLogger(__name__)
    
    try:
        structured_logger.info("Starting VISTA API Server...")
        
        # Initialize security manager with CORS whitelist
        security_manager = SecurityManager(config.allowed_origins)
        structured_logger.info(f"Security manager initialized with {len(config.allowed_origins)} allowed origins")
        
        # Initialize metrics collector
        metrics_collector = MetricsCollector()
        
        # Initialize VISTA
        query_engine = initialize_vista()
        
        # Initialize health checker
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
        
        structured_logger.info("VISTA API Server ready!")
    except Exception as e:
        if structured_logger:
            structured_logger.error(f"Failed to initialize VISTA: {e}")
        else:
            logging.error(f"Failed to initialize VISTA: {e}")
        sys.exit(1)
    
    yield
    
    # Shutdown
    if structured_logger:
        structured_logger.info("VISTA API Server shutting down...")


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
# In production, restrict to your specific domain
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
allowed_origins = [origin.strip() for origin in allowed_origins if origin.strip()]

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
        raise HTTPException(status_code=503, detail="VISTA not initialized")
    
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    try:
        logger = structured_logger or logging.getLogger(__name__)
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
        logger = structured_logger or logging.getLogger(__name__)
        logger.error(f"Error processing query: {e}")
        
        # Sanitize error message before sending to client
        sanitized_error = security_manager.sanitize_error_message(e) if security_manager else str(e)
        
        raise HTTPException(status_code=500, detail=f"Error processing query: {sanitized_error}")


@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/ready")
async def readiness_check():
    """Detailed health check endpoint."""
    global health_checker
    
    if not health_checker:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "message": "Health checker not initialized"}
        )
    
    health_status = health_checker.check_health()
    
    # Return appropriate HTTP status code based on health
    status_code = 200 if health_status.status == "healthy" else (503 if health_status.status == "unhealthy" else 200)
    
    return JSONResponse(
        status_code=status_code,
        content=health_status.to_dict()
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