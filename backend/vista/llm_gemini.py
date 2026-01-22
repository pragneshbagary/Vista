# llm_gemini.py
from google import genai
from google.genai.types import GenerateContentConfig
from vista.llm_base import BaseLLMClient
import time
import logging

logger = logging.getLogger(__name__)

class GeminiLLMClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        # Initialize the client with the API key
        self.client = genai.Client(api_key=api_key)
        self.model_name = model
        
    def generate_response(self, prompt: str, max_tokens: int = 500) -> str:
        def _make_api_call():
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config = GenerateContentConfig(
                        system_instruction="You are VISTA, a personal technical assistant representing the work of Pragnesh.Be clear, concise, and honest.Avoid over-polished language.Prefer practical explanations over marketing-style phrasing.If something is uncertain, say so.Do not exaggerate. Do not praise excessively.Do not use buzzwords unless necessary.",
                        max_output_tokens= max_tokens, 
                        temperature=0.2
                    )
            )   
                
                return response.text.strip()
            except Exception as e:
                logger.error(f"Gemini API call failed: {e}")
                raise
        
        return self._retry_with_backoff(_make_api_call)
    
    def _retry_with_backoff(self, func, max_retries=3):
        for attempt in range(max_retries + 1):
            try:
                return func()
            except Exception as e:
                if attempt == max_retries:
                    raise e
                wait_time = 2 ** attempt
                logger.warning(f"Retry attempt {attempt + 1}/{max_retries} after {wait_time}s")
                time.sleep(wait_time)


                
