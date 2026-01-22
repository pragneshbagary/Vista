"""Tests for persistence management."""

import pytest
import tempfile
import shutil
from pathlib import Path
from vista.persistence import PersistenceManager


@pytest.fixture
def temp_persist_dir():
    """Create a temporary persistence directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    if Path(temp_dir).exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def persistence_manager(temp_persist_dir):
    """Create a persistence manager with temporary directory."""
    return PersistenceManager(persist_directory=temp_persist_dir)


class TestPersistenceDirectoryManagement:
    """Test persistence directory management."""
    
    def test_ensure_persistence_directory_creates_directory(self, temp_persist_dir):
        """Test that ensure_persistence_directory creates the directory."""
        persist_dir = Path(temp_persist_dir) / "new_db"
        manager = PersistenceManager(persist_directory=str(persist_dir))
        
        assert not persist_dir.exists()
        manager.ensure_persistence_directory()
        assert persist_dir.exists()
        assert persist_dir.is_dir()
    
    def test_ensure_persistence_directory_idempotent(self, persistence_manager):
        """Test that ensure_persistence_directory is idempotent."""
        persistence_manager.ensure_persistence_directory()
        persistence_manager.ensure_persistence_directory()
        assert persistence_manager.persist_directory.exists()
    
    def test_ensure_persistence_directory_validates_writable(self, temp_persist_dir):
        """Test that ensure_persistence_directory validates directory is writable."""
        persist_dir = Path(temp_persist_dir) / "db"
        manager = PersistenceManager(persist_directory=str(persist_dir))
        manager.ensure_persistence_directory()
        
        # Should not raise
        assert manager.persist_directory.exists()
    
    def test_ensure_persistence_directory_permission_error(self):
        """Test that ensure_persistence_directory raises OSError for invalid paths."""
        # Try to create in a path that doesn't have write permissions
        manager = PersistenceManager(persist_directory="/root/invalid_path_12345")
        
        with pytest.raises((PermissionError, OSError)):
            manager.ensure_persistence_directory()


class TestDatabaseBackup:
    """Test database backup functionality."""
    
    def test_backup_database_creates_backup(self, persistence_manager, temp_persist_dir):
        """Test that backup_database creates a backup."""
        # Create some test files in persistence directory
        persistence_manager.ensure_persistence_directory()
        test_file = persistence_manager.persist_directory / "test.txt"
        test_file.write_text("test data")
        
        backup_dir = Path(temp_persist_dir) / "backup"
        metadata = persistence_manager.backup_database(str(backup_dir))
        
        assert backup_dir.exists()
        assert (backup_dir / "test.txt").exists()
        assert metadata["file_count"] == 1
        assert "timestamp" in metadata
    
    def test_backup_database_nonexistent_source(self, temp_persist_dir):
        """Test that backup_database raises FileNotFoundError for nonexistent source."""
        manager = PersistenceManager(persist_directory=str(Path(temp_persist_dir) / "nonexistent"))
        backup_dir = Path(temp_persist_dir) / "backup"
        
        with pytest.raises(FileNotFoundError):
            manager.backup_database(str(backup_dir))
    
    def test_backup_database_overwrites_existing(self, persistence_manager, temp_persist_dir):
        """Test that backup_database overwrites existing backup."""
        persistence_manager.ensure_persistence_directory()
        test_file = persistence_manager.persist_directory / "test.txt"
        test_file.write_text("test data")
        
        backup_dir = Path(temp_persist_dir) / "backup"
        
        # Create first backup
        metadata1 = persistence_manager.backup_database(str(backup_dir))
        assert metadata1["file_count"] == 1
        
        # Add another file
        test_file2 = persistence_manager.persist_directory / "test2.txt"
        test_file2.write_text("test data 2")
        
        # Create second backup (should overwrite)
        metadata2 = persistence_manager.backup_database(str(backup_dir))
        assert metadata2["file_count"] == 2


class TestDatabaseRestore:
    """Test database restore functionality."""
    
    def test_restore_database_from_backup(self, temp_persist_dir):
        """Test that restore_database restores from backup."""
        # Create initial database with files
        persist_dir = Path(temp_persist_dir) / "db"
        manager = PersistenceManager(persist_directory=str(persist_dir))
        manager.ensure_persistence_directory()
        test_file = persist_dir / "test.txt"
        test_file.write_text("test data")
        
        # Create backup
        backup_dir = Path(temp_persist_dir) / "backup"
        manager.backup_database(str(backup_dir))
        
        # Verify backup exists
        assert backup_dir.exists()
        assert (backup_dir / "test.txt").exists()
        
        # Modify original database
        test_file.write_text("modified data")
        
        # Restore from backup
        metadata = manager.restore_database(str(backup_dir))
        
        # Verify restored data
        assert test_file.read_text() == "test data"
        assert metadata["file_count"] == 1
    
    def test_restore_database_nonexistent_backup(self, persistence_manager, temp_persist_dir):
        """Test that restore_database raises FileNotFoundError for nonexistent backup."""
        backup_dir = Path(temp_persist_dir) / "nonexistent_backup"
        
        with pytest.raises(FileNotFoundError):
            persistence_manager.restore_database(str(backup_dir))
    
    def test_restore_database_corrupted_backup(self, persistence_manager, temp_persist_dir):
        """Test that restore_database raises ValueError for corrupted backup."""
        # Create an empty backup directory
        backup_dir = Path(temp_persist_dir) / "corrupted_backup"
        backup_dir.mkdir()
        
        with pytest.raises(ValueError):
            persistence_manager.restore_database(str(backup_dir))


class TestDatabaseIntegrityVerification:
    """Test database integrity verification."""
    
    def test_verify_database_integrity_empty_directory(self, persistence_manager):
        """Test that verify_database_integrity returns False for empty directory."""
        persistence_manager.ensure_persistence_directory()
        assert persistence_manager.verify_database_integrity() is False
    
    def test_verify_database_integrity_with_files(self, persistence_manager):
        """Test that verify_database_integrity returns True with valid files."""
        persistence_manager.ensure_persistence_directory()
        
        # Create a mock ChromaDB file
        db_file = persistence_manager.persist_directory / "chroma.sqlite3"
        db_file.write_text("mock database")
        
        assert persistence_manager.verify_database_integrity() is True
    
    def test_verify_database_integrity_nonexistent_directory(self, temp_persist_dir):
        """Test that verify_database_integrity returns False for nonexistent directory."""
        manager = PersistenceManager(persist_directory=str(Path(temp_persist_dir) / "nonexistent"))
        assert manager.verify_database_integrity() is False


class TestDatabaseRebuild:
    """Test database rebuild functionality."""
    
    def test_rebuild_database_removes_existing(self, persistence_manager, temp_persist_dir):
        """Test that rebuild_database removes existing database."""
        # Create initial database
        persistence_manager.ensure_persistence_directory()
        test_file = persistence_manager.persist_directory / "test.txt"
        test_file.write_text("test data")
        
        # Create documents directory
        docs_dir = Path(temp_persist_dir) / "documents"
        docs_dir.mkdir()
        (docs_dir / "doc.txt").write_text("document")
        
        # Rebuild
        persistence_manager.rebuild_database(str(docs_dir))
        
        # Verify old database is gone
        assert not test_file.exists()
        # Verify new empty database is created
        assert persistence_manager.persist_directory.exists()
    
    def test_rebuild_database_nonexistent_documents(self, persistence_manager, temp_persist_dir):
        """Test that rebuild_database raises FileNotFoundError for nonexistent documents."""
        docs_dir = Path(temp_persist_dir) / "nonexistent_docs"
        
        with pytest.raises(FileNotFoundError):
            persistence_manager.rebuild_database(str(docs_dir))
    
    def test_rebuild_database_creates_backup(self, persistence_manager, temp_persist_dir):
        """Test that rebuild_database creates a backup of existing database."""
        # Create initial database
        persistence_manager.ensure_persistence_directory()
        test_file = persistence_manager.persist_directory / "test.txt"
        test_file.write_text("test data")
        
        # Create documents directory
        docs_dir = Path(temp_persist_dir) / "documents"
        docs_dir.mkdir()
        (docs_dir / "doc.txt").write_text("document")
        
        # Rebuild
        persistence_manager.rebuild_database(str(docs_dir))
        
        # Verify backup exists
        backup_dir = persistence_manager.persist_directory.parent / f"{persistence_manager.persist_directory.name}_pre_rebuild_backup"
        assert backup_dir.exists()
        assert (backup_dir / "test.txt").exists()
