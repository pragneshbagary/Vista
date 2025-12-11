"""Tests for the LLM client."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice

from vista.llm_openai import OpenAILLMClient


class TestLLMClient:
    """Test cases for LLMClient class."""
    
    def test_init(self):
        """Test LLMClient initialization."""
        client = OpenAILLMClient(api_key="test-key", model="gpt-3.5-turbo")
        assert client.api_key == "test-key"
        assert client.model == "gpt-3.5-turbo"
        assert client.client is not None
    
    @patch('vista.llm_client.OpenAI')
    def test_generate_response_success(self, mock_openai):
        """Test successful response generation."""
        # Mock the OpenAI client and response
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        # Create a mock response
        mock_message = ChatCompletionMessage(role="assistant", content="Test response")
        mock_choice = Choice(index=0, message=mock_message, finish_reason="stop")
        mock_response = ChatCompletion(
            id="test-id",
            choices=[mock_choice],
            created=1234567890,
            model="gpt-3.5-turbo",
            object="chat.completion"
        )
        
        mock_client.chat.completions.create.return_value = mock_response
        
        # Test the client
        client = OpenAILLMClient(api_key="test-key")
        result = client.generate_response("Test prompt", max_tokens=100)
        
        assert result == "Test response"
        mock_client.chat.completions.create.assert_called_once()
    
    @patch('vista.llm_client.OpenAI')
    def test_generate_response_empty_response(self, mock_openai):
        """Test handling of empty response."""
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        # Mock empty response
        mock_response = ChatCompletion(
            id="test-id",
            choices=[],
            created=1234567890,
            model="gpt-3.5-turbo",
            object="chat.completion"
        )
        
        mock_client.chat.completions.create.return_value = mock_response
        
        client = OpenAILLMClient(api_key="test-key")
        
        with pytest.raises(Exception, match="Empty response from OpenAI API"):
            client.generate_response("Test prompt")
    
    @patch('vista.llm_client.time.sleep')
    def test_retry_with_backoff_success_on_retry(self, mock_sleep):
        """Test retry logic succeeds on second attempt."""
        client = OpenAILLMClient(api_key="test-key")
        
        # Mock function that fails once then succeeds
        mock_func = Mock(side_effect=[Exception("First failure"), "Success"])
        
        result = client._retry_with_backoff(mock_func, max_retries=2)
        
        assert result == "Success"
        assert mock_func.call_count == 2
        mock_sleep.assert_called_once_with(1)  # 2^0 = 1 second delay
    
    @patch('vista.llm_client.time.sleep')
    def test_retry_with_backoff_all_attempts_fail(self, mock_sleep):
        """Test retry logic when all attempts fail."""
        client = OpenAILLMClient(api_key="test-key")
        
        # Mock function that always fails
        mock_func = Mock(side_effect=Exception("Always fails"))
        
        with pytest.raises(Exception, match="Always fails"):
            client._retry_with_backoff(mock_func, max_retries=2)
        
        assert mock_func.call_count == 3  # Initial + 2 retries
        # Should have delays of 1, 2 seconds (2^0, 2^1)
        from unittest.mock import call
        expected_calls = [call(1), call(2)]
        mock_sleep.assert_has_calls(expected_calls)
    
    def test_retry_with_backoff_immediate_success(self):
        """Test retry logic when function succeeds immediately."""
        client = OpenAILLMClient(api_key="test-key")
        
        mock_func = Mock(return_value="Immediate success")
        
        result = client._retry_with_backoff(mock_func, max_retries=2)
        
        assert result == "Immediate success"
        assert mock_func.call_count == 1