
from typing import List, Literal, Optional, Any, Dict
from pydantic import BaseModel, Field

class Message(BaseModel):
    """
    Represents a single message in the conversation history.
    """
    role: Literal["user", "model", "system"]
    content: str

class ChatRequest(BaseModel):
    """
    The strict contract for incoming chat requests.
    """
    query: str = Field(..., min_length=1, description="The user's question")
    history: List[Message] = Field(default_factory=list, description="Previous conversation context")
    
    # Configuration overrides (optional)
    top_k: Optional[int] = Field(default=5, ge=1, le=25, description="Number of documents to retrieve")
    
class StreamEvent(BaseModel):
    """
    Standardizes Server-Sent Events (SSE) data format.
    """
    event: Literal["content", "citation", "error", "metadata"]
    data: Any