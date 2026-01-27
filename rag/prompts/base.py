from abc import ABC, abstractmethod
from typing import Any, Dict

class PromptLoaderBase(ABC):
    """
    Abstract interface for loading and rendering prompts.
    """

    @abstractmethod
    def render(self, template_name: str, **kwargs: Any) -> str:
        """
        Load a template and render it with the provided variables.
        
        Args:
            template_name: The filename (e.g., 'rag_query.yaml')
            kwargs: Variables to inject (e.g., query="Hello", context="...")
        """
        pass