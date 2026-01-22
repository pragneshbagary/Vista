# llm_base.py
from abc import ABC, abstractmethod

class BaseLLMClient(ABC):

    @abstractmethod
    def generate_response(self, prompt: str, max_tokens: int = 500) -> str:
        pass
