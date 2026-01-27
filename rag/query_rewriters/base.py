from abc import ABC, abstractmethod
from typing import List

class QueryRewriterBase(ABC):
    """
    Abstract interface for query transformation.
    """

    @abstractmethod
    async def rewrite(self, original_query: str) -> str:
        """
        Rewrite the query to be more search-friendly.
        Example: "How much is it?" -> "What is the price of the Premium Plan?"
        """
        pass