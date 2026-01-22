"""Persistence management for the Vista vector database."""

import os
import shutil
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class PersistenceManager:
    """Manages vector database persistence, backups, and recovery."""
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        """Initialize persistence manager.
        
        Args:
            persist_directory: Directory for database persistence
        """
        self.persist_directory = Path(persist_directory)
        self.metadata_file = self.persist_directory / "backup_metadata.json"
    
    def ensure_persistence_directory(self) -> None:
        """Create persistence directory if it doesn't exist.
        
        Raises:
            PermissionError: If directory cannot be created or is not writable
            OSError: If other OS-level errors occur
        """
        try:
            # Create directory if it doesn't exist
            self.persist_directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Persistence directory ensured at {self.persist_directory}")
            
            # Validate directory is writable
            self._validate_directory_writable()
            
        except PermissionError as e:
            error_msg = f"Permission denied: Cannot create or access persistence directory at {self.persist_directory}"
            logger.error(error_msg)
            raise PermissionError(error_msg) from e
        except OSError as e:
            error_msg = f"OS error while creating persistence directory: {e}"
            logger.error(error_msg)
            raise OSError(error_msg) from e
    
    def _validate_directory_writable(self) -> None:
        """Validate that the persistence directory is writable.
        
        Raises:
            PermissionError: If directory is not writable
        """
        if not os.access(self.persist_directory, os.W_OK):
            error_msg = f"Persistence directory is not writable: {self.persist_directory}"
            logger.error(error_msg)
            raise PermissionError(error_msg)
        
        logger.debug(f"Persistence directory is writable: {self.persist_directory}")
    
    def backup_database(self, backup_path: str) -> Dict[str, Any]:
        """Create backup of vector database.
        
        Args:
            backup_path: Path where backup should be stored
            
        Returns:
            Dictionary with backup metadata including timestamp and file count
            
        Raises:
            FileNotFoundError: If persistence directory doesn't exist
            PermissionError: If backup directory is not writable
            OSError: If backup operation fails
        """
        backup_path = Path(backup_path)
        
        try:
            # Validate source directory exists
            if not self.persist_directory.exists():
                error_msg = f"Persistence directory does not exist: {self.persist_directory}"
                logger.error(error_msg)
                raise FileNotFoundError(error_msg)
            
            # Create backup directory
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Validate backup directory is writable
            if not os.access(backup_path.parent, os.W_OK):
                error_msg = f"Backup directory is not writable: {backup_path.parent}"
                logger.error(error_msg)
                raise PermissionError(error_msg)
            
            # Remove existing backup if it exists
            if backup_path.exists():
                shutil.rmtree(backup_path)
                logger.debug(f"Removed existing backup at {backup_path}")
            
            # Copy entire persistence directory
            shutil.copytree(self.persist_directory, backup_path)
            
            # Count files in backup
            file_count = sum(1 for _ in backup_path.rglob("*") if _.is_file())
            
            # Create metadata
            metadata = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "backup_path": str(backup_path),
                "source_path": str(self.persist_directory),
                "file_count": file_count
            }
            
            logger.info(f"Database backup created at {backup_path} with {file_count} files")
            return metadata
            
        except (FileNotFoundError, PermissionError) as e:
            logger.error(f"Backup failed: {e}")
            raise
        except OSError as e:
            error_msg = f"OS error during backup: {e}"
            logger.error(error_msg)
            raise OSError(error_msg) from e
    
    def restore_database(self, backup_path: str) -> Dict[str, Any]:
        """Restore vector database from backup.
        
        Args:
            backup_path: Path to backup to restore from
            
        Returns:
            Dictionary with restore metadata including timestamp and file count
            
        Raises:
            FileNotFoundError: If backup doesn't exist
            ValueError: If backup integrity check fails
            OSError: If restore operation fails
        """
        backup_path = Path(backup_path)
        
        try:
            # Validate backup exists
            if not backup_path.exists():
                error_msg = f"Backup does not exist: {backup_path}"
                logger.error(error_msg)
                raise FileNotFoundError(error_msg)
            
            # Verify backup integrity
            self._verify_backup_integrity(backup_path)
            
            # Backup current database if it exists
            if self.persist_directory.exists():
                temp_backup = self.persist_directory.parent / f"{self.persist_directory.name}_temp_backup"
                shutil.copytree(self.persist_directory, temp_backup)
                logger.debug(f"Created temporary backup of current database at {temp_backup}")
                
                # Remove current database
                shutil.rmtree(self.persist_directory)
            
            # Restore from backup
            shutil.copytree(backup_path, self.persist_directory)
            
            # Count files in restored database
            file_count = sum(1 for _ in self.persist_directory.rglob("*") if _.is_file())
            
            # Create metadata
            metadata = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "backup_path": str(backup_path),
                "restore_path": str(self.persist_directory),
                "file_count": file_count
            }
            
            logger.info(f"Database restored from {backup_path} with {file_count} files")
            return metadata
            
        except (FileNotFoundError, ValueError) as e:
            logger.error(f"Restore failed: {e}")
            raise
        except OSError as e:
            error_msg = f"OS error during restore: {e}"
            logger.error(error_msg)
            raise OSError(error_msg) from e
    
    def _verify_backup_integrity(self, backup_path: Path) -> None:
        """Verify backup integrity before restore.
        
        Args:
            backup_path: Path to backup to verify
            
        Raises:
            ValueError: If backup is corrupted or invalid
        """
        if not backup_path.is_dir():
            raise ValueError(f"Backup is not a directory: {backup_path}")
        
        # Check for required ChromaDB files
        required_files = ["chroma.sqlite3"]
        found_files = [f.name for f in backup_path.iterdir() if f.is_file()]
        
        # At least one required file should exist
        has_required = any(req in found_files for req in required_files)
        
        if not has_required and not any(backup_path.iterdir()):
            raise ValueError(f"Backup appears to be empty: {backup_path}")
        
        logger.debug(f"Backup integrity verified: {backup_path}")
    
    def verify_database_integrity(self) -> bool:
        """Verify database integrity.
        
        Returns:
            True if database is valid, False otherwise
        """
        try:
            if not self.persist_directory.exists():
                logger.warning(f"Database directory does not exist: {self.persist_directory}")
                return False
            
            # Check for required ChromaDB files
            required_files = ["chroma.sqlite3"]
            found_files = [f.name for f in self.persist_directory.iterdir() if f.is_file()]
            
            # At least one required file should exist
            has_required = any(req in found_files for req in required_files)
            
            if not has_required and not any(self.persist_directory.iterdir()):
                logger.warning(f"Database directory appears to be empty: {self.persist_directory}")
                return False
            
            logger.debug(f"Database integrity verified: {self.persist_directory}")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying database integrity: {e}")
            return False
    
    def rebuild_database(self, documents_path: str) -> None:
        """Rebuild database from source documents.
        
        This method removes the current database and signals that it needs
        to be rebuilt from source documents.
        
        Args:
            documents_path: Path to source documents for rebuilding
            
        Raises:
            FileNotFoundError: If documents path doesn't exist
            OSError: If rebuild operation fails
        """
        documents_path = Path(documents_path)
        
        try:
            # Validate documents path exists
            if not documents_path.exists():
                error_msg = f"Documents path does not exist: {documents_path}"
                logger.error(error_msg)
                raise FileNotFoundError(error_msg)
            
            # Backup current database before rebuild
            if self.persist_directory.exists():
                backup_dir = self.persist_directory.parent / f"{self.persist_directory.name}_pre_rebuild_backup"
                if backup_dir.exists():
                    shutil.rmtree(backup_dir)
                shutil.copytree(self.persist_directory, backup_dir)
                logger.info(f"Created pre-rebuild backup at {backup_dir}")
                
                # Remove current database
                shutil.rmtree(self.persist_directory)
                logger.info(f"Removed database for rebuild: {self.persist_directory}")
            
            # Create empty persistence directory
            self.ensure_persistence_directory()
            
            logger.info(f"Database rebuild initiated. Ready to load documents from {documents_path}")
            
        except (FileNotFoundError, OSError) as e:
            logger.error(f"Rebuild failed: {e}")
            raise
