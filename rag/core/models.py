# rag/core/models.py
from typing import List, Optional, Dict, Any , List
from pydantic import BaseModel, Field
from datetime import datetime

# --- Ingestion/Storage Models ---

# class Document(BaseModel):
#     """Raw document before chunking."""
#     id: str
#     content: str
#     metadata: Dict[str, Any] = Field(default_factory=dict)
#     source: str  # filepath or url
#     created_at: datetime = Field(default_factory=datetime.utcnow)

# class Chunk(BaseModel):
#     """The unit of data stored in Pinecone."""
#     id: str
#     content: str
#     vector: List[float]
#     metadata: Dict[str, Any] = Field(default_factory=dict)
#     document_id: str
    
# --- Retrieval/Generation Models ---

class SearchResult(BaseModel):
    """A single result from the vector DB."""
    id: str
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)

# class UserQuery(BaseModel):
#     """Incoming user request."""
#     query_text: str
#     filters: Optional[Dict[str, Any]] = None
#     top_k: int = 5

class GenerationResponse(BaseModel):
    """Final answer from the RAG pipeline."""
    answer: str
    sources: List[str]
    latency_seconds: float
    usage_tokens: int
    model_used: str             