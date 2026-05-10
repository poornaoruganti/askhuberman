from __future__ import annotations

from typing import Any, Dict, List

import google.generativeai as genai

from src.shared.blob_storage import read_json, write_json, embeds_blob_path
from src.shared.settings import get_settings
from src.shared.logging import get_logger, log_event, log_exception
from src.shared.embeddings_helper import build_embedding_records, embed_text_with_retry

LOGGER = get_logger(__name__)


DEFAULT_EMBEDDING_MODEL = "models/gemini-embedding-001"


def embed_chunks_to_blob(input_data: Dict[str, Any]) -> Dict[str, Any]:
    settings = get_settings()

    video_id = input_data.get("video_id")
    chunks_blob_path = input_data.get("chunks_blob_path")
    embedding_model = input_data.get("embedding_model", DEFAULT_EMBEDDING_MODEL)

    if not video_id:
        raise ValueError("video_id is required")

    if not chunks_blob_path:
        raise ValueError("chunks_blob_path is required")

    log_event(
        LOGGER,
        "Starting embed_chunks_to_blob",
        extra={
            "video_id": video_id,
            "chunks_blob_path": chunks_blob_path,
            "embedding_model": embedding_model,
        },
    )

    genai.configure(api_key=settings.gemini_api_key)

    video_json = read_json(
        container=settings.chunks_container,
        blob_path=chunks_blob_path,
    )

    if not isinstance(video_json, dict):
        raise ValueError("Expected chunks blob to contain one video JSON object")

    records = build_embedding_records(
        video_json=video_json,
        embedding_model=embedding_model,
    )

    embeddings: List[Dict[str, Any]] = []

    for index, record in enumerate(records):
        try:
            vector = embed_text_with_retry(
                text=record["text"],
                model=embedding_model,
            )

            embeddings.append(
                {
                    "id": record["id"],
                    "values": vector,
                    "metadata": record["metadata"],
                }
            )

        except Exception as exc:
            log_exception(
                LOGGER,
                "Failed to embed chunk",
                extra={
                    "video_id": video_id,
                    "chunk_index": index,
                    "vector_id": record["id"],
                    "error": str(exc),
                },
            )
            raise

    embeddings_blob_path = embeds_blob_path(video_id)

    write_json(
        container=settings.embeds_container,
        blob_path=embeddings_blob_path,
        data=embeddings,
    )

    log_event(
        LOGGER,
        "Completed embed_chunks_to_blob",
        extra={
            "video_id": video_id,
            "embedded_chunk_count": len(embeddings),
            "embeddings_blob_path": embeddings_blob_path,
        },
    )

    return {
        "video_id": video_id,
        "embeddings_blob_path": embeddings_blob_path,
        "embedding_model": embedding_model,
        "embedded_chunk_count": len(embeddings),
    }