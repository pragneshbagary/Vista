"""Document loading functionality for the Personal AI RAG System."""

from pathlib import Path
from typing import List, Dict
import logging

from echo.models import Document

logger = logging.getLogger(__name__)


class DocumentLoader:
    """Loads and parses text files from a directory structure."""
    
    def load_documents(self, data_dir: str) -> List[Document]:
        """Load all text files from directory recursively.
        
        Args:
            data_dir: Path to the data directory
            
        Returns:
            List of Document objects
        """
        documents = []
        data_path = Path(data_dir)
        
        if not data_path.exists():
            logger.error(f"Data directory does not exist: {data_dir}")
            return documents
        
        # Recursively find all .txt files
        for file_path in data_path.rglob("*.txt"):
            try:
                # Read file content
                content = file_path.read_text(encoding='utf-8')
                
                # Extract metadata
                metadata = self._extract_metadata(str(file_path))
                
                # Create Document object
                document = Document(
                    content=content,
                    file_path=str(file_path),
                    category=metadata['category'],
                    filename=metadata['filename']
                )
                documents.append(document)
                logger.info(f"Loaded document: {file_path}")
                
            except Exception as e:
                # Log error and continue with remaining files
                logger.error(f"Failed to load file {file_path}: {e}")
                continue
        
        logger.info(f"Successfully loaded {len(documents)} documents")
        return documents
    
    def _extract_metadata(self, file_path: str) -> Dict[str, str]:
        """Extract category and metadata from file path.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary containing metadata (category, filename)
        """
        path = Path(file_path)
        filename = path.name
        
        # Extract category from parent directory
        # For example: data/projects/file.txt -> category: "projects"
        # For example: data/static/file.txt -> category: "static"
        parts = path.parts
        
        # Find the category (directory immediately after 'data')
        category = "unknown"
        for i, part in enumerate(parts):
            if part == "data" and i + 1 < len(parts):
                category = parts[i + 1]
                break
        
        return {
            'category': category,
            'filename': filename
        }
