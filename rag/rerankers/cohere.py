import cohere
from typing import List

from rag.rerankers.base import RerankerBase
from rag.core.models import SearchResult
from rag.config.settings import settings
from rag.utils.logging import setup_rag_logger

logger = setup_rag_logger(__name__)

class CohereReranker(RerankerBase):
    def __init__(self):
        # Initialize Async Client
        self.client = cohere.AsyncClient(api_key=settings.cohere.api_key)
        self.model_name = settings.cohere.model

    async def rerank(
        self, 
        query: str, 
        documents: List[SearchResult], 
        top_n: int = 10
    ) -> List[SearchResult]:
        
        # Optimization: Don't rerank if list is empty or smaller than top_n
        if not documents:
            return []
        
        if len(documents) <= top_n:
            # If we have fewer docs than requested, just return them all 
            logger.info("Skipping rerank: Document count fewer than top_n")
            return documents

        try:
            # 1. Prepare strings for Cohere
            docs_text = [doc.metadata.get('text', "") for doc in documents]
            
            # 2. Call API
            response = await self.client.rerank(
                model=self.model_name,
                query=query,
                documents=docs_text,
                top_n=top_n
            )

            # 3. Reconstruct the list based on results
            reranked_results = []
            
            for result in response.results:
                # 'result.index' tells us which document from the original list this is
                original_doc = documents[result.index]
                
                # Update the score with Cohere's relevance score
                original_doc.score = result.relevance_score
                
                reranked_results.append(original_doc)

            logger.info(f"Reranked {len(documents)} docs down to {len(reranked_results)}")
            return reranked_results

        except Exception as e:
            logger.error(f"Cohere reranking failed: {e}")
            # Fail safe: Return original documents if reranker dies
            # This prevents the whole app from crashing when  Cohere is down
            return documents[:top_n]