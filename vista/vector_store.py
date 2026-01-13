"""Vector store management for the Vista."""

from typing import List, Optional
import logging
import os
import chromadb
from chromadb.config import Settings

from vista.models import Chunk, RetrievedChunk

logger = logging.getLogger(__name__)


class VectorStoreManager:
    """Manages ChromaDB vector store for storing and retrieving embeddings.
    
    Supports both local persistence and Chroma Cloud for production deployments.
    """
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        """Initialize ChromaDB client with persistence or cloud.
        
        Args:
            persist_directory: Directory for local ChromaDB persistence
            
        Environment Variables:
            CHROMA_API_IMPL: Set to 'rest' to use Chroma Cloud
            CHROMA_SERVER_HOST: Chroma Cloud host (default: api.trychroma.com)
            CHROMA_SERVER_HTTP_PORT: Chroma Cloud port (default: 443)
            CHROMA_SERVER_SSL_ENABLED: Enable SSL (default: true)
            CHROMA_TENANT: Chroma Cloud tenant ID
            CHROMA_API_KEY: Chroma Cloud API key
        """
        self.persist_directory = persist_directory
        self.client = self._initialize_client()
        self.collection: Optional[chromadb.Collection] = None
        logger.info("Initialized ChromaDB client")
    
    def _initialize_client(self):
        """Initialize ChromaDB client based on configuration.
        
        Returns:
            ChromaDB client (local or cloud)
        """
        # Check if using Chroma Cloud
        if os.getenv('CHROMA_API_IMPL') == 'rest':
            logger.info("Using Chroma Cloud for vector storage")
            
            # Get Chroma Cloud configuration
            host = os.getenv('CHROMA_SERVER_HOST', 'api.trychroma.com')
            port = int(os.getenv('CHROMA_SERVER_HTTP_PORT', 443))
            ssl_enabled = os.getenv('CHROMA_SERVER_SSL_ENABLED', 'true').lower() == 'true'
            tenant = os.getenv('CHROMA_TENANT')
            api_key = os.getenv('CHROMA_API_KEY')
            
            if not tenant or not api_key:
                raise ValueError(
                    "CHROMA_TENANT and CHROMA_API_KEY environment variables are required "
                    "when using Chroma Cloud (CHROMA_API_IMPL=rest)"
                )
            
            # Create HTTP client for Chroma Cloud
            client = chromadb.HttpClient(
                host=host,
                port=port,
                ssl=ssl_enabled,
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'X-Chroma-Tenant': tenant
                }
            )
            logger.info(f"Connected to Chroma Cloud at {host}:{port}")
            return client
        else:
            # Use local persistence
            logger.info(f"Using local ChromaDB persistence at {self.persist_directory}")
            return chromadb.PersistentClient(path=self.persist_directory)
    
    def create_collection(self, collection_name: str) -> None:
        """Create or get collection.
        
        Args:
            collection_name: Name of the collection
        """
        try:
            # Try to get existing collection first
            self.collection = self.client.get_collection(name=collection_name)
            logger.info(f"Retrieved existing collection: {collection_name}")
        except Exception:
            # Collection doesn't exist, create it
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}  # Use cosine similarity
            )
            logger.info(f"Created new collection: {collection_name}")
    
    def add_chunks(self, chunks: List[Chunk], embeddings: List[List[float]]) -> None:
        """Add chunks with embeddings to collection.
        
        Args:
            chunks: List of chunks to add
            embeddings: Corresponding embeddings
        """
        if self.collection is None:
            raise RuntimeError("Collection not initialized. Call create_collection() first.")
        
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks must match number of embeddings")
        
        if not chunks:
            logger.warning("No chunks to add")
            return
        
        # Prepare data for ChromaDB
        ids = []
        documents = []
        metadatas = []
        
        for i, chunk in enumerate(chunks):
            # Create unique ID combining document_id and chunk_index
            chunk_id = f"{chunk.document_id}_{chunk.chunk_index}"
            ids.append(chunk_id)
            documents.append(chunk.text)
            
            # Prepare metadata (ChromaDB requires string values)
            metadata = chunk.metadata.copy()
            metadata["document_id"] = chunk.document_id
            metadata["chunk_index"] = str(chunk.chunk_index)
            metadatas.append(metadata)
        
        # Add to collection
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        
        logger.info(f"Added {len(chunks)} chunks to collection")
    
    def query(self, query_embedding: List[float], n_results: int = 5) -> List[RetrievedChunk]:
        """Query vector store for similar chunks.
        
        Args:
            query_embedding: Query embedding vector
            n_results: Number of results to return
            
        Returns:
            List of retrieved chunks with similarity scores
        """
        if self.collection is None:
            raise RuntimeError("Collection not initialized. Call create_collection() first.")
        
        # Query the collection
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        # Convert results to RetrievedChunk objects
        retrieved_chunks = []
        
        if results["documents"] and results["documents"][0]:
            documents = results["documents"][0]
            metadatas = results["metadatas"][0] if results["metadatas"] else []
            distances = results["distances"][0] if results["distances"] else []
            
            for i, document in enumerate(documents):
                # Convert distance to similarity score (cosine distance -> cosine similarity)
                # ChromaDB returns distances, we want similarity scores
                distance = distances[i] if i < len(distances) else 1.0
                similarity_score = 1.0 - distance  # Convert distance to similarity
                
                metadata = metadatas[i] if i < len(metadatas) else {}
                
                retrieved_chunk = RetrievedChunk(
                    text=document,
                    metadata=metadata,
                    similarity_score=similarity_score
                )
                retrieved_chunks.append(retrieved_chunk)
        
        logger.info(f"Retrieved {len(retrieved_chunks)} chunks for query")
        return retrieved_chunks
    
    def reset_collection(self) -> None:
        """Delete and recreate collection."""
        if self.collection is None:
            logger.warning("No collection to reset")
            return
        
        collection_name = self.collection.name
        
        try:
            # Delete the existing collection
            self.client.delete_collection(name=collection_name)
            logger.info(f"Deleted collection: {collection_name}")
        except Exception:
            # Collection might not exist
            logger.warning(f"Collection {collection_name} not found for deletion")
        
        # Recreate the collection
        self.collection = self.client.create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"Recreated collection: {collection_name}")
    
    def get_collection_count(self) -> int:
        """Get the number of items in the collection.
        
        Returns:
            Number of items in the collection
        """
        if self.collection is None:
            return 0
        
        return self.collection.count()
