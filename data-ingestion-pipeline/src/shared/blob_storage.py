import json
from typing import Any, Dict, Optional

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, ContentSettings
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.shared.settings import get_settings


class BlobError(Exception):
    pass


def _client() -> BlobServiceClient:
    s = get_settings()
    cred = DefaultAzureCredential()
    # s.blob_account_url example: "https://mystorageaccount.blob.core.windows.net"
    return BlobServiceClient(account_url=s.blob_account_url, credential=cred)


@retry(reraise=True, stop=stop_after_attempt(5), wait=wait_exponential(multiplier=0.5, min=1, max=10),
       retry=retry_if_exception_type(Exception))
def ensure_container(container_name: str) -> None:
    try:
        c = _client().get_container_client(container_name)
        if not c.exists():
            c.create_container()
    except Exception as e:
        raise BlobError(f"Failed to ensure container '{container_name}': {e}") from e


@retry(reraise=True, stop=stop_after_attempt(5), wait=wait_exponential(multiplier=0.5, min=1, max=10),
       retry=retry_if_exception_type(Exception))
def write_json(
    *,
    container: str,
    blob_path: str,
    data: Any,
    content_type: str = "application/json",
    metadata: Optional[Dict[str, str]] = None,
) -> None:
    try:
        ensure_container(container)
        blob = _client().get_blob_client(container=container, blob=blob_path)
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        blob.upload_blob(
            payload,
            overwrite=True,
            metadata=metadata,
            content_settings=ContentSettings(content_type=content_type),
        )
    except Exception as e:
        raise BlobError(f"Failed to write json blob '{container}/{blob_path}': {e}") from e


@retry(reraise=True, stop=stop_after_attempt(5), wait=wait_exponential(multiplier=0.5, min=1, max=10),
       retry=retry_if_exception_type(Exception))
def read_json(*, container: str, blob_path: str) -> Any:
    try:
        blob = _client().get_blob_client(container=container, blob=blob_path)
        raw = blob.download_blob().readall()
        return json.loads(raw)
    except Exception as e:
        raise BlobError(f"Failed to read json blob '{container}/{blob_path}': {e}") from e


def raw_blob_path(video_id: str) -> str:
    return f"{video_id}.json"


def chunks_blob_path(video_id: str) -> str:
    return f"{video_id}.json"


def embeds_blob_path(video_id: str) -> str:
    return f"{video_id}.json"


def manifest_blob_path(video_id: str) -> str:
    return f"{video_id}.json"