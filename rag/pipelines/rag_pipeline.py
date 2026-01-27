import time
from typing import Optional, List

from rag.core.models import GenerationResponse, SearchResult


# Import Interfaces
from rag.retrievers.base import RetrieverBase
from rag.generators.base import GeneratorBase
from rag.rerankers.base import RerankerBase
from rag.query_rewriters.base import QueryRewriterBase
from rag.injection_detection.base import InjectionDetectorBase
from typing import List, AsyncGenerator, Tuple, Any
from rag.utils.logging import setup_rag_logger

logger = setup_rag_logger(__name__)

class RAGPipeline:
    def __init__(
        self,
        retriever: RetrieverBase,
        generator: GeneratorBase,
        reranker: Optional[RerankerBase] = None,
        rewriter: Optional[QueryRewriterBase] = None,
        detector: Optional[InjectionDetectorBase] = None,
    ):
        """
        Initializes the RAG pipeline with its components.
        
        Args:
            retriever: Finds documents.
            generator: Generates answers.
            reranker: (Optional) Re-orders documents for better relevance.
            rewriter: (Optional) Cleans up the user query.
            detector: (Optional) Checks for malicious prompts.
        """
        self.retriever = retriever
        self.generator = generator
        self.reranker = reranker
        self.rewriter = rewriter
        self.detector = detector

    async def run_stream(self, query: str, top_k: int = 25)-> AsyncGenerator[Tuple[str, Any], None]:
        """
        Executes the full RAG flow: 
        Detect -> Rewrite -> Retrieve -> Rerank -> Generate.
        """

        current_query = query
        
        try:
            # 1. Safety Check (Guardrails)
            if self.detector:
                is_safe = await self.detector.detect(query)
                if not is_safe:
                    logger.warning(f"Injection detected for query: {query}")
                    raise InjectionError("Unsafe query detected.")

            # 2. Query Rewriting (Optimization)
            if self.rewriter:
                logger.info(f"Original query: {query}")
                current_query = await self.rewriter.rewrite(query)
                logger.info(f"Rewritten query: {current_query}")

            # 3. Retrieval (Fetch)
            documents = await self.retriever.search(query, top_k=top_k)
            
            if not documents:
                logger.warning(f"No documents found for query: {current_query}")
                # Optional: Return early or let the LLM handle "I don't know"
            
            # 4. Reranking 
            if self.reranker and documents:
                ranked_documents = await self.reranker.rerank(
                    query=query, 
                    documents=documents, 
                    top_n=10
                )
            yield ("citations", ranked_documents)

            # 5. Generation (Answer)
            async for chunk in self.generator.generate_stream(query=query,documents=ranked_documents):
                yield ("content", chunk)

        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            raise e


    async def run(self, query: str, top_k: int = 25) -> GenerationResponse:
        """
        Executes the full RAG flow: 
        Detect -> Rewrite -> Retrieve -> Rerank -> Generate.
        """
        start_total = time.time()
        current_query = query
        
        try:
            # 1. Safety Check (Guardrails)
            if self.detector:
                is_safe = await self.detector.detect(query)
                if not is_safe:
                    logger.warning(f"Injection detected for query: {query}")
                    raise InjectionError("Unsafe query detected.")

            # 2. Query Rewriting (Optimization)
            if self.rewriter:
                logger.info(f"Original query: {query}")
                current_query = await self.rewriter.rewrite(query)
                logger.info(f"Rewritten query: {current_query}")

            # 3. Retrieval (Fetch)
            documents = await self.retriever.search(query, top_k=top_k)
            
            if not documents:
                logger.warning(f"No documents found for query: {current_query}")
                # Optional: Return early or let the LLM handle "I don't know"
            
            # 4. Reranking (Refinement)
            if self.reranker and documents:
                documents = await self.reranker.rerank(
                    query=query, 
                    documents=documents, 
                    top_n=10
                )

            # 5. Generation (Answer)
            response = await self.generator.generate(
                query=query,  
                documents=documents
            )
            
            # Add total pipeline latency to the response metrics
            response.latency_seconds = time.time() - start_total
            
            logger.info(f"Pipeline finished in {response.latency_seconds:.2f}s")
            return response

        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            raise e