"""CLI interface for the Personal AI RAG System."""

import logging
import signal
import sys
from typing import Optional

from echo.query_engine import QueryEngine
from echo.models import QueryResponse

logger = logging.getLogger(__name__)


class CLI:
    """Command-line interface for user interaction."""
    
    def __init__(self, query_engine: QueryEngine):
        """Initialize CLI with query engine.
        
        Args:
            query_engine: Query engine instance
        """
        self.query_engine = query_engine
        self.running = True
        self.last_response: Optional[QueryResponse] = None
        
        # Set up graceful shutdown handling
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def run(self) -> None:
        """Start interactive CLI loop."""
        print("=" * 60)
        print("ECHO")
        print("=" * 60)
        print("Ask me questions about Pragnesh Bagary!")
        print("\nAvailable commands:")
        print("  ask <question>  - Ask a question")
        print("  sources         - Show sources from last response")
        print("  rebuild         - Rebuild the knowledge base")
        print("  help            - Show this help message")
        print("  exit            - Exit the application")
        print("\nYou can also just type your question directly.")
        print("-" * 60)
        
        while self.running:
            try:
                # Get user input
                user_input = input("\n> ").strip()
                
                if not user_input:
                    continue
                
                # Parse and execute command
                self._parse_and_execute_command(user_input)
                
            except EOFError:
                # Handle Ctrl+D
                print("\nGoodbye!")
                break
            except KeyboardInterrupt:
                # Handle Ctrl+C
                print("\nUse 'exit' to quit gracefully.")
                continue
            except Exception as e:
                logger.error(f"Unexpected error in CLI loop: {e}")
                print(f"An unexpected error occurred: {e}")
                print("Please try again or type 'exit' to quit.")
    
    def _parse_and_execute_command(self, user_input: str) -> None:
        """Parse user input and execute the appropriate command.
        
        Args:
            user_input: Raw user input string
        """
        # Convert to lowercase for command matching
        input_lower = user_input.lower().strip()
        
        # Handle explicit commands
        if input_lower == "exit" or input_lower == "quit":
            self._handle_exit()
        elif input_lower == "help":
            self._handle_help()
        elif input_lower == "sources":
            self._handle_sources()
        elif input_lower == "rebuild":
            self._handle_rebuild()
        elif input_lower.startswith("ask "):
            # Extract question after "ask "
            question = user_input[4:].strip()
            if question:
                self._handle_ask(question)
            else:
                print("Please provide a question after 'ask'.")
        else:
            # Treat any other input as a direct question
            self._handle_ask(user_input)
    
    def _handle_ask(self, question: str) -> None:
        """Handle ask command by processing the question.
        
        Args:
            question: User question to process
        """
        print(f"\nProcessing your question: {question}")
        print("-" * 40)
        
        try:
            # Query the engine
            response = self.query_engine.query(question)
            self.last_response = response
            
            # Display the response
            self._display_response(response)
            
        except Exception as e:
            logger.error(f"Error processing question: {e}")
            print(f"Sorry, I encountered an error while processing your question: {e}")
    
    def _handle_sources(self) -> None:
        """Handle sources command by showing sources from last response."""
        if self.last_response is None:
            print("No previous response available. Ask a question first.")
            return
        
        if not self.last_response.sources:
            print("No sources were used for the last response.")
            return
        
        print(f"\nSources used for: '{self.last_response.query}'")
        print("=" * 50)
        self._display_sources(self.last_response.sources)
    
    def _handle_rebuild(self) -> None:
        """Handle rebuild command by rebuilding the knowledge base."""
        print("\nRebuilding knowledge base...")
        print("Note: This feature requires restarting the application with fresh data.")
        print("Please restart the application to rebuild the knowledge base.")
    
    def _handle_help(self) -> None:
        """Handle help command by showing available commands."""
        print("\nAvailable commands:")
        print("  ask <question>  - Ask a question about Pragnesh Bagary")
        print("  sources         - Show source documents from the last response")
        print("  rebuild         - Rebuild the knowledge base (requires restart)")
        print("  help            - Show this help message")
        print("  exit            - Exit the application")
        print("\nYou can also just type your question directly without using 'ask'.")
    
    def _handle_exit(self) -> None:
        """Handle exit command by gracefully shutting down."""
        print("Thank you for using Personal AI RAG System. Goodbye!")
        self.running = False
    
    def _display_response(self, response: QueryResponse) -> None:
        """Format and display response with sources.
        
        Args:
            response: Query response to display
        """
        # Display the main answer
        print(f"\nAnswer:")
        print("-" * 20)
        print(response.answer)
        
        # Display source information
        if response.sources:
            print(f"\nSources ({len(response.sources)} documents used):")
            print("-" * 30)
            
            # Show brief source summary
            source_files = set()
            for source in response.sources:
                if source.metadata:
                    category = source.metadata.get("category", "unknown")
                    filename = source.metadata.get("filename", "unknown")
                    source_files.add(f"{category}/{filename}")
            
            for source_file in sorted(source_files):
                print(f"  • {source_file}")
            
            print(f"\nType 'sources' to see detailed source content.")
        else:
            print("\nNo sources were used for this response.")
    
    def _display_sources(self, sources) -> None:
        """Display detailed source information.
        
        Args:
            sources: List of RetrievedChunk objects
        """
        for i, source in enumerate(sources, 1):
            print(f"\nSource {i}:")
            print("-" * 15)
            
            # Display metadata
            if source.metadata:
                category = source.metadata.get("category", "unknown")
                filename = source.metadata.get("filename", "unknown")
                print(f"File: {category}/{filename}")
                print(f"Similarity: {source.similarity_score:.3f}")
            
            # Display content (truncated if too long)
            content = source.text.strip()
            if len(content) > 300:
                content = content[:300] + "..."
            
            print(f"Content: {content}")
            
            if i < len(sources):
                print()  # Add spacing between sources
    
    def _signal_handler(self, signum, frame) -> None:
        """Handle system signals for graceful shutdown.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        print(f"\nReceived signal {signum}. Shutting down gracefully...")
        self.running = False
        sys.exit(0)
