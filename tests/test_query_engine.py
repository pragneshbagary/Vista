"""Tests for the QueryEngine class."""

import pytest
from unittest.mock import Mock, MagicMock

from vista.query_engine import QueryEngine
from vista.models import RetrievedChunk, QueryResponse


class TestQueryEngine:
    """Test cases for QueryEngine class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_vector_store = Mock()
        self.mock_embedding_gen = Mock()
        self.mock_llm_client = Mock()
        
        self.query_engine = QueryEngine(
            vector_store=self.mock_vector_store,
            embedding_gen=self.mock_embedding_gen,
            llm_client=self.mock_llm_client,
            max_context_tokens=1000
        )
    
    def test_query_with_results(self):
        """Test query processing with retrieved results."""
        # Setup mocks
        question = "What is my experience?"
        query_embedding = [0.1, 0.2, 0.3]
        
        retrieved_chunks = [
            RetrievedChunk(
                text="I have 5 years of software development experience.",
                metadata={"category": "experience", "filename": "work.txt"},
                similarity_score=0.9
            ),
            RetrievedChunk(
                text="I worked at Tech Corp as a senior developer.",
                metadata={"category": "experience", "filename": "work.txt"},
                similarity_score=0.8
            )
        ]
        
        self.mock_embedding_gen.generate_embedding.return_value = query_embedding
        self.mock_vector_store.query.return_value = retrieved_chunks
        self.mock_llm_client.generate_response.return_value = "Based on the context, you have 5 years of software development experience and worked at Tech Corp as a senior developer."
        
        # Execute query
        result = self.query_engine.query(question, n_results=5)
        
        # Verify calls
        self.mock_embedding_gen.generate_embedding.assert_called_once_with(question)
        self.mock_vector_store.query.assert_called_once_with(query_embedding, 5)
        self.mock_llm_client.generate_response.assert_called_once()
        
        # Verify result
        assert isinstance(result, QueryResponse)
        assert result.query == question
        assert result.sources == retrieved_chunks
        assert "5 years of software development experience" in result.answer
    
    def test_query_no_results(self):
        """Test query processing when no results are found."""
        question = "What is my favorite color?"
        query_embedding = [0.1, 0.2, 0.3]
        
        self.mock_embedding_gen.generate_embedding.return_value = query_embedding
        self.mock_vector_store.query.return_value = []
        
        # Execute query
        result = self.query_engine.query(question)
        
        # Verify calls
        self.mock_embedding_gen.generate_embedding.assert_called_once_with(question)
        self.mock_vector_store.query.assert_called_once_with(query_embedding, 5)
        self.mock_llm_client.generate_response.assert_not_called()
        
        # Verify result
        assert isinstance(result, QueryResponse)
        assert result.query == question
        assert result.sources == []
        assert "don't have any relevant information" in result.answer
    
    def test_construct_prompt_with_context(self):
        """Test prompt construction with context chunks."""
        question = "What is my experience?"
        chunks = [
            RetrievedChunk(
                text="I have 5 years of experience.",
                metadata={"category": "experience", "filename": "work.txt"},
                similarity_score=0.9
            )
        ]
        
        prompt = self.query_engine._construct_prompt(question, chunks)
        
        assert question in prompt
        assert "I have 5 years of experience." in prompt
        assert "experience/work.txt" in prompt
        assert "Context 1" in prompt
    
    def test_construct_prompt_no_context(self):
        """Test prompt construction with no context."""
        question = "What is my experience?"
        chunks = []
        
        prompt = self.query_engine._construct_prompt(question, chunks)
        
        assert question in prompt
        assert "No relevant context found" in prompt
    
    def test_limit_context_size(self):
        """Test context size limiting."""
        # Create chunks that would exceed the limit
        large_chunks = [
            RetrievedChunk(
                text="A" * 1000,  # Large chunk
                metadata={},
                similarity_score=0.9
            ),
            RetrievedChunk(
                text="B" * 1000,  # Another large chunk
                metadata={},
                similarity_score=0.8
            ),
            RetrievedChunk(
                text="C" * 100,   # Small chunk
                metadata={},
                similarity_score=0.7
            )
        ]
        
        # With max_context_tokens=1000, available_chars should be ~2000
        # First chunk (1000 + 100 overhead) should fit, second might not
        limited = self.query_engine._limit_context_size(large_chunks)
        
        # Should have at least one chunk, but not necessarily all
        assert len(limited) >= 1
        assert len(limited) <= len(large_chunks)
    
    def test_query_error_handling(self):
        """Test error handling in query processing."""
        question = "What is my experience?"
        
        # Mock an exception during embedding generation
        self.mock_embedding_gen.generate_embedding.side_effect = Exception("Embedding failed")
        
        result = self.query_engine.query(question)
        
        # Should return error response instead of raising exception
        assert isinstance(result, QueryResponse)
        assert result.query == question
        assert result.sources == []
        assert "error" in result.answer.lower()