from abc import ABC, abstractmethod
from typing import List, AsyncGenerator
from rag.core.models import GenerationResponse, SearchResult

class GeneratorBase(ABC):
    """
    Abstract interface for LLM generation (e.g., Gemini Flash/Pro).
    """

    @abstractmethod
    async def generate(
        self, 
        query: str, 
        documents: List[SearchResult]
    ) -> GenerationResponse:
        """
        Generate an answer given the query and retrieved context.
        """
        pass

    @abstractmethod
    async def generate_stream(
        self, 
        query: str, 
        documents: List[SearchResult]
    ) -> AsyncGenerator[str, None]:
        """
        Yields chunks of text as they are generated.
        """
        pass