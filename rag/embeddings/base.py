from abc import ABC, abstractmethod
from typing import List

class EmbeddingBase(ABC):
    """
    Abstract interface for embedding models (e.g., Gemini, OpenAI).
    """

    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """
        Embed a single string (query) into a vector.
        """
        pass

    @abstractmethod
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of strings (documents) into a list of vectors.
        Optimized for batching.
        """
        pass