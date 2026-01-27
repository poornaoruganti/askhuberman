
from functools import lru_cache
from typing import AsyncGenerator

# --- Internal RAG Library Imports ---
from rag.config.settings import Settings as RagSettings
from rag.utils.logging import setup_rag_logger
from rag.embeddings.gemini import GeminiEmbedding
from rag.retrievers.pinecone import PineconeRetriever
from rag.rerankers.cohere import CohereReranker
from rag.generators.gemini import GeminiGenerator
from rag.pipelines.rag_pipeline import RAGPipeline
from rag.prompts.file_loader import FilePromptLoader

@lru_cache()
def get_rag_settings():
    return RagSettings()

class PipelineFactory:
    """
    Singleton factory to ensure we only initialize heavy clients (Pinecone/Cohere) once.
    """
    _instance: RAGPipeline | None = None

    @classmethod
    async def get_instance(cls) -> RAGPipeline:
        if cls._instance is None:
            settings = get_rag_settings()
            logger = setup_rag_logger(__name__)
            logger.info("Initializing RAG Components...")
    

            prompt_loader = FilePromptLoader()
            embedder = GeminiEmbedding()

            # 2. Core Modules
            # Inject embedder into retriever
            retriever = PineconeRetriever(embedder=embedder) 
             # Inject prompt loader into generator
            generator = GeminiGenerator(prompt_loader=prompt_loader)
            reranker = CohereReranker()
            
            # Wire them together into the Pipeline
            cls._instance = RAGPipeline(
                retriever=retriever,
                reranker=reranker,
                generator=generator,
                rewriter=None
            )
        
        return cls._instance

# --- FastAPI Dependency ---
async def get_pipeline() -> RAGPipeline:
    """
    Dependency to be used in routes:
    async def chat(pipeline: RAGPipeline = Depends(get_pipeline)):
    """
    return await PipelineFactory.get_instance()