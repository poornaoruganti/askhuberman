from typing import Any, Dict, List, Optional

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
    CouldNotRetrieveTranscript,
)
from youtube_transcript_api.proxies import GenericProxyConfig
from src.shared.settings import get_settings


class TranscriptFetchError(Exception):
    pass


def fetch_transcript(
    video_id: str,
    *,
    languages: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Fetch transcript for a video and return a JSON-friendly payload.

    Returns:
      {
        "video_id": "...",
        "items": [{"text": "...", "start": 0.0, "duration": 4.2}, ...]
      }

    """
    if not video_id:
        raise ValueError("video_id is required")

    langs = languages or ["en"]

    try:
        settings = get_settings()
        ytt_api = YouTubeTranscriptApi(
            proxy_config=GenericProxyConfig(
                http_url=settings.youtube_proxy_http_url,
                https_url=settings.youtube_proxy_https_url,
            )
        )
        transcript_data = ytt_api.fetch(video_id).to_raw_data()
        # items already JSON-friendly (list of dicts)
        return {"video_id": video_id, "items": transcript_data, "languages": langs}
    except (VideoUnavailable, TranscriptsDisabled, NoTranscriptFound) as e:
        raise TranscriptFetchError(f"Transcript not available for video_id={video_id}: {e}") from e
    except (CouldNotRetrieveTranscript,) as e:
        raise TranscriptFetchError(f"Could not retrieve transcript for video_id={video_id}: {e}") from e
    except Exception as e:
        raise TranscriptFetchError(f"Unexpected transcript error for video_id={video_id}: {e}") from e
