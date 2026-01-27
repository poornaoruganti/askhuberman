class RAGError(Exception):
    """Base exception for all RAG related errors."""
    pass

class ConfigurationError(RAGError):
    """Missing API keys or bad config."""
    pass

class EmbeddingError(RAGError):
    """Failed to generate embeddings from provider."""
    pass

class RetrievalError(RAGError):
    """Vector DB connection or query failed."""
    pass

class GenerationError(RAGError):
    """LLM generation failed."""
    pass

class ContextLimitExceededError(RAGError):
    """Prompt is too long for the model."""
    pass