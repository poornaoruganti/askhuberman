import urllib.parse
from azure.communication.email import EmailClient
from azure.identity import DefaultAzureCredential
from src.shared.settings import get_settings
from src.shared.logging import get_logger, log_event

LOGGER = get_logger(__name__)

def send_approval_email(input_data: dict) -> dict:
    settings = get_settings()
    video_id = input_data.get("video_id")
    token = input_data.get("token")
    chunk_count = input_data.get("chunk_count", 0)
    transcript_blob_path = input_data.get("transcript_blob_path", "")
    chunks_blob_path = input_data.get("chunks_blob_path", "")

    video_title = input_data.get("video_title", "Unknown")
    video_url = input_data.get("video_url", f"https://www.youtube.com/watch?v={video_id}")
    published_at = input_data.get("published_at", "Unknown")
    duration_sec = input_data.get("duration_sec", 0)
    chapters_count = input_data.get("chapters_count", 0)

    host_url = settings.host_url.rstrip('/')
    blob_url = settings.blob_account_url.rstrip('/')
    
    # URL encode token
    safe_token = urllib.parse.quote(token)
    
    approve_link = f"{host_url}?video_id={video_id}&decision=approve&token={safe_token}"
    reject_link = f"{host_url}?video_id={video_id}&decision=reject&token={safe_token}"

    full_transcript_url = f"{blob_url}/{settings.raw_container}/{transcript_blob_path}"
    full_chunks_url = f"{blob_url}/{settings.chunks_container}/{chunks_blob_path}"

    html_content = f"""
    <html>
        <body>
            <h2>Approval Required for Video Ingestion</h2>
            
            <h3>About video:</h3>
            <p><strong>videoid:</strong> {video_id}</p>
            <p><strong>video title:</strong> {video_title}</p>
            <p><strong>video url:</strong> <a href="{video_url}">{video_url}</a></p>
            <p><strong>video published at:</strong> {published_at}</p>

            <h3>video Details:</h3>
            <p><strong>duration:</strong> {duration_sec} seconds</p>
            <p><strong>number of chapters:</strong> {chapters_count}</p>
            <p><strong>total number of chunks:</strong> {chunk_count}</p>
            <p><strong>blob url for the transcript:</strong> <a href="{full_transcript_url}">{full_transcript_url}</a></p>
            <p><strong>blob url for the chapters:</strong> <a href="{full_chunks_url}">{full_chunks_url}</a></p>
            <br/>
            <p><a href="{approve_link}" style="padding:10px; background-color:green; color:white; text-decoration:none;">Approve</a></p>
            <br/>
            <p><a href="{reject_link}" style="padding:10px; background-color:red; color:white; text-decoration:none;">Reject</a></p>
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
                "to": [{"address": settings.approver_email_address}],
            },
            "content": {
                "subject": f"Approval Required: Video {video_id}",
                "html": html_content,
            }
        }

        poller = email_client.begin_send(message)
        result = poller.result()
        log_event(LOGGER, "Approval email sent successfully", extra={"video_id": video_id})
        return {"status": "success", "video_id": video_id}
    except Exception as e:
        log_event(LOGGER, f"Failed to send approval email for {video_id}: {e}")
        raise
