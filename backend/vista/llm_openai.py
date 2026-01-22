"""LLM client for the Vista."""

import logging
import time
from typing import Callable, Any
from openai import OpenAI
from openai.types.chat import ChatCompletion

from vista.llm_base import BaseLLMClient

logger = logging.getLogger(__name__)


class OpenAILLMClient(BaseLLMClient):
    """Interface with LLM API for response generation."""
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        """Initialize OpenAI client.
        
        Args:
            api_key: OpenAI API key
            model: Model name to use
        """
        self.api_key = api_key
        self.model = model
        self.client = OpenAI(api_key=api_key)
    
    def generate_response(self, prompt: str, max_tokens: int = 500) -> str:
        """Generate response from LLM.
        
        Args:
            prompt: Prompt to send to LLM
            max_tokens: Maximum tokens in response
            
        Returns:
            Generated response text
            
        Raises:
            Exception: If API call fails after all retries
        """
        def _make_api_call() -> str:
            """Make the actual API call to OpenAI."""
            try:
                response: ChatCompletion = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are VISTA, a personal technical assistant representing the work of Pragnesh.Be clear, concise, and honest.Avoid over-polished language.Prefer practical explanations over marketing-style phrasing.If something is uncertain, say so.Do not exaggerate. Do not praise excessively.Do not use buzzwords unless necessary."
                        },
                        {
                            "role": "user", 
                            "content": prompt
                        }
                    ],
                    max_tokens=max_tokens,
                    temperature=0.1  # Low temperature for more consistent, factual responses
                )
                
                if response.choices and response.choices[0].message.content:
                    return response.choices[0].message.content.strip()
                else:
                    raise Exception("Empty response from OpenAI API")
                    
            except Exception as e:
                logger.error(f"OpenAI API call failed: {e}")
                raise
        
        # Use retry logic for the API call
        return self._retry_with_backoff(_make_api_call, max_retries=3)
    
    def _retry_with_backoff(self, func: Callable[[], Any], max_retries: int = 3) -> Any:
        """Retry failed API calls with exponential backoff.
        
        Args:
            func: Function to retry
            max_retries: Maximum number of retry attempts
            
        Returns:
            Result of the function call
            
        Raises:
            Exception: If all retry attempts fail
        """
        last_exception = None
        
        for attempt in range(max_retries + 1):  # +1 to include the initial attempt
            try:
                return func()
            except Exception as e:
                last_exception = e
                
                if attempt == max_retries:
                    # This was the last attempt, re-raise the exception
                    logger.error(f"All {max_retries + 1} attempts failed. Last error: {e}")
                    raise e
                
                # Calculate exponential backoff delay: 2^attempt seconds
                delay = 2 ** attempt
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay} seconds...")
                time.sleep(delay)
        
        # This should never be reached, but just in case
        if last_exception:
            raise last_exception
        else:
            raise Exception("Unexpected error in retry logic")
