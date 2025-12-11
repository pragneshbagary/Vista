"""Query engine for the Vista."""

from typing import List
import logging

from vista.models import QueryResponse, RetrievedChunk
from vista.vector_store import VectorStoreManager
from vista.embedding_generator import EmbeddingGenerator
from vista.llm_base import BaseLLMClient
logger = logging.getLogger(__name__)


class QueryEngine:
    """Processes user queries and orchestrates retrieval and generation."""
    
    def __init__(
        self,
        vector_store: VectorStoreManager,
        embedding_gen: EmbeddingGenerator,
        llm_client: BaseLLMClient,
        max_context_tokens: int = 3000
    ):
        """Initialize with dependencies.
        
        Args:
            vector_store: Vector store manager
            embedding_gen: Embedding generator
            llm_client: LLM client
            max_context_tokens: Maximum tokens for context
        """
        self.vector_store = vector_store
        self.embedding_gen = embedding_gen
        self.llm_client = llm_client
        self.max_context_tokens = max_context_tokens
    
    def query(self, question: str, n_results: int = 5) -> QueryResponse:
        """Process question and return response with sources.
        
        Args:
            question: User question
            n_results: Number of chunks to retrieve
            
        Returns:
            QueryResponse with answer and sources
        """
        logger.info(f"Processing query: {question[:100]}...")
        
        try:
            # Step 1: Generate embedding for the query
            logger.debug("Generating query embedding")
            query_embedding = self.embedding_gen.generate_embedding(question)
            
            # Step 2: Retrieve relevant chunks from vector store
            logger.debug(f"Retrieving {n_results} similar chunks")
            retrieved_chunks = self.vector_store.query(query_embedding, n_results)
            
            # Step 3: Handle case where no relevant context is found
            if not retrieved_chunks:
                logger.warning("No relevant chunks found for query")
                return QueryResponse(
                    answer="I don't have any relevant information to answer your question.",
                    sources=[],
                    query=question
                )
            
            # Step 4: Limit context size to fit within token limits
            logger.debug("Limiting context size")
            limited_chunks = self._limit_context_size(retrieved_chunks)
            
            # Step 5: Construct prompt with context
            logger.debug("Constructing prompt")
            prompt = self._construct_prompt(question, limited_chunks)
            
            # Step 6: Generate response using LLM
            logger.debug("Generating LLM response")
            answer = self.llm_client.generate_response(prompt)
            
            logger.info("Query processed successfully")
            return QueryResponse(
                answer=answer,
                sources=limited_chunks,
                query=question
            )
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return QueryResponse(
                answer=f"I encountered an error while processing your question: {str(e)}",
                sources=[],
                query=question
            )
    
    def _construct_prompt(self, question: str, context_chunks: List[RetrievedChunk]) -> str:
        """Build prompt with retrieved context.
        
        Args:
            question: User question
            context_chunks: Retrieved context chunks
            
        Returns:
            Constructed prompt
        """
        if not context_chunks:
            return f"""Please answer the following question. If you don't have enough information, say so clearly.

Question: {question}

Context: No relevant context found."""
        
        # Build context section from chunks
        context_parts = []
        for i, chunk in enumerate(context_chunks, 1):
            # Include source information in context
            source_info = ""
            if chunk.metadata:
                category = chunk.metadata.get("category", "unknown")
                filename = chunk.metadata.get("filename", "unknown")
                source_info = f" (Source: {category}/{filename})"
            
            context_parts.append(f"Context {i}{source_info}:\n{chunk.text}")
        
        context_text = "\n\n".join(context_parts)
        
        prompt = f"""Please answer the following question based only on the provided context. If the context doesn't contain enough information to answer the question, say so clearly. Always cite which context sections you used in your answer.

Question: {question}

{context_text}

Answer:"""
        
        return prompt
    
    def _limit_context_size(self, chunks: List[RetrievedChunk]) -> List[RetrievedChunk]:
        """Limit the total context size to fit within LLM token limits.
        
        Args:
            chunks: Retrieved chunks to limit
            
        Returns:
            Limited list of chunks that fit within token limits
        """
        if not chunks:
            return chunks
        
        # Rough estimation: 1 token ≈ 4 characters for English text
        # Reserve some tokens for the prompt structure and question
        available_tokens = self.max_context_tokens - 500  # Reserve 500 tokens for prompt overhead
        available_chars = available_tokens * 4
        
        limited_chunks = []
        current_chars = 0
        
        for chunk in chunks:
            # Estimate characters needed for this chunk (text + metadata formatting)
            chunk_chars = len(chunk.text) + 100  # Add overhead for formatting
            
            if current_chars + chunk_chars <= available_chars:
                limited_chunks.append(chunk)
                current_chars += chunk_chars
            else:
                # Stop adding chunks if we would exceed the limit
                logger.debug(f"Context size limit reached. Using {len(limited_chunks)} out of {len(chunks)} chunks")
                break
        
        if not limited_chunks and chunks:
            # If even the first chunk is too large, include it anyway but truncate
            logger.warning("First chunk exceeds context limit, truncating")
            first_chunk = chunks[0]
            max_chunk_chars = available_chars - 100  # Leave room for formatting
            
            if len(first_chunk.text) > max_chunk_chars:
                truncated_text = first_chunk.text[:max_chunk_chars] + "..."
                truncated_chunk = RetrievedChunk(
                    text=truncated_text,
                    metadata=first_chunk.metadata,
                    similarity_score=first_chunk.similarity_score
                )
                limited_chunks = [truncated_chunk]
            else:
                limited_chunks = [first_chunk]
        
        return limited_chunks
