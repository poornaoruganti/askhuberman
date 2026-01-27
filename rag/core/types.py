# rag/core/types.py
from enum import Enum

class GeminiModelType(str, Enum):
    FLASH = "flash"  # Fast, cheap
    PRO = "pro"      # Reasoning heavy

class Role(str, Enum):
    USER = "user"
    SYSTEM = "system"
    ASSISTANT = "model"

class TaskType(str, Enum):
    """Gemini specific embedding task types."""
    RETRIEVAL_QUERY = "RETRIEVAL_QUERY"
    RETRIEVAL_DOCUMENT = "RETRIEVAL_DOCUMENT"
    SEMANTIC_SIMILARITY = "SEMANTIC_SIMILARITY"