from typing import Any, Dict

from src.shared.blob_storage import read_json, write_json, chunks_blob_path , raw_blob_path
from src.shared.chunking_adapter import chunk_transcript_items
from src.shared.logging import get_logger, log_event, log_exception
from src.shared.settings import get_settings


LOGGER = get_logger(__name__)


def chunk_transcript_to_blob(input2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Activity input:
      { "video_id": "...", "corr_id": "..." }

    Output:
      { "video_id": "...", "chunks_blob": "<path>", "chunks_count": <int> }
    """
    s = get_settings()
    video_id = input2.get("video_id")
    corr_id = input2.get("corr_id")

    if not video_id:
        raise ValueError("chunk_transcript_to_blob: missing video_id")



    try:
        raw_path = raw_blob_path(video_id)
        transcript_payload = read_json(container=s.raw_container, blob_path=raw_path)

        chunked = chunk_transcript_items(transcript_payload)

        out_path = chunks_blob_path(video_id)
        write_json(
            container=s.chunks_container,
            blob_path=out_path,
            data=chunked,
            metadata={
                "video_id": video_id,
                "stage": "chunked_transcript",
                "corr_id": corr_id or "",
            },
        )

        chunks_count = len(chunked.get("chunks", []))
        log_event(
            LOGGER,
            "Transcript chunked and saved to blob",
            corr_id=corr_id,
            extra={"video_id": video_id, "chunks_blob": out_path, "chunks_count": chunks_count},
        )

        return {
            "video_id": video_id, 
            "chunks_blob": out_path, 
            "chunks_count": chunks_count,
            "video_title": chunked.get("video_title"),
            "url": chunked.get("url"),
            "published_at": chunked.get("published_at"),
            "duration_sec": chunked.get("duration_sec"),
            "chapters_count": len(chunked.get("chapters", []))
        }

    except Exception as e:
        log_exception(
            LOGGER,
            "chunk_transcript_to_blob failed",
            corr_id=corr_id,
            extra={"video_id": video_id, "err": str(e)},
        )
        raise
