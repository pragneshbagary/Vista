"""Data models for the Vista."""

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class Document:
    """Represents a loaded document with metadata.
    
    Attributes:
        content: The full text content of the document
        file_path: Path to the source file
        category: Category extracted from directory structure
        filename: Name of the source file
    """
    content: str
    file_path: str
    category: str
    filename: str


@dataclass
class Chunk:
    """Represents a chunk of text from a document.
    
    Attributes:
        text: The chunk text content
        document_id: Identifier of the source document
        chunk_index: Index of this chunk within the document
        metadata: Additional metadata (file_path, category, filename)
    """
    text: str
    document_id: str
    chunk_index: int
    metadata: Dict[str, str]


@dataclass
class RetrievedChunk:
    """Represents a chunk retrieved from the vector store.
    
    Attributes:
        text: The chunk text content
        metadata: Metadata associated with the chunk
        similarity_score: Similarity score from vector search
    """
    text: str
    metadata: Dict[str, str]
    similarity_score: float


@dataclass
class QueryResponse:
    """Represents a response to a user query.
    
    Attributes:
        answer: The generated answer from the LLM
        sources: List of chunks used as context
        query: The original user query
    """
    answer: str
    sources: List[RetrievedChunk]
    query: str
