import json
import logging
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException
from fastapi_limiter.depends import RateLimiter
from fastapi.responses import StreamingResponse

from rag.pipelines.rag_pipeline import RAGPipeline
from api.schemas import ChatRequest, StreamEvent
from api.dependencies import get_pipeline
from rag.core.exceptions import RAGError

router = APIRouter()
logger = logging.getLogger("rag.api")

async def response_generator(pipeline: RAGPipeline, request: ChatRequest) -> AsyncGenerator[str, None]:
    """
    This generator yields SSE-formatted events.
    Format: data: <json_string>\n\n
    """
    try:
        # 1. Trigger the Pipeline
        # pipeline.run() returns an async generator or an object containing one.
        pipeline_generator = pipeline.run_stream(
            query=request.query, 
            top_k=request.top_k or 5
        )
        async for event_type, data in pipeline_generator:
            if event_type == "citations":
                # Data is List[Document]
                # We serialize it to send to frontend
                serialized_docs = [
                                    {
                                        doc.id: {
                                            "title": doc.metadata.get("video_title", ""),
                                            "topic": doc.metadata.get("chapter_title", ""),
                                            "url": doc.metadata.get("timestamp_url", "")
                                                        }
                                    }
                                    for doc in data
                                    ]
                event = StreamEvent(event="citation", data=serialized_docs)
                yield f"data: {event.model_dump_json()}\n\n"
            
            elif event_type == "content":
                # Data is str (text chunk)
                event = StreamEvent(event="content", data=data)
                yield f"data: {event.model_dump_json()}\n\n"

    except Exception as e:
        logger.exception("Unexpected API Error")
        err_event = StreamEvent(event="error", data="Internal Server Error")
        yield f"data: {err_event.model_dump_json()}\n\n"

@router.post("/chat")
async def chat_endpoint(
    request: ChatRequest,
    pipeline: RAGPipeline = Depends(get_pipeline),
    _minute: None = Depends(RateLimiter(times=10, seconds=60)),       # 10/min
    _day: None = Depends(RateLimiter(times=100, seconds=86400)),      # 200/day
):
    """
    SSE Endpoint for RAG Chat.
    Client should consume this using EventSource or fetch with stream reading.
    """
    return StreamingResponse(
        response_generator(pipeline, request),
        media_type="text/event-stream"
    )