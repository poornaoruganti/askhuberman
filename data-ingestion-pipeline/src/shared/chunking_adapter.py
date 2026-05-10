from typing import Any, Dict, List
from src.shared.custom_chunkking import chapter_level_chunk


class ChunkingError(Exception):
    pass


def chunk_transcript_items(transcript_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Adapter for your existing chunking logic.

    Input shape (from blob raw/{video_id}.json):
      {
        "video_id": "...",
        "items": [{"text": "...", "start": 0.0, "duration": 4.2}, ...]
      }

    Output shape we will store to blob chunks/{video_id}.json:
      {
        "video_id": "...",
        "chunks": [
          {
            "chunk_id": "abc123_0001",
            "text": "...",
            "start": 12.34,
            "end": 56.78,
            "metadata": {...}
          },
          ...
        ]
      }
    """
    try:
        video_id = transcript_payload.get("video_id")
        items: List[Dict[str, Any]] = transcript_payload.get("items", [])

        if not video_id:
            raise ChunkingError("Missing video_id in transcript payload")
        if not isinstance(items, list):
            raise ChunkingError("Transcript items must be a list")
        chunks = chapter_level_chunk(transcript_payload)

        # return {"video_id": video_id, "chunks": chunks}
        return chunks
    except Exception as e:
        raise ChunkingError(f"Chunking failed: {e}") from e
