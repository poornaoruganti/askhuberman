import hashlib
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception,
)

def is_retryable_embedding_error(exc: Exception) -> bool:
    message = str(exc).lower()

    retryable_markers = [
        "429",
        "resource_exhausted",
        "quota",
        "rate limit",
        "timeout",
        "temporarily unavailable",
        "500",
        "502",
        "503",
        "504",
    ]

    return any(marker in message for marker in retryable_markers)


@retry(
    reraise=True,
    stop=stop_after_attempt(5),
    wait=wait_exponential_jitter(initial=2, max=30),
    retry=retry_if_exception(is_retryable_embedding_error),
)
def embed_text_with_retry(text: str, model: str) -> List[float]:
    response = genai.embed_content(
        model=model,
        content=text,
        task_type="retrieval_document",
    )

    vector = response.get("embedding")

    if not vector:
        raise RuntimeError("Gemini returned empty embedding vector")

    return vector


def safe_int(value: Any) -> Optional[int]:
    if value is None:
        return None

    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def build_timestamp_url(url: Optional[str], seconds: Any) -> Optional[str]:
    if not url:
        return None

    start = safe_int(seconds)

    if start is None:
        return url

    separator = "&" if "?" in url else "?"
    return f"{url}{separator}t={start}"


def clean_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pinecone metadata should be flat.
    Allowed values: str, int, float, bool, list[str].
    """
    cleaned: Dict[str, Any] = {}

    for key, value in metadata.items():
        if value is None:
            continue

        if isinstance(value, (str, int, float, bool)):
            cleaned[key] = value

        elif isinstance(value, list):
            cleaned[key] = [str(item) for item in value if item is not None]

        else:
            cleaned[key] = str(value)

    return cleaned


def make_vector_id(
    video_id: str,
    start_seconds: Any,
    end_seconds: Any,
    chunk_index: int,
    embedding_model: str,
) -> str:
    model_version = embedding_model.split("/")[-1]

    start = safe_int(start_seconds)
    end = safe_int(end_seconds)

    if start is not None and end is not None:
        return f"{video_id}::{start}-{end}"

    fallback = hashlib.sha1(f"{video_id}:{chunk_index}".encode()).hexdigest()[:12]
    return f"{video_id}::chunk-{chunk_index}-{fallback}::{model_version}"


def build_embedding_records(video_json: Dict[str, Any], embedding_model: str) -> List[Dict[str, Any]]:
    video_id = video_json.get("video_id")

    if not video_id:
        raise ValueError("video_json is missing video_id")

    chunks = video_json.get("chunks", [])

    if not isinstance(chunks, list):
        raise ValueError("video_json.chunks must be a list")

    parents = video_json.get("parents", [])
    parent_map = {
        parent.get("parent_id"): parent
        for parent in parents
        if isinstance(parent, dict) and parent.get("parent_id")
    }

    stats = video_json.get("stats") or {}

    records: List[Dict[str, Any]] = []

    for chunk_index, chunk in enumerate(chunks):
        if not isinstance(chunk, dict):
            continue

        text = (chunk.get("text") or "").strip()

        if not text:
            continue

        parent_id = chunk.get("parent_id")
        parent = parent_map.get(parent_id, {})

        start_seconds = chunk.get("start_seconds")
        end_seconds = chunk.get("end_seconds")
        parent_start_seconds = parent.get("start_seconds")
        parent_end_seconds = parent.get("end_seconds")

        metadata = {
            # video-level metadata
            "video_id": video_id,
            "video_title": video_json.get("video_title"),
            "url": video_json.get("url"),
            "timestamp_url": build_timestamp_url(video_json.get("url"), start_seconds),
            "parent_timestamp_url": build_timestamp_url(video_json.get("url"), parent_start_seconds),
            "published_at": video_json.get("published_at"),
            "duration_sec": video_json.get("duration_sec"),
            "channel_title": video_json.get("channel_title"),
            "tags": video_json.get("tags", []),
            "viewCount": stats.get("viewCount"),
            "likeCount": stats.get("likeCount"),
            "commentCount": stats.get("commentCount"),
            "source": video_json.get("source"),
            "indexed_at": video_json.get("indexed_at"),

            # chunk-level metadata
            "chunk_index": chunk_index,
            "chapter_title": chunk.get("chapter_title"),
            "start_seconds": start_seconds,
            "end_seconds": end_seconds,

            # parent-level metadata
            "parent_id": parent_id,
            "parent_start_seconds": parent_start_seconds,
            "parent_end_seconds": parent_end_seconds,

            # keep this for final answer citations/display
            "text": text,
        }

        records.append(
            {
                "id": make_vector_id(
                    video_id=video_id,
                    start_seconds=start_seconds,
                    end_seconds=end_seconds,
                    chunk_index=chunk_index,
                    embedding_model=embedding_model,
                ),
                "text": text,
                "metadata": clean_metadata(metadata),
            }
        )

    return records
