from typing import Any, Dict

from src.shared.blob_storage import write_json, raw_blob_path
from src.shared.logging import get_logger, log_event, log_exception
from src.shared.settings import get_settings
from src.shared.youtube_transcripts import fetch_transcript


LOGGER = get_logger(__name__)


def fetch_transcript_to_blob(input1: Dict[str, Any]) -> Dict[str, Any]:
    """
    Activity input:
      { "video_id": "...", "corr_id": "..." }

    Output:
      { "video_id": "...", "raw_blob": "<path>" }
    """
    s = get_settings()
    video_id = input1.get("video_id")
    corr_id = input1.get("corr_id")

    if not video_id:
        raise ValueError("fetch_transcript_to_blob: missing video_id")
    

    try:
        payload = fetch_transcript(video_id)

        blob_path = raw_blob_path(video_id)
        write_json(
            container=s.raw_container,
            blob_path=blob_path,
            data=payload,
            metadata={
                "video_id": video_id,
                "stage": "raw_transcript",
                "corr_id": corr_id or "",
            },
        )

        log_event(
            LOGGER,
            "Transcript fetched and saved to blob",
            corr_id=corr_id,
            extra={"video_id": video_id, "raw_blob": blob_path, "items": len(payload.get("items", []))},
        )

        return {"video_id": video_id, "raw_blob": blob_path}

    except Exception as e:
        log_exception(
            LOGGER,
            "fetch_transcript_to_blob failed",
            corr_id=corr_id,
            extra={"video_id": video_id, "err": str(e)},
        )
        raise
