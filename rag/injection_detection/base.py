from abc import ABC, abstractmethod

class InjectionDetectorBase(ABC):
    """
    Abstract interface for detecting prompt injection attacks.
    """

    @abstractmethod
    async def detect(self, query: str) -> bool:
        """
        Returns True if the query is safe, False if it contains an injection attack.
        """
        pass