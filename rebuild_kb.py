#!/usr/bin/env python3
"""Script to rebuild the knowledge base."""

import logging
import sys
from pathlib import Path

from vista.config import Config
from vista.document_loader import DocumentLoader
from vista.text_chunker import TextChunker
from vista.embedding_generator import EmbeddingGenerator
from vista.vector_store import VectorStoreManager


def setup_logging() -> None:
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def rebuild_knowledge_base() -> None:
    """Rebuild the knowledge base from scratch."""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting knowledge base rebuild...")
        
        # Load configuration
        config = Config.from_env()
        
        # Validate data directory
        data_path = Path(config.data_directory)
        if not data_path.exists():
            raise Exception(f"Data directory does not exist: {config.data_directory}")
        
        # Initialize components
        logger.info("Initializing components...")
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
        
        # Create collection (or get existing index)
        vector_store.create_collection()
        
        # Reset collection to clear old data
        logger.info("Clearing existing knowledge base...")
        vector_store.reset_collection()
        
        # Load documents
        logger.info(f"Loading documents from {config.data_directory}...")
        documents = document_loader.load_documents(config.data_directory)
        
        if not documents:
            raise Exception(f"No documents found in {config.data_directory}")
        
        logger.info(f"Loaded {len(documents)} documents")
        
        # Chunk documents
        logger.info("Chunking documents...")
        all_chunks = []
        for document in documents:
            chunks = text_chunker.chunk_document(document)
            all_chunks.extend(chunks)
        
        if not all_chunks:
            raise Exception("No chunks generated from documents")
        
        logger.info(f"Generated {len(all_chunks)} chunks")
        
        # Generate embeddings
        logger.info("Generating embeddings...")
        chunk_texts = [chunk.text for chunk in all_chunks]
        embeddings = embedding_generator.generate_batch_embeddings(chunk_texts)
        
        logger.info(f"Generated {len(embeddings)} embeddings")
        
        # Store in vector database
        logger.info("Storing chunks and embeddings...")
        vector_store.add_chunks(all_chunks, embeddings)
        
        logger.info("Knowledge base rebuild completed successfully!")
        logger.info(f"Total chunks: {len(all_chunks)} from {len(documents)} documents")
        
    except Exception as e:
        logger.error(f"Knowledge base rebuild failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    setup_logging()
    rebuild_knowledge_base()
