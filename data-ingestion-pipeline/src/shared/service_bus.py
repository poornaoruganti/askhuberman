import json
from typing import Any, Dict, Optional

from azure.identity import DefaultAzureCredential
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.shared.settings import get_settings


class ServiceBusSendError(Exception):
    pass


@retry(
    reraise=True,
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=0.5, min=1, max=10),
    retry=retry_if_exception_type(Exception),
)
def send_video_id_message(
    video_id: str,
    *,
    corr_id: Optional[str] = None,
    extra_payload: Optional[Dict[str, Any]] = None,
) -> None:
    if not video_id:
        raise ValueError("video_id is required")

    s = get_settings()

    body: Dict[str, Any] = {"video_id": video_id}
    if extra_payload:
        body.update(extra_payload)

    msg = ServiceBusMessage(
        json.dumps(body),
        content_type="application/json",
        message_id=video_id,  # duplicate detection
        correlation_id=corr_id,
        subject="youtube.video_id",
    )

    try:
        cred = DefaultAzureCredential()
        # s.service_bus_fqdn example: "mybus.servicebus.windows.net"
        with ServiceBusClient(fully_qualified_namespace=s.service_bus_fqdn, credential=cred) as client:
            with client.get_queue_sender(queue_name=s.service_bus_queue_name) as sender:
                sender.send_messages(msg)
    except Exception as e:
        raise ServiceBusSendError(f"Failed to send video_id message: {e}") from e
