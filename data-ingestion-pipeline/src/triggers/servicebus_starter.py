import json
from typing import Any, Dict, Optional

import azure.functions as func
import azure.durable_functions as df

from src.shared.logging import get_logger, log_event, log_exception, new_corr_id
from src.shared.settings import get_settings
from src.shared.state_store import IngestionStateRepository


LOGGER = get_logger(__name__)


def _safe_json_loads(raw: str) -> Dict[str, Any]:
    try:
        return json.loads(raw)
    except Exception:
        return {}


async def servicebus_starter(msg: func.ServiceBusMessage, client: df.DurableOrchestrationClient) -> None:
    """
    Service Bus trigger:
      - reads video_id from queue 
      - starts Durable orchestrator instance with payload
    """
    s = get_settings()
    corr_id = msg.correlation_id or new_corr_id()

    try:
        body_raw = msg.get_body().decode("utf-8")
        payload = _safe_json_loads(body_raw)
        video_id = payload.get("video_id")

        if not video_id:
            log_event(
                LOGGER,
                "ServiceBus message missing video_id",
                corr_id=corr_id,
                extra={"body": body_raw[:500]},
            )
            return

        # Include useful metadata for traceability
        orchestrator_input = {
            "video_id": video_id,
            "corr_id": corr_id,
            "source": "servicebus",
        }


        # Use a deterministic instance id per video to avoid parallel duplicate runs even beyond SB dedupe window.
        instance_id = f"ingest-{video_id}"

        # Start only if not already running/completed recently (optional)
        status = await client.get_status(instance_id)
        if status and status.runtime_status in ("Running", "Pending", "ContinuedAsNew"):
            log_event(
                LOGGER,
                "Orchestration already running; skipping start",
                corr_id=corr_id,
                extra={"video_id": video_id, "instance_id": instance_id, "runtime_status": status.runtime_status},
            )
            return
        
        
        # Create initial state record
        repo = IngestionStateRepository()
        repo.create_or_get(video_id, instance_id)

        await client.start_new("orchestrator_main", instance_id, orchestrator_input)



        log_event(
            LOGGER,
            "Started orchestration from Service Bus",
            corr_id=corr_id,
            extra={"video_id": video_id, "instance_id": instance_id, "queue": "huberman-videoids"},
        )

    except Exception as e:
        log_exception(
            LOGGER,
            "ServiceBus starter failed",
            corr_id=corr_id,
            extra={"err": str(e)},
        )
        raise
