#!/usr/bin/env python3
"""Main application entry point for the Personal AI RAG System."""

import logging
import sys
from pathlib import Path
from typing import List

from echo.config import Config
from echo.document_loader import DocumentLoader
from echo.text_chunker import TextChunker
from echo.embedding_generator import EmbeddingGenerator
from echo.vector_store import VectorStoreManager
from echo.llm_factory import LLMFactory
from echo.query_engine import QueryEngine
from echo.cli import CLI
from echo.models import Document, Chunk


def setup_logging() -> None:
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def initialize_system(config: Config) -> QueryEngine:
    """Initialize all system components and build the knowledge base.
    
    Args:
        config: System configuration
        
    Returns:
        Initialized QueryEngine ready for queries
        
    Raises:
        Exception: If initialization fails
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting Echo....")
        logger.info(f"Using LLM Provider: {config.llm_provider}")
        logger.info(f"Using LLM Model: {config.llm_model}")
        
        # Step 1: Initialize core components
        logger.info("Initializing core components...")
        
        # Initialize document loader
        document_loader = DocumentLoader()
        
        # Initialize text chunker
        text_chunker = TextChunker(
            chunk_size=config.chunk_size,
            overlap=config.chunk_overlap
        )
        
        # Initialize embedding generator
        embedding_generator = EmbeddingGenerator(model_name=config.embedding_model)
        
        # Initialize vector store
        vector_store = VectorStoreManager(persist_directory=config.persist_directory)
        vector_store.create_collection("personal_knowledge")
        
        # Initialize LLM client using factory
        llm_client = LLMFactory.create_llm_client(
            provider=config.llm_provider,
            api_key=config.get_api_key(),
            model=config.llm_model
        )
        
        # Initialize query engine
        query_engine = QueryEngine(
            vector_store=vector_store,
            embedding_gen=embedding_generator,
            llm_client=llm_client,
            max_context_tokens=config.max_context_tokens
        )
        
        logger.info("Core components initialized successfully")
        
        # Step 2: Check if we need to build the knowledge base
        existing_count = vector_store.get_collection_count()
        if existing_count > 0:
            logger.info(f"Found existing knowledge base with {existing_count} chunks")
            return query_engine
        
        logger.info("Building knowledge base from documents...")
        
        # Step 3: Load documents
        logger.info(f"Loading documents from {config.data_directory}...")
        documents = document_loader.load_documents(config.data_directory)
        
        if not documents:
            raise Exception(f"No documents found in {config.data_directory}. Please check the data directory.")
        
        logger.info(f"Loaded {len(documents)} documents")
        
        # Step 4: Chunk documents
        logger.info("Chunking documents...")
        all_chunks: List[Chunk] = []
        
        for document in documents:
            chunks = text_chunker.chunk_document(document)
            all_chunks.extend(chunks)
        
        if not all_chunks:
            raise Exception("No chunks generated from documents")
        
        logger.info(f"Generated {len(all_chunks)} chunks")
        
        # Step 5: Generate embeddings
        logger.info("Generating embeddings...")
        chunk_texts = [chunk.text for chunk in all_chunks]
        embeddings = embedding_generator.generate_batch_embeddings(chunk_texts)
        
        logger.info(f"Generated {len(embeddings)} embeddings")
        
        # Step 6: Store in vector database
        logger.info("Storing chunks and embeddings in vector database...")
        vector_store.add_chunks(all_chunks, embeddings)
        
        logger.info("Knowledge base built successfully")
        logger.info(f"System ready with {len(all_chunks)} chunks from {len(documents)} documents")
        
        return query_engine
        
    except Exception as e:
        logger.error(f"System initialization failed: {e}")
        raise


def main() -> None:
    """Main application entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = Config.from_env()
        logger.info("Configuration loaded successfully")
        
        # Validate data directory exists
        data_path = Path(config.data_directory)
        if not data_path.exists():
            logger.error(f"Data directory does not exist: {config.data_directory}")
            print(f"Error: Data directory '{config.data_directory}' not found.")
            print("Please create the data directory and add your text files.")
            sys.exit(1)
        
        # Initialize system
        query_engine = initialize_system(config)
        
        # Start CLI interface
        logger.info("Starting CLI interface...")
        cli = CLI(query_engine)
        cli.run()
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        print("\nApplication stopped by user.")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Application failed: {e}")
        print(f"Error: {e}")
        print("\nPlease check the logs and configuration, then try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()