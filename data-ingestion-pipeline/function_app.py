import azure.functions as func

from src.shared.logging import get_logger, log_event
from src.triggers.servicebus_starter import servicebus_starter
import azure.durable_functions as df
from src.orchestrators.ingest_orchestrator import run_orchestrator
from src.activities.fetch_transcript_to_blob import fetch_transcript_to_blob
from src.activities.chunk_transcript_to_blob import chunk_transcript_to_blob
from src.activities.update_state import update_state
from src.activities.generate_approval_token import generate_approval_token
from src.activities.send_approval_email import send_approval_email
from src.activities.embed_chunks_to_blob import embed_chunks_to_blob
from src.activities.upsert_embeddings_to_pinecone import upsert_embeddings_to_pinecone
from src.activities.send_notification_email import send_notification_email
from src.triggers.approval_webhook import approval_webhook
from src.triggers.youtube_webhook import pushVideoId
from src.triggers.resubscribe_timer import resubscribe

LOGGER = get_logger(__name__)


app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

#timer trigger for resubscribing to youtube push notifications every 24 hours
@app.function_name(name="resubscribe_timer")
@app.timer_trigger(
    schedule="0 0 0 * * *",
    arg_name="timer",
    run_on_startup=False
)
def youtube_resubscribe(timer: func.TimerRequest) -> None:
    resubscribe(timer)

#webhook trigger for youtube push notifications
@app.function_name(name="webhook_push_video_id")
@app.route(route="v1/youtube/webhook/pusshVideoId", methods=["GET", "POST"])
def webhook_push_video_id(req: func.HttpRequest) -> func.HttpResponse:
    return pushVideoId(req)

# Service Bus Trigger (Starter) - receives video ids from service bus
@app.function_name(name="sb_starter")
@app.service_bus_queue_trigger(
    arg_name="azservicebus", 
    queue_name="huberman-videoids",
    connection="SERVICEBUS"
)
@app.durable_client_input(client_name="client")     
async def sb_starter(azservicebus: func.ServiceBusMessage, client: df.DurableOrchestrationClient):

    log_event(LOGGER, "Serviceee Bus trigger received message", extra={"message_id": azservicebus.message_id, "correlation_id": azservicebus.correlation_id})
    try:
        await servicebus_starter(azservicebus, client)
    except Exception as e:
        log_event(LOGGER, "Error in servicebus_starter", extra={"error": str(e)})



# Durable Orchestrator - orchestrates the ingestion process
@app.function_name(name="orchestrator_main")
@app.orchestration_trigger(context_name="context")
def ingest_orchestrator(context: df.DurableOrchestrationContext):
    result = yield from run_orchestrator(context)
    return result


# Durable Activity - fetch transcript to blob
@app.function_name(name="fetch_transcript_to_blob")
@app.activity_trigger(input_name="input1")
def fetch_transcript_activity(input1):
    return fetch_transcript_to_blob(input1)

# Durable Activity - chunk transcript to blob
@app.function_name(name="chunk_transcript_to_blob") 
@app.activity_trigger(input_name="input2")
def chunk_transcript_activity(input2):
    return chunk_transcript_to_blob(input2)

@app.function_name(name="update_state")
@app.activity_trigger(input_name="input3")
def update_state_activity(input3):
    return update_state(input3)

@app.function_name(name="generate_approval_token")
@app.activity_trigger(input_name="input4")
def generate_approval_token_activity(input4):
    return generate_approval_token(input4)

@app.function_name(name="send_approval_email")
@app.activity_trigger(input_name="input5")
def send_approval_email_activity(input5):
    return send_approval_email(input5)

@app.function_name(name="embed_chunks_to_blob")
@app.activity_trigger(input_name="input6")
def embed_chunks_to_blob_activity(input6):
    return embed_chunks_to_blob(input6)

@app.function_name(name="upsert_embeddings_to_pinecone")
@app.activity_trigger(input_name="input7")
def upsert_embeddings_to_pinecone_activity(input7):
    return upsert_embeddings_to_pinecone(input7)

@app.function_name(name="send_notification_email")
@app.activity_trigger(input_name="input8")
def send_notification_email_activity(input8):
    return send_notification_email(input8)

# HTTP Trigger for approval webhook
@app.function_name(name="approval_webhook")
@app.route(route="approval", methods=["GET"])
@app.durable_client_input(client_name="client")
async def approval_webhook_trigger(req: func.HttpRequest, client: df.DurableOrchestrationClient) -> func.HttpResponse:
    return await approval_webhook(req, client)
