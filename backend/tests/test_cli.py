"""Tests for the CLI class."""

import pytest
from unittest.mock import Mock, patch
from io import StringIO

from vista.cli import CLI
from vista.models import QueryResponse, RetrievedChunk


class TestCLI:
    """Test cases for CLI class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_query_engine = Mock()
        self.cli = CLI(query_engine=self.mock_query_engine)
    
    def test_init(self):
        """Test CLI initialization."""
        assert self.cli.query_engine == self.mock_query_engine
        assert self.cli.running is True
        assert self.cli.last_response is None
    
    def test_parse_exit_command(self):
        """Test parsing exit command."""
        self.cli._parse_and_execute_command("exit")
        assert self.cli.running is False
    
    def test_parse_quit_command(self):
        """Test parsing quit command."""
        self.cli._parse_and_execute_command("quit")
        assert self.cli.running is False
    
    def test_parse_ask_command(self):
        """Test parsing ask command."""
        # Setup mock response
        mock_response = QueryResponse(
            answer="Test answer",
            sources=[],
            query="test question"
        )
        self.mock_query_engine.query.return_value = mock_response
        
        with patch('builtins.print') as mock_print:
            self.cli._parse_and_execute_command("ask test question")
        
        # Verify query engine was called
        self.mock_query_engine.query.assert_called_once_with("test question")
        
        # Verify response was stored
        assert self.cli.last_response == mock_response
    
    def test_parse_direct_question(self):
        """Test parsing direct question without 'ask' prefix."""
        # Setup mock response
        mock_response = QueryResponse(
            answer="Test answer",
            sources=[],
            query="what is my name"
        )
        self.mock_query_engine.query.return_value = mock_response
        
        with patch('builtins.print') as mock_print:
            self.cli._parse_and_execute_command("what is my name")
        
        # Verify query engine was called
        self.mock_query_engine.query.assert_called_once_with("what is my name")
    
    def test_handle_sources_no_previous_response(self):
        """Test sources command with no previous response."""
        with patch('builtins.print') as mock_print:
            self.cli._handle_sources()
        
        mock_print.assert_called_with("No previous response available. Ask a question first.")
    
    def test_handle_sources_with_response(self):
        """Test sources command with previous response."""
        # Setup previous response with sources
        sources = [
            RetrievedChunk(
                text="Test content",
                metadata={"category": "test", "filename": "test.txt"},
                similarity_score=0.9
            )
        ]
        self.cli.last_response = QueryResponse(
            answer="Test answer",
            sources=sources,
            query="test query"
        )
        
        with patch('builtins.print') as mock_print:
            self.cli._handle_sources()
        
        # Should display sources
        mock_print.assert_called()
    
    def test_display_response_with_sources(self):
        """Test displaying response with sources."""
        sources = [
            RetrievedChunk(
                text="Test content",
                metadata={"category": "experience", "filename": "work.txt"},
                similarity_score=0.9
            )
        ]
        response = QueryResponse(
            answer="Test answer about experience",
            sources=sources,
            query="test query"
        )
        
        with patch('builtins.print') as mock_print:
            self.cli._display_response(response)
        
        # Should print answer and source information
        mock_print.assert_called()
    
    def test_display_response_no_sources(self):
        """Test displaying response without sources."""
        response = QueryResponse(
            answer="Test answer",
            sources=[],
            query="test query"
        )
        
        with patch('builtins.print') as mock_print:
            self.cli._display_response(response)
        
        # Should print answer and no sources message
        mock_print.assert_called()
    
    def test_display_sources(self):
        """Test displaying detailed source information."""
        sources = [
            RetrievedChunk(
                text="This is test content for the source display.",
                metadata={"category": "projects", "filename": "project1.txt"},
                similarity_score=0.85
            ),
            RetrievedChunk(
                text="Another piece of content from a different source.",
                metadata={"category": "skills", "filename": "skills.txt"},
                similarity_score=0.75
            )
        ]
        
        with patch('builtins.print') as mock_print:
            self.cli._display_sources(sources)
        
        # Should print detailed source information
        mock_print.assert_called()
    
    def test_handle_help(self):
        """Test help command."""
        with patch('builtins.print') as mock_print:
            self.cli._handle_help()
        
        # Should print help information
        mock_print.assert_called()
    
    def test_handle_rebuild(self):
        """Test rebuild command."""
        with patch('builtins.print') as mock_print:
            self.cli._handle_rebuild()
        
        # Should print rebuild information
        mock_print.assert_called()