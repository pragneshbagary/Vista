"""Vector store management for the Vista."""

from typing import List, Optional, Dict, Any
import logging
import os
from pinecone import Pinecone, ServerlessSpec

from .models import Chunk, RetrievedChunk

logger = logging.getLogger(__name__)


class VectorStoreManager:
    """Manages Pinecone vector store for storing and retrieving embeddings.
    
    Pinecone is a cloud-native vector database for production deployments.
    """
    
    def __init__(self, api_key: Optional[str] = None, environment: Optional[str] = None, 
                 index_name: str = "vista-vectors", namespace: str = "default"):
        """Initialize Pinecone client with cloud configuration.
        
        Args:
            api_key: Pinecone API key (optional, falls back to env var)
            environment: Pinecone environment (optional, falls back to env var)
            index_name: Name of the index (default: vista-vectors)
            namespace: Namespace for multi-tenancy (default: default)
            
        Raises:
            RuntimeError: If Pinecone authentication fails
            ValueError: If required credentials are missing
        """
        self.api_key = api_key or os.getenv('PINECONE_API_KEY')
        self.environment = environment or os.getenv('PINECONE_ENVIRONMENT')
        self.index_name = index_name or os.getenv('PINECONE_INDEX_NAME', 'vista-vectors')
        self.namespace = namespace or os.getenv('PINECONE_NAMESPACE', 'default')
        
        self.client = self._initialize_client()
        self.index = None
        
        # Initialize index if it exists, otherwise create_collection will handle it
        if self.index_name:
             # Just set it, connection happens on demand or in create_collection
             pass
             
        logger.info("Initialized Pinecone client")
    
    def _initialize_client(self) -> Pinecone:
        """Initialize Pinecone client with API credentials.
        
        Returns:
            Pinecone client instance
            
        Raises:
            RuntimeError: If authentication fails
            ValueError: If required credentials are missing
        """
        if not self.api_key:
            raise ValueError(
                "Pinecone API key is required. Set PINECONE_API_KEY env var or pass to constructor."
            )
        
        if not self.environment:
            raise ValueError(
                "Pinecone environment is required. Set PINECONE_ENVIRONMENT env var or pass to constructor."
            )
        
        try:
            logger.info(f"Connecting to Pinecone with environment: {self.environment}")
            client = Pinecone(api_key=self.api_key)
            logger.info("Successfully authenticated with Pinecone")
            return client
        except Exception as e:
            logger.error(f"Pinecone authentication failed: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to authenticate with Pinecone: {str(e)}")
    
    def create_collection(self, collection_name: str = None) -> None:
        """Create or get Pinecone index.
        
        Args:
            collection_name: Name of the index (optional, uses default if None)
            
        Raises:
            RuntimeError: If Pinecone API call fails
        """
        if collection_name:
            self.index_name = collection_name
        
        if not self.index_name:
             raise ValueError("Index name must be provided either in constructor or create_collection")

        try:
            # Check if index already exists
            indexes = self.client.list_indexes()
            index_names = [idx.name for idx in indexes]
            
            if self.index_name in index_names:
                logger.info(f"Retrieved existing index: {self.index_name}")
                self.index = self.client.Index(self.index_name)
            else:
                # Create new index with cosine similarity and dimension 1536 (default for text-embedding-ada-002)
                # Note: For free tier users, they might need to use 'gcp-starter' region or similar, 
                # but 'serverless' with 'aws' is standard for paid.
                # Use the environment variable for region/cloud if strict control is needed, 
                # but Pinecone Python SDK v3+ usually handles this with just Index creation if serverless.
                # However, ServerlessSpec is good practice.
                
                logger.info(f"Creating new index: {self.index_name}")
                self.client.create_index(
                    name=self.index_name,
                    dimension=1536, # TODO: Make this configurable based on embedding model if needed
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1" # Default to us-east-1 for serverless if not specified
                    )
                )
                logger.info(f"Created new index: {self.index_name}")
                self.index = self.client.Index(self.index_name)
        except Exception as e:
            logger.error(f"Failed to manage index '{self.index_name}': {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to manage index '{self.index_name}': {str(e)}")
    
    def add_chunks(self, chunks: List[Chunk], embeddings: List[List[float]]) -> None:
        """Add chunks with embeddings to Pinecone index.
        
        Args:
            chunks: List of chunks to add
            embeddings: Corresponding embeddings (1536-dimensional for OpenAI)
            
        Raises:
            RuntimeError: If index not initialized
            ValueError: If chunks and embeddings counts don't match
        """
        if self.index is None:
            raise RuntimeError("Collection not initialized. Call create_collection() first.")
        
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks must match number of embeddings")
        
        if not chunks:
            logger.warning("No chunks to add")
            return
        
        try:
            # Prepare vectors for Pinecone
            vectors_to_upsert = []
            
            for i, chunk in enumerate(chunks):
                # Create unique ID combining document_id and chunk_index
                vector_id = f"{chunk.document_id}_{chunk.chunk_index}"
                
                # Prepare metadata
                metadata = chunk.metadata.copy()
                metadata["document_id"] = chunk.document_id
                metadata["chunk_index"] = str(chunk.chunk_index)
                metadata["text"] = chunk.text
                
                # Create vector tuple (id, values, metadata)
                vectors_to_upsert.append((
                    vector_id,
                    embeddings[i],
                    metadata
                ))
            
            # Batch upsert to Pinecone
            self.index.upsert(
                vectors=vectors_to_upsert,
                namespace=self.namespace
            )
            
            logger.info(f"Added {len(chunks)} vectors to index")
        except Exception as e:
            logger.error(f"Failed to add chunks: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to add chunks: {str(e)}")
    
    def query(self, query_embedding: List[float], n_results: int = 5) -> List[RetrievedChunk]:
        """Query Pinecone index for similar chunks.
        
        Args:
            query_embedding: Query embedding vector
            n_results: Number of results to return
            
        Returns:
            List of RetrievedChunk objects with similarity scores
            
        Raises:
            RuntimeError: If index not initialized
        """
        if self.index is None:
            raise RuntimeError("Collection not initialized. Call create_collection() first.")
        
        try:
            # Query the index
            results = self.index.query(
                vector=query_embedding,
                top_k=n_results,
                namespace=self.namespace,
                include_metadata=True
            )
            
            # Convert results to RetrievedChunk objects
            retrieved_chunks = []
            
            for match in results.matches:
                metadata = match.metadata.copy() if match.metadata else {}
                
                # Extract text from metadata (stored during add_chunks)
                text = metadata.pop("text", "")
                
                # Pinecone score is already in 0-1 range for cosine similarity
                similarity_score = match.score
                
                retrieved_chunk = RetrievedChunk(
                    text=text,
                    metadata=metadata,
                    similarity_score=similarity_score
                )
                retrieved_chunks.append(retrieved_chunk)
            
            logger.info(f"Retrieved {len(retrieved_chunks)} vectors from query")
            return retrieved_chunks
        except Exception as e:
            logger.error(f"Query failed: {str(e)}", exc_info=True)
            raise RuntimeError(f"Query failed: {str(e)}")
    
    def reset_collection(self) -> None:
        """Delete and recreate Pinecone index.
        
        Raises:
            RuntimeError: If index operations fail
        """
        if self.index_name is None:
            logger.warning("No index to reset")
            return
        
        try:
            # Delete the existing index
            logger.info(f"Deleting index: {self.index_name}")
            self.client.delete_index(self.index_name)
            logger.info(f"Deleted index: {self.index_name}")
            
            # Recreate the index
            logger.info(f"Recreating index: {self.index_name}")
            self.client.create_index(
                name=self.index_name,
                dimension=384,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )
            logger.info(f"Recreated index: {self.index_name}")
            self.index = self.client.Index(self.index_name)
        except Exception as e:
            logger.error(f"Failed to reset collection: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to reset collection: {str(e)}")
    
    def get_collection_count(self) -> int:
        """Get number of vectors in current index.
        
        Returns:
            Number of vectors in the index
        """
        if self.index is None:
            return 0
        
        try:
            # Get index statistics
            stats = self.index.describe_index_stats()
            
            # Get count from namespace
            if self.namespace in stats.namespaces:
                return stats.namespaces[self.namespace].vector_count
            else:
                return 0
        except Exception as e:
            logger.error(f"Failed to get collection count: {str(e)}", exc_info=True)
            return 0
