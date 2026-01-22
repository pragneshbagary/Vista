"""Pytest configuration and shared fixtures."""

import pytest
from pathlib import Path


@pytest.fixture
def test_data_dir(tmp_path):
    """Create a temporary test data directory."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def test_persist_dir(tmp_path):
    """Create a temporary persistence directory."""
    persist_dir = tmp_path / "chroma_db"
    persist_dir.mkdir()
    return persist_dir
