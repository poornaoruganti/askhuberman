import google.generativeai as genai
from typing import List
from rag.embeddings.base import EmbeddingBase
from rag.config.settings import settings
from rag.core.exceptions import EmbeddingError
from rag.utils.logging import setup_rag_logger

logger = setup_rag_logger(__name__)

class GeminiEmbedding(EmbeddingBase):
    def __init__(self):
        genai.configure(api_key=settings.gemini.api_key)
        self.model_name = settings.gemini.embedding_model

    async def embed_text(self, text: str) -> List[float]:
        """
        Embeds a single query string.
        Task type: RETRIEVAL_QUERY (optimized for search questions)
        """
        try:
            result = await genai.embed_content_async(
                model=self.model_name,
                content=text,
                task_type="retrieval_query"
            )
            return result['embedding']
        except Exception as e:
            logger.error(f"Error embedding text: {e}")
            raise EmbeddingError(f"Gemini embedding failed: {str(e)}")

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embeds a batch of documents.
        Task type: RETRIEVAL_DOCUMENT (optimized for storage)
        """
        try:
            # Note: Gemini batch embedding has limits (often 100 docs per call).
            # processing one huge batch here for now
            # later chunk 'texts' into groups of 100.
            result = await genai.embed_content_async(
                model=self.model_name,
                content=texts,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            logger.error(f"Error embedding documents: {e}")
            raise EmbeddingError(f"Gemini batch embedding failed: {str(e)}")