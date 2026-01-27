from pinecone import PineconeAsyncio
from typing import List, Optional, Dict, Any

from rag.retrievers.base import RetrieverBase
from rag.embeddings.base import EmbeddingBase
from rag.core.models import SearchResult
from rag.config.settings import settings
from rag.core.exceptions import RetrievalError
from rag.utils.logging import setup_rag_logger

logger = setup_rag_logger(__name__)

class PineconeRetriever(RetrieverBase):
    def __init__(self, embedder: EmbeddingBase):
        self.embedder = embedder
        self.index_name = settings.pinecone.index_name
        self.api_key = settings.pinecone.api_key
        
        # Initialize client
        self.pc = PineconeAsyncio(api_key=self.api_key)
        
        # We need the Host URL for Async Index calls. 
        # We'll fetch it lazily during the first search.
        self._index_host = None

    async def _get_index_host(self) -> str:
        """
        Helper to fetch the Host URL.
        Caches the result so we only call describe_index once.
        """
        if self._index_host:
            return self._index_host
            
        try:
            logger.debug(f"Fetching host for index: {self.index_name}")
            desc = await self.pc.describe_index(self.index_name)
            self._index_host = desc.host
            return self._index_host
        except Exception as e:
            logger.error(f"Failed to describe index: {e}")
            raise RetrievalError(f"Could not find index '{self.index_name}'. Check your Pinecone console.")

    async def search(
        self, 
        query: str, 
        top_k: int = 25, 
        filters: Optional[Dict[str, Any]] = None,
        namespace: Optional[str] = None
    ) -> List[SearchResult]:
        
        try:

            target_namespace = namespace or settings.pinecone.namespace
            # 1. Convert text query to vector
            vector = await self.embedder.embed_text(query)
    
            # 2. Get Host URL (Required for Async)
            host = await self._get_index_host()
            # 3. Connect to Index (Use async context manager)
            async with self.pc.IndexAsyncio(host=host) as index:
                
                # 4. Execute Query
                response = await index.query(
                    vector=vector,
                    top_k=top_k,
                    filter=filters,
                    namespace=target_namespace,
                    include_metadata=True,
                    include_values=False
                )

                # 5. Parse Results
                results = []
                for match in response.get('matches', []):
                    metadata = match.get('metadata', {})
                    content = metadata.get('content', "")
                    
                    results.append(SearchResult(
                        id=match['id'],
                        score=match['score'],
                        content=content,
                        metadata=metadata
                    ))
                
                logger.info(f"Retrieved {len(results)} docs for query: '{query}'")
                return results

        except Exception as e:
            logger.error(f"Pinecone search failed: {e}")
            raise RetrievalError(f"Database search failed: {str(e)}")

    async def close(self):
        """Cleanup method to close the client session."""
        await self.pc.close()