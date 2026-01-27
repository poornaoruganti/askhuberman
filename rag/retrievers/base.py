from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from rag.core.models import SearchResult

class RetrieverBase(ABC):
    @abstractmethod
    async def search(
        self, 
        query: str, 
        top_k: int = 5, 
        filters: Optional[Dict[str, Any]] = None,
        namespace: Optional[str] = None  
    ) -> List[SearchResult]:
        """
        Retrieve relevant documents.
        Args:
            namespace: Partition to search in. If None, uses default.
        """
        pass