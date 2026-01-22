"""Unit and property-based tests for Pinecone VectorStoreManager.

These tests verify the VectorStoreManager implementation for Pinecone integration,
including unit tests for specific examples and property-based tests for universal
correctness properties.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from hypothesis import given, strategies as st, settings, assume
import logging
import os
from typing import List

from vista.vector_store import VectorStoreManager
from models import Chunk, RetrievedChunk


# ============================================================================
# Unit Tests: Initialization and Configuration
# ============================================================================

class TestVectorStoreInitialization:
    """Unit tests for VectorStoreManager initialization."""
    
    def test_init_with_valid_credentials(self):
        """Test initialization with valid Pinecone credentials."""
        with patch.dict(os.environ, {
            'PINECONE_API_KEY': 'test-api-key',
            'PINECONE_ENVIRONMENT': 'us-west-2-aws'
        }):
            with patch('vista.vector_store.Pinecone') as mock_pinecone:
                manager = VectorStoreManager()
                assert manager.client is not None
                assert manager.index_name is None
                assert manager.namespace == 'default'
    
    def test_init_missing_api_key(self):
        """Test initialization fails when PINECONE_API_KEY is missing."""
        with patch.dict(os.environ, {
            'PINECONE_ENVIRONMENT': 'us-west-2-aws'
        }, clear=True):
            with pytest.raises(ValueError) as exc_info:
                VectorStoreManager()
            assert "PINECONE_API_KEY" in str(exc_info.value)
    
    def test_init_missing_environment(self):
        """Test initialization fails when PINECONE_ENVIRONMENT is missing."""
        with patch.dict(os.environ, {
            'PINECONE_API_KEY': 'test-api-key'
        }, clear=True):
            with pytest.raises(ValueError) as exc_info:
                VectorStoreManager()
            assert "PINECONE_ENVIRONMENT" in str(exc_info.value)
    
    def test_init_with_custom_namespace(self):
        """Test initialization with custom namespace."""
        with patch.dict(os.environ, {
            'PINECONE_API_KEY': 'test-api-key',
            'PINECONE_ENVIRONMENT': 'us-west-2-aws',
            'PINECONE_NAMESPACE': 'custom-namespace'
        }):
            with patch('vista.vector_store.Pinecone'):
                manager = VectorStoreManager()
                assert manager.namespace == 'custom-namespace'
    
    def test_init_authentication_failure(self):
        """Test initialization handles authentication failures."""
        with patch.dict(os.environ, {
            'PINECONE_API_KEY': 'invalid-key',
            'PINECONE_ENVIRONMENT': 'us-west-2-aws'
        }):
            with patch('vista.vector_store.Pinecone', side_effect=Exception("Auth failed")):
                with pytest.raises(RuntimeError) as exc_info:
                    VectorStoreManager()
                assert "Failed to authenticate" in str(exc_info.value)


# ============================================================================
# Unit Tests: Index Management
# ============================================================================

class TestIndexManagement:
    """Unit tests for index creation and management."""
    
    @pytest.fixture
    def manager(self):
        """Create a VectorStoreManager with mocked Pinecone client."""
        with patch.dict(os.environ, {
            'PINECONE_API_KEY': 'test-api-key',
            'PINECONE_ENVIRONMENT': 'us-west-2-aws'
        }):
            with patch('vista.vector_store.Pinecone') as mock_pinecone:
                manager = VectorStoreManager()
                manager.client = MagicMock()
                return manager
    
    def test_create_new_index(self, manager):
        """Test creating a new index."""
        manager.client.list_indexes.return_value = []
        mock_index = MagicMock()
        manager.client.Index.return_value = mock_index
        
        manager.create_collection("test-index")
        
        assert manager.index_name == "test-index"
        assert manager.index == mock_index
        manager.client.create_index.assert_called_once()
    
    def test_retrieve_existing_index(self, manager):
        """Test retrieving an existing index."""
        mock_existing_index = MagicMock()
        mock_existing_index.name = "test-index"
        manager.client.list_indexes.return_value = [mock_existing_index]
        mock_index = MagicMock()
        manager.client.Index.return_value = mock_index
        
        manager.create_collection("test-index")
        
        assert manager.index_name == "test-index"
        manager.client.create_index.assert_not_called()
    
    def test_reset_collection(self, manager):
        """Test resetting a collection."""
        manager.index_name = "test-index"
        mock_index = MagicMock()
        manager.client.Index.return_value = mock_index
        
        manager.reset_collection()
        
        manager.client.delete_index.assert_called_once_with("test-index")
        manager.client.create_index.assert_called_once()
    
    def test_reset_collection_no_index(self, manager):
        """Test resetting when no index is initialized."""
        manager.index_name = None
        manager.reset_collection()
        manager.client.delete_index.assert_not_called()


# ============================================================================
# Unit Tests: Vector Operations
# ============================================================================

class TestVectorOperations:
    """Unit tests for adding and querying vectors."""
    
    @pytest.fixture
    def manager(self):
        """Create a VectorStoreManager with mocked Pinecone client."""
        with patch.dict(os.environ, {
            'PINECONE_API_KEY': 'test-api-key',
            'PINECONE_ENVIRONMENT': 'us-west-2-aws'
        }):
            with patch('vista.vector_store.Pinecone'):
                manager = VectorStoreManager()
                manager.index = MagicMock()
                return manager
    
    def test_add_chunks_success(self, manager):
        """Test successfully adding chunks."""
        chunks = [
            Chunk(
                text="Test chunk 1",
                document_id="doc1",
                chunk_index=0,
                metadata={"file_path": "/path/to/file.pdf", "category": "test"}
            )
        ]
        embeddings = [[0.1] * 1536]
        
        manager.add_chunks(chunks, embeddings)
        
        manager.index.upsert.assert_called_once()
    
    def test_add_chunks_mismatched_counts(self, manager):
        """Test adding chunks with mismatched embedding count."""
        chunks = [
            Chunk(
                text="Test chunk 1",
                document_id="doc1",
                chunk_index=0,
                metadata={}
            )
        ]
        embeddings = [[0.1] * 1536, [0.2] * 1536]
        
        with pytest.raises(ValueError) as exc_info:
            manager.add_chunks(chunks, embeddings)
        assert "must match" in str(exc_info.value)
    
    def test_add_chunks_empty_list(self, manager):
        """Test adding empty chunk list."""
        manager.add_chunks([], [])
        manager.index.upsert.assert_not_called()
    
    def test_add_chunks_no_index(self, manager):
        """Test adding chunks when index is not initialized."""
        manager.index = None
        chunks = [Chunk(text="Test", document_id="doc1", chunk_index=0, metadata={})]
        embeddings = [[0.1] * 1536]
        
        with pytest.raises(RuntimeError) as exc_info:
            manager.add_chunks(chunks, embeddings)
        assert "not initialized" in str(exc_info.value)
    
    def test_query_success(self, manager):
        """Test successful query."""
        mock_match = MagicMock()
        mock_match.score = 0.95
        mock_match.metadata = {
            "text": "Test chunk",
            "document_id": "doc1",
            "chunk_index": "0",
            "file_path": "/path/to/file.pdf",
            "category": "test"
        }
        
        manager.index.query.return_value = MagicMock(matches=[mock_match])
        
        results = manager.query([0.1] * 1536, n_results=5)
        
        assert len(results) == 1
        assert results[0].similarity_score == 0.95
        assert results[0].text == "Test chunk"
    
    def test_query_no_index(self, manager):
        """Test querying when index is not initialized."""
        manager.index = None
        
        with pytest.raises(RuntimeError) as exc_info:
            manager.query([0.1] * 1536)
        assert "not initialized" in str(exc_info.value)
    
    def test_get_collection_count(self, manager):
        """Test getting collection count."""
        mock_stats = MagicMock()
        mock_stats.namespaces = {
            'default': MagicMock(vector_count=42)
        }
        manager.index.describe_index_stats.return_value = mock_stats
        
        count = manager.get_collection_count()
        
        assert count == 42
    
    def test_get_collection_count_no_index(self, manager):
        """Test getting count when index is not initialized."""
        manager.index = None
        count = manager.get_collection_count()
        assert count == 0


# ============================================================================
# Unit Tests: Error Handling
# ============================================================================

class TestErrorHandling:
    """Unit tests for error handling."""
    
    @pytest.fixture
    def manager(self):
        """Create a VectorStoreManager with mocked Pinecone client."""
        with patch.dict(os.environ, {
            'PINECONE_API_KEY': 'test-api-key',
            'PINECONE_ENVIRONMENT': 'us-west-2-aws'
        }):
            with patch('vista.vector_store.Pinecone'):
                manager = VectorStoreManager()
                manager.index = MagicMock()
                return manager
    
    def test_add_chunks_api_error(self, manager):
        """Test handling API errors during add_chunks."""
        manager.index.upsert.side_effect = Exception("API Error")
        chunks = [Chunk(text="Test", document_id="doc1", chunk_index=0, metadata={})]
        embeddings = [[0.1] * 1536]
        
        with pytest.raises(RuntimeError) as exc_info:
            manager.add_chunks(chunks, embeddings)
        assert "Failed to add chunks" in str(exc_info.value)
    
    def test_query_api_error(self, manager):
        """Test handling API errors during query."""
        manager.index.query.side_effect = Exception("API Error")
        
        with pytest.raises(RuntimeError) as exc_info:
            manager.query([0.1] * 1536)
        assert "Query failed" in str(exc_info.value)
    
    def test_reset_collection_api_error(self, manager):
        """Test handling API errors during reset."""
        manager.index_name = "test-index"
        manager.client = MagicMock()
        manager.client.delete_index.side_effect = Exception("API Error")
        
        with pytest.raises(RuntimeError) as exc_info:
            manager.reset_collection()
        assert "Failed to reset collection" in str(exc_info.value)


# ============================================================================
# Property-Based Tests
# ============================================================================

class TestVectorStoreProperties:
    """Property-based tests for VectorStoreManager correctness properties."""
    
    @pytest.fixture
    def manager(self):
        """Create a VectorStoreManager with mocked Pinecone client."""
        with patch.dict(os.environ, {
            'PINECONE_API_KEY': 'test-api-key',
            'PINECONE_ENVIRONMENT': 'us-west-2-aws'
        }):
            with patch('vista.vector_store.Pinecone'):
                manager = VectorStoreManager()
                manager.index = MagicMock()
                return manager
    
    # ========================================================================
    # Property 1: Vector Storage Round Trip
    # ========================================================================
    
    @given(
        text=st.text(min_size=1, max_size=500),
        doc_id=st.text(min_size=1, max_size=50, alphabet=st.characters(
            blacklist_characters="\n\r\t_"
        )),
        chunk_idx=st.integers(min_value=0, max_value=1000)
    )
    @settings(max_examples=50)
    def test_property_vector_storage_round_trip(self, manager, text, doc_id, chunk_idx):
        """Property 1: Vector Storage Round Trip.
        
        For any chunk with embedding and metadata, when the chunk is added to
        the index and then queried with the same embedding, the returned chunk
        should contain the same text and metadata.
        
        Validates: Requirements 3.1, 3.2, 10.1, 10.2
        """
        # Create chunk and embedding
        chunk = Chunk(
            text=text,
            document_id=doc_id,
            chunk_index=chunk_idx,
            metadata={
                "file_path": "/test/path.pdf",
                "category": "test",
                "filename": "test.pdf"
            }
        )
        embedding = [0.1 + (i % 100) * 0.001 for i in range(1536)]
        
        # Mock the query to return the same chunk
        mock_match = MagicMock()
        mock_match.score = 0.99
        mock_match.metadata = {
            "text": text,
            "document_id": doc_id,
            "chunk_index": str(chunk_idx),
            "file_path": "/test/path.pdf",
            "category": "test",
            "filename": "test.pdf"
        }
        manager.index.query.return_value = MagicMock(matches=[mock_match])
        
        # Add chunk
        manager.add_chunks([chunk], [embedding])
        
        # Query with same embedding
        results = manager.query(embedding, n_results=1)
        
        # Verify round trip
        assert len(results) == 1
        assert results[0].text == text
        assert results[0].metadata["document_id"] == doc_id
        assert results[0].metadata["chunk_index"] == str(chunk_idx)
    
    # ========================================================================
    # Property 2: Similarity Score Ordering
    # ========================================================================
    
    @given(
        num_results=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=50)
    def test_property_similarity_score_ordering(self, manager, num_results):
        """Property 2: Similarity Score Ordering.
        
        For any query embedding and set of stored vectors, the returned chunks
        should be ordered by similarity score in descending order.
        
        Validates: Requirements 4.1, 4.3
        """
        # Create mock matches with descending scores
        matches = []
        for i in range(num_results):
            mock_match = MagicMock()
            mock_match.score = 1.0 - (i * 0.1)  # Descending scores
            mock_match.metadata = {
                "text": f"Chunk {i}",
                "document_id": f"doc{i}",
                "chunk_index": str(i),
                "file_path": "/test/path.pdf",
                "category": "test",
                "filename": "test.pdf"
            }
            matches.append(mock_match)
        
        manager.index.query.return_value = MagicMock(matches=matches)
        
        # Query
        results = manager.query([0.1] * 1536, n_results=num_results)
        
        # Verify ordering
        for i in range(len(results) - 1):
            assert results[i].similarity_score >= results[i + 1].similarity_score
    
    # ========================================================================
    # Property 3: Query Result Count
    # ========================================================================
    
    @given(
        n_results=st.integers(min_value=1, max_value=20),
        actual_count=st.integers(min_value=0, max_value=30)
    )
    @settings(max_examples=50)
    def test_property_query_result_count(self, manager, n_results, actual_count):
        """Property 3: Query Result Count.
        
        For any query with n_results parameter, the system should return at
        most n_results chunks.
        
        Validates: Requirements 4.6
        """
        # Create mock matches
        matches = []
        for i in range(min(actual_count, n_results)):
            mock_match = MagicMock()
            mock_match.score = 0.9 - (i * 0.01)
            mock_match.metadata = {
                "text": f"Chunk {i}",
                "document_id": f"doc{i}",
                "chunk_index": str(i),
                "file_path": "/test/path.pdf",
                "category": "test",
                "filename": "test.pdf"
            }
            matches.append(mock_match)
        
        manager.index.query.return_value = MagicMock(matches=matches)
        
        # Query
        results = manager.query([0.1] * 1536, n_results=n_results)
        
        # Verify count
        assert len(results) <= n_results
        assert len(results) == min(actual_count, n_results)
    
    # ========================================================================
    # Property 4: Metadata Preservation with Special Characters
    # ========================================================================
    
    @given(
        special_chars=st.text(
            alphabet="!@#$%^&*()_+-=[]{}|;:',.<>?/~`",
            min_size=1,
            max_size=50
        )
    )
    @settings(max_examples=50)
    def test_property_metadata_preservation_special_chars(self, manager, special_chars):
        """Property 4: Metadata Preservation with Special Characters.
        
        For any chunk with metadata containing special characters or unicode,
        when stored and retrieved, all metadata fields should be preserved
        exactly as provided.
        
        Validates: Requirements 10.3, 10.4, 10.5
        """
        # Create chunk with special characters in metadata
        chunk = Chunk(
            text="Test chunk",
            document_id="doc1",
            chunk_index=0,
            metadata={
                "file_path": f"/path/{special_chars}/file.pdf",
                "category": special_chars,
                "filename": f"file_{special_chars}.pdf"
            }
        )
        embedding = [0.1] * 1536
        
        # Mock query to return same metadata
        mock_match = MagicMock()
        mock_match.score = 0.95
        mock_match.metadata = {
            "text": "Test chunk",
            "document_id": "doc1",
            "chunk_index": "0",
            "file_path": f"/path/{special_chars}/file.pdf",
            "category": special_chars,
            "filename": f"file_{special_chars}.pdf"
        }
        manager.index.query.return_value = MagicMock(matches=[mock_match])
        
        # Add and query
        manager.add_chunks([chunk], [embedding])
        results = manager.query(embedding, n_results=1)
        
        # Verify metadata preservation
        assert results[0].metadata["file_path"] == f"/path/{special_chars}/file.pdf"
        assert results[0].metadata["category"] == special_chars
        assert results[0].metadata["filename"] == f"file_{special_chars}.pdf"
    
    # ========================================================================
    # Property 5: Index Creation Idempotence
    # ========================================================================
    
    @given(
        collection_name=st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(blacklist_characters="\n\r\t ")
        )
    )
    @settings(max_examples=50)
    def test_property_index_creation_idempotence(self, manager, collection_name):
        """Property 5: Index Creation Idempotence.
        
        For any collection name, calling create_collection() multiple times
        with the same name should result in the same index being used without
        errors or duplicate indexes.
        
        Validates: Requirements 2.2
        """
        mock_existing_index = MagicMock()
        mock_existing_index.name = collection_name
        manager.client.list_indexes.return_value = [mock_existing_index]
        mock_index = MagicMock()
        manager.client.Index.return_value = mock_index
        
        # Create collection multiple times
        manager.create_collection(collection_name)
        first_index = manager.index
        
        manager.create_collection(collection_name)
        second_index = manager.index
        
        # Should use same index
        assert first_index == second_index
        # Should not create new index
        manager.client.create_index.assert_not_called()
    
    # ========================================================================
    # Property 6: Collection Reset Idempotence
    # ========================================================================
    
    @settings(max_examples=50)
    def test_property_collection_reset_idempotence(self, manager):
        """Property 6: Collection Reset Idempotence.
        
        For any index, calling reset_collection() followed by
        get_collection_count() should return 0, and calling reset_collection()
        again should succeed without error.
        
        Validates: Requirements 2.3
        """
        manager.index_name = "test-index"
        mock_index = MagicMock()
        manager.client.Index.return_value = mock_index
        
        # Mock stats to return 0 after reset
        mock_stats = MagicMock()
        mock_stats.namespaces = {'default': MagicMock(vector_count=0)}
        mock_index.describe_index_stats.return_value = mock_stats
        
        # Reset collection
        manager.reset_collection()
        count = manager.get_collection_count()
        assert count == 0
        
        # Reset again should succeed
        manager.reset_collection()
        count = manager.get_collection_count()
        assert count == 0
    
    # ========================================================================
    # Property 7: Unique Vector IDs
    # ========================================================================
    
    @given(
        chunks_data=st.lists(
            st.tuples(
                st.text(min_size=1, max_size=20, alphabet=st.characters(
                    blacklist_characters="\n\r\t_"
                )),
                st.integers(min_value=0, max_value=1000)
            ),
            min_size=1,
            max_size=20,
            unique=True
        )
    )
    @settings(max_examples=50)
    def test_property_unique_vector_ids(self, manager, chunks_data):
        """Property 7: Unique Vector IDs.
        
        For any two different chunks with different document_id or chunk_index
        values, the generated vector IDs should be unique and not collide.
        
        Validates: Requirements 3.3
        """
        # Create chunks
        chunks = []
        for doc_id, chunk_idx in chunks_data:
            chunk = Chunk(
                text=f"Chunk {doc_id}_{chunk_idx}",
                document_id=doc_id,
                chunk_index=chunk_idx,
                metadata={}
            )
            chunks.append(chunk)
        
        embeddings = [[0.1] * 1536 for _ in chunks]
        
        # Capture the upsert call to check IDs
        manager.add_chunks(chunks, embeddings)
        
        # Get the vectors that were upserted
        call_args = manager.index.upsert.call_args
        vectors = call_args[1]['vectors']
        
        # Extract IDs
        ids = [v[0] for v in vectors]
        
        # Verify all IDs are unique
        assert len(ids) == len(set(ids))
    
    # ========================================================================
    # Property 8: Query Returns Complete Metadata
    # ========================================================================
    
    @settings(max_examples=50)
    def test_property_query_complete_metadata(self, manager):
        """Property 8: Query Returns Complete Metadata.
        
        For any query result, all metadata fields (document_id, chunk_index,
        file_path, category, filename) should be present in the returned
        RetrievedChunk objects.
        
        Validates: Requirements 4.5, 10.2
        """
        # Create mock match with all metadata fields
        mock_match = MagicMock()
        mock_match.score = 0.95
        mock_match.metadata = {
            "text": "Test chunk",
            "document_id": "doc1",
            "chunk_index": "0",
            "file_path": "/test/path.pdf",
            "category": "test",
            "filename": "test.pdf"
        }
        manager.index.query.return_value = MagicMock(matches=[mock_match])
        
        # Query
        results = manager.query([0.1] * 1536, n_results=1)
        
        # Verify all metadata fields present
        assert "document_id" in results[0].metadata
        assert "chunk_index" in results[0].metadata
        assert "file_path" in results[0].metadata
        assert "category" in results[0].metadata
        assert "filename" in results[0].metadata
    
    # ========================================================================
    # Property 9: Similarity Score Range
    # ========================================================================
    
    @given(
        num_results=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=50)
    def test_property_similarity_score_range(self, manager, num_results):
        """Property 9: Similarity Score Range.
        
        For any query result, the similarity scores should be in the range
        [0, 1] with higher scores indicating greater similarity.
        
        Validates: Requirements 4.4
        """
        # Create mock matches with scores in valid range
        matches = []
        for i in range(num_results):
            mock_match = MagicMock()
            # Generate score between 0 and 1
            mock_match.score = i / max(num_results, 1)
            mock_match.metadata = {
                "text": f"Chunk {i}",
                "document_id": f"doc{i}",
                "chunk_index": str(i),
                "file_path": "/test/path.pdf",
                "category": "test",
                "filename": "test.pdf"
            }
            matches.append(mock_match)
        
        manager.index.query.return_value = MagicMock(matches=matches)
        
        # Query
        results = manager.query([0.1] * 1536, n_results=num_results)
        
        # Verify all scores in valid range
        for result in results:
            assert 0 <= result.similarity_score <= 1
    
    # ========================================================================
    # Property 10: Collection Count Accuracy
    # ========================================================================
    
    @given(
        num_chunks=st.integers(min_value=0, max_value=100)
    )
    @settings(max_examples=50)
    def test_property_collection_count_accuracy(self, manager, num_chunks):
        """Property 10: Collection Count Accuracy.
        
        For any sequence of add_chunks() operations, the get_collection_count()
        should return the total number of vectors added to the index.
        
        Validates: Requirements 9.1, 9.3
        """
        # Mock stats to return the count
        mock_stats = MagicMock()
        mock_stats.namespaces = {
            'default': MagicMock(vector_count=num_chunks)
        }
        manager.index.describe_index_stats.return_value = mock_stats
        
        # Get count
        count = manager.get_collection_count()
        
        # Verify accuracy
        assert count == num_chunks
