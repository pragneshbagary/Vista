"""Text chunking functionality for the Vista."""

import re
from typing import List
import logging

from vista.models import Document, Chunk

logger = logging.getLogger(__name__)


class TextChunker:
    """Splits documents into semantically coherent chunks with overlap."""
    
    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        """Initialize chunker with size and overlap parameters.
        
        Args:
            chunk_size: Maximum size of each chunk in characters
            overlap: Number of characters to overlap between consecutive chunks
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        
        if overlap >= chunk_size:
            raise ValueError("Overlap must be less than chunk_size")
        if overlap < 0:
            raise ValueError("Overlap must be non-negative")
        if chunk_size <= 0:
            raise ValueError("Chunk size must be positive")
    
    def chunk_document(self, document: Document) -> List[Chunk]:
        """Split document into overlapping chunks.
        
        Args:
            document: Document to chunk
            
        Returns:
            List of Chunk objects
        """
        text = document.content
        
        # Handle edge case: document smaller than chunk size
        if len(text) <= self.chunk_size:
            return [
                Chunk(
                    text=text,
                    document_id=document.file_path,
                    chunk_index=0,
                    metadata={
                        'file_path': document.file_path,
                        'category': document.category,
                        'filename': document.filename
                    }
                )
            ]
        
        # Split text into chunks respecting sentence boundaries
        chunks = []
        chunk_index = 0
        start = 0
        
        while start < len(text):
            # Calculate end position for this chunk
            end = min(start + self.chunk_size, len(text))
            
            # If this is not the last chunk, try to find a sentence boundary
            if end < len(text):
                chunk_text = self._split_on_sentences(text[start:end])
            else:
                # Last chunk - take everything remaining
                chunk_text = text[start:]
            
            # Prevent infinite loop - ensure we make progress
            if len(chunk_text) == 0:
                # No sentence boundary found, take the full chunk
                chunk_text = text[start:end]
            
            # Create chunk with metadata
            chunk = Chunk(
                text=chunk_text,
                document_id=document.file_path,
                chunk_index=chunk_index,
                metadata={
                    'file_path': document.file_path,
                    'category': document.category,
                    'filename': document.filename
                }
            )
            chunks.append(chunk)
            
            # Move start position forward, accounting for overlap
            # Ensure we always make progress (move at least 1 character forward)
            advance = max(1, len(chunk_text) - self.overlap)
            start = start + advance
            chunk_index += 1
        
        logger.info(f"Chunked document {document.filename} into {len(chunks)} chunks")
        return chunks
    
    def _split_on_sentences(self, text: str) -> str:
        """Split text respecting sentence boundaries.
        
        This method finds the best sentence boundary within the text to split on.
        It looks for periods, question marks, exclamation marks, or newlines.
        
        Args:
            text: Text to split
            
        Returns:
            Text up to the last sentence boundary, or full text if no boundary found
        """
        # Look for sentence boundaries: . ! ? followed by space or newline, or just newline
        # We search from the end backwards to find the last sentence boundary
        
        # Pattern matches: period/question/exclamation followed by whitespace, or newline
        sentence_endings = [
            (r'\.\s', '.'),
            (r'\?\s', '?'),
            (r'!\s', '!'),
            (r'\n', '\n')
        ]
        
        best_split = -1
        
        for pattern, _ in sentence_endings:
            # Find all matches
            for match in re.finditer(pattern, text):
                # We want the position after the sentence ending
                pos = match.end()
                if pos > best_split:
                    best_split = pos
        
        # If we found a sentence boundary, split there
        if best_split > 0:
            return text[:best_split].rstrip()
        
        # No sentence boundary found - return the full text
        return text
