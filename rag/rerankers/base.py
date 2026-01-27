from abc import ABC, abstractmethod
from typing import List
from rag.core.models import SearchResult

class RerankerBase(ABC):
    """
    Abstract interface for reranking retrieved documents.
    """

    @abstractmethod
    async def rerank(
        self, 
        query: str, 
        documents: List[SearchResult], 
        top_n: int = 3
    ) -> List[SearchResult]:
        """
        Re-order the documents based on relevance to the query.
        """
        pass