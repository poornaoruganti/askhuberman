import google.generativeai as genai
import time
from typing import List , AsyncGenerator

from rag.generators.base import GeneratorBase
from rag.core.models import GenerationResponse, SearchResult
from rag.prompts.base import PromptLoaderBase
from rag.config.settings import settings
from rag.core.exceptions import GenerationError
from rag.utils.logging import setup_rag_logger

logger = setup_rag_logger(__name__)

class GeminiGenerator(GeneratorBase):
    def __init__(self, prompt_loader: PromptLoaderBase):
        genai.configure(api_key=settings.gemini.api_key)
        self.prompt_loader = prompt_loader
        self.default_model_name = settings.gemini.flash_model

    async def generate_stream(
        self, 
        query: str, 
        documents: List[SearchResult]
    ) -> AsyncGenerator[str, None]:
        
        try:
            # 1. Prepare Prompt 
            system_prompt, user_prompt = self.prompt_loader.render(
                "qa.yaml", 
                query=query, 
                documents=documents
            )

            # 2. Initialize Model 
            self.model = genai.GenerativeModel(
                model_name=self.default_model_name,
                system_instruction=system_prompt
            )
            
            # 3. Call with stream=True
            response_stream = await self.model.generate_content_async(
                user_prompt,
                generation_config=genai.types.GenerationConfig(temperature=0.0),
                stream=True 
            )
            
            # 4. Yield chunks
            async for chunk in response_stream:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            yield f"Error generating response: {str(e)}"

    async def generate(
        self, 
        query: str, 
        documents: List[SearchResult]
    ) -> GenerationResponse:
        
        start_time = time.time()
        
        try:
            # 1. Prepare Context from Documents
            # YAML template handles the looping over docs
            
            # 2. Load and Render Prompt
            system_prompt, user_prompt = self.prompt_loader.render(
                            "qa.yaml", 
                            query=query, 
                            documents=documents
                        )
            self.model = genai.GenerativeModel(
                            model_name=self.default_model_name,
                            system_instruction=system_prompt
                        )
            
            print(system_prompt)
            print(user_prompt)
            print(self.default_model_name)
            
            # 3. Call LLM (Async)
            # generation_config can be tuned for temperature here
            response = await self.model.generate_content_async(
                            user_prompt,
                            generation_config=genai.types.GenerationConfig(temperature=0.0)
                        )
            latency = time.time() - start_time
            
            # 4. Usage tracking (Estimate if not provided by API)
            token_count = self.model.count_tokens(user_prompt).total_tokens
            return GenerationResponse(
                answer=response.text,
                sources=[i.metadata.get('timestamp_url', '') for i in documents],
                latency_seconds=latency,
                usage_tokens=token_count,
                model_used=settings.gemini.flash_model
            )

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise GenerationError(f"LLM generation failed: {str(e)}")