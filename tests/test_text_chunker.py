"""Tests for text chunking functionality."""

import pytest
from echo.text_chunker import TextChunker
from echo.models import Document


def test_chunk_small_document():
    """Test chunking a document smaller than chunk size."""
    chunker = TextChunker(chunk_size=500, overlap=50)
    doc = Document(
        content="This is a small document.",
        file_path="/test/file.txt",
        category="test",
        filename="file.txt"
    )
    
    chunks = chunker.chunk_document(doc)
    
    assert len(chunks) == 1
    assert chunks[0].text == "This is a small document."
    assert chunks[0].document_id == "/test/file.txt"
    assert chunks[0].chunk_index == 0
    assert chunks[0].metadata['category'] == "test"


def test_chunk_large_document():
    """Test chunking a document larger than chunk size."""
    chunker = TextChunker(chunk_size=50, overlap=10)
    
    # Create a document with multiple sentences
    content = "This is sentence one. This is sentence two. This is sentence three. This is sentence four."
    doc = Document(
        content=content,
        file_path="/test/file.txt",
        category="test",
        filename="file.txt"
    )
    
    chunks = chunker.chunk_document(doc)
    
    # Should have multiple chunks
    assert len(chunks) > 1
    
    # All chunks should have the same document_id
    for chunk in chunks:
        assert chunk.document_id == "/test/file.txt"
    
    # Chunk indices should be sequential
    for i, chunk in enumerate(chunks):
        assert chunk.chunk_index == i


def test_chunk_respects_sentence_boundaries():
    """Test that chunks respect sentence boundaries."""
    chunker = TextChunker(chunk_size=50, overlap=5)
    
    content = "First sentence. Second sentence. Third sentence."
    doc = Document(
        content=content,
        file_path="/test/file.txt",
        category="test",
        filename="file.txt"
    )
    
    chunks = chunker.chunk_document(doc)
    
    # Check that no chunk splits a sentence in the middle
    for chunk in chunks:
        # If chunk contains a period, it should be at a sentence boundary
        if '.' in chunk.text and not chunk.text.endswith('.'):
            # Period should be followed by space (sentence boundary)
            assert '. ' in chunk.text or '.\n' in chunk.text


def test_chunk_metadata_preservation():
    """Test that metadata is preserved in chunks."""
    chunker = TextChunker(chunk_size=50, overlap=10)
    
    doc = Document(
        content="A" * 200,  # Long document
        file_path="/data/projects/test.txt",
        category="projects",
        filename="test.txt"
    )
    
    chunks = chunker.chunk_document(doc)
    
    for chunk in chunks:
        assert chunk.metadata['file_path'] == "/data/projects/test.txt"
        assert chunk.metadata['category'] == "projects"
        assert chunk.metadata['filename'] == "test.txt"


def test_invalid_parameters():
    """Test that invalid parameters raise errors."""
    with pytest.raises(ValueError):
        TextChunker(chunk_size=50, overlap=60)  # overlap >= chunk_size
    
    with pytest.raises(ValueError):
        TextChunker(chunk_size=50, overlap=-1)  # negative overlap
    
    with pytest.raises(ValueError):
        TextChunker(chunk_size=0, overlap=0)  # zero chunk_size
