import azure.functions as func
import azure.durable_functions as df
import datetime
from src.shared.settings import get_settings
from src.shared.state_store import IngestionStateRepository
from src.shared.auth import verify_approval_token
from src.shared.logging import get_logger, log_event

LOGGER = get_logger(__name__)

async def approval_webhook(req: func.HttpRequest, client: df.DurableOrchestrationClient) -> func.HttpResponse:
    video_id = req.params.get('video_id')
    decision = req.params.get('decision')
    token = req.params.get('token')

    if not video_id or not decision or not token:
        return func.HttpResponse("Missing parameters", status_code=400)

    decision = decision.lower()
    if decision not in ["approve", "reject"]:
        return func.HttpResponse("Invalid decision", status_code=400)

    settings = get_settings()
    repo = IngestionStateRepository()
    
    state = repo.get_state(video_id)
    if not state:
        return func.HttpResponse("State not found", status_code=404)

    if state.get("approval_status") != "WAITING":
        return func.HttpResponse("Video is not pending approval", status_code=400)

    expected_hash = state.get("approval_token_hash")
    if not verify_approval_token(settings.approval_secret_key, token, expected_hash):
        return func.HttpResponse("Invalid token", status_code=403)

    expires_at_str = state.get("approval_expires_at")
    if expires_at_str:
        expires_at = datetime.datetime.fromisoformat(expires_at_str)
        if datetime.datetime.now(datetime.timezone.utc) > expires_at:
            return func.HttpResponse("Token expired", status_code=400)

    orchestration_id = state.get("orchestration_id")
    if not orchestration_id:
        return func.HttpResponse("Orchestration ID not found", status_code=500)

    payload = {
        "video_id": video_id,
        "decision": decision + "d", # approved or rejected
        "approved_by": "manual_email_link",
        "approved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "reason": None
    }

    try:
        await client.raise_event(
            instance_id=orchestration_id,
            event_name="approval_response",
            event_data=payload
        )
        log_event(LOGGER, f"Approval event raised for {video_id}", extra={"decision": decision})
    except Exception as e:
        log_event(LOGGER, f"Failed to raise approval event for {video_id}: {e}")
        return func.HttpResponse("Failed to process approval", status_code=500)

    return func.HttpResponse(
        f"<html><body><h2>{decision.capitalize()}d successfully</h2><p>You can close this window.</p></body></html>",
        mimetype="text/html",
        status_code=200
    )
