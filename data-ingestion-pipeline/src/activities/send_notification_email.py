import urllib.parse
from azure.communication.email import EmailClient
from azure.identity import DefaultAzureCredential
from src.shared.settings import get_settings
from src.shared.logging import get_logger, log_event

LOGGER = get_logger(__name__)

def send_notification_email(input_data: dict) -> dict:
    settings = get_settings()
    video_id = input_data.get("video_id")
    status = input_data.get("status")
    reason = input_data.get("reason", "")
    
    if status == "success":
        subject = f"Pipeline Success: Video {video_id} Ingested"
        html_content = f"""
        <html>
            <body>
                <h2>Pipeline Execution Successful</h2>
                <p>The ingestion pipeline for video <strong>{video_id}</strong> has completed successfully.</p>
            </body>
        </html>
        """
    else:
        subject = f"Pipeline Failed: Video {video_id}"
        html_content = f"""
        <html>
            <body>
                <h2>Pipeline Execution Failed</h2>
                <p>The ingestion pipeline for video <strong>{video_id}</strong> has failed.</p>
                <p><strong>Reason:</strong> {reason}</p>
            </body>
        </html>
        """

    try:
        email_client = EmailClient(
            endpoint=settings.communication_services_endpoint,
            credential=DefaultAzureCredential()
        )

        message = {
            "senderAddress": settings.sender_email_address,
            "recipients":  {
                "to": [{"address": settings.approver_email_address}], # sending to the same approver email
            },
            "content": {
                "subject": subject,
                "html": html_content,
            }
        }

        poller = email_client.begin_send(message)
        result = poller.result()
        log_event(LOGGER, f"Notification email sent successfully for {video_id} (status: {status})", extra={"video_id": video_id})
        return {"status": "success", "video_id": video_id}
    except Exception as e:
        log_event(LOGGER, f"Failed to send notification email for {video_id}: {e}")
        raise
