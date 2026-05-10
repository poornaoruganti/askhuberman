import logging

import azure.functions as func

from azure.identity import DefaultAzureCredential
import xml.etree.ElementTree as ET
from azure.servicebus import ServiceBusClient, ServiceBusMessage
import os
from src.shared.logging import get_logger, log_event, log_exception, new_corr_id
import hmac
import hashlib
import json
from src.shared.settings import get_settings

LOGGER = get_logger(__name__)



# -------------------------
# Signature verification
# -------------------------
def _verify_websub_signature(secret: str, body: bytes, sig256: str, sig1: str) -> bool:
    """
    Verifies hub signature. Supports:
      - X-Hub-Signature-256: sha256=<hex>
      - X-Hub-Signature: sha1=<hex>
    """
    if not secret:
        # If secret not configured, verification is disabled
        return True

    # Prefer sha256 header if present
    if sig256:
        # Expected format: "sha256=<hexdigest>"
        try:
            algo, provided = sig256.split("=", 1)
        except ValueError:
            return False
        if algo.strip().lower() != "sha256":
            return False

        expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, provided.strip().lower())

    # Fall back to sha1 header (older)
    if sig1:
        # Expected format: "sha1=<hexdigest>"
        try:
            algo, provided = sig1.split("=", 1)
        except ValueError:
            return False
        if algo.strip().lower() != "sha1":
            return False

        expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha1).hexdigest()
        return hmac.compare_digest(expected, provided.strip().lower())

    # Secret is set but no signature headers provided -> reject
    return False



def pushVideoId(req: func.HttpRequest) -> func.HttpResponse:
    # Load settings
    settings = get_settings()

    # Replace environment variable reads with settings attributes
    SERVICEBUS_NAMESPACE = settings.service_bus_fqdn
    QUEUE_NAME = settings.service_bus_queue_name
    WEBSUB_SECRET = settings.websub_secret

    msg = "Log event from youtube_webhook trigger"

    log_event(
    LOGGER,
    msg,
    extra={
        "SERVICEBUS_NAMESPACE": SERVICEBUS_NAMESPACE,
        "QUEUE_NAME": QUEUE_NAME,
        "WEBSUB_SECRET_SET": WEBSUB_SECRET,
        "Method": req.method,
    })


    if req.method == "GET":
        hub_challenge = req.params.get("hub.challenge")
        if hub_challenge:
            return func.HttpResponse(hub_challenge, status_code=200)
        return func.HttpResponse("Missing hub.challenge", status_code=400)

    # POST
    try:
        # IMPORTANT: Use raw bytes for signature verification
        body_bytes = req.get_body()

        # 1) Verify signature if secret is configured
        sig256 = req.headers.get("X-Hub-Signature-256") or req.headers.get("x-hub-signature-256") or ""
        sig1 = req.headers.get("X-Hub-Signature") or req.headers.get("x-hub-signature") or ""

        # if not _verify_websub_signature(WEBSUB_SECRET, body_bytes, sig256, sig1):
        #     logging.warning("Invalid/missing WebSub signature. Rejecting request.")
        #     return func.HttpResponse("Invalid signature", status_code=401)

        # 2) Parse XML (can decode after verification)
        body = body_bytes.decode("utf-8", errors="replace")
        root = ET.fromstring(body)

        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "yt": "http://www.youtube.com/xml/schemas/2015",
        }

        entry = root.find(".//atom:entry", ns)
        if entry is None:
            # logging.warning("No <entry> in notification. Ack with 200.")
            log_event(LOGGER, "No <entry> found in notification XML")
            return func.HttpResponse("No entry", status_code=200)

        vid_el = entry.find("yt:videoId", ns)
        video_id = (vid_el.text or "").strip() if vid_el is not None else ""
        if not video_id:
            log_event(LOGGER, "No videoId found. Ack with 200.")
            return func.HttpResponse("No videoId", status_code=200)

        # 3) Send to Service Bus
        payload = {
    "video_id": video_id
        }
        credential = DefaultAzureCredential()
        with ServiceBusClient(SERVICEBUS_NAMESPACE, credential) as client:
            with client.get_queue_sender(QUEUE_NAME) as sender:
                msg = ServiceBusMessage(json.dumps(payload))
                msg.message_id = video_id  # enables dedupe if queue has duplicate detection on
                sender.send_messages(msg)

        # logging.info("Queued video_id=%s", video_id)
        log_event(LOGGER, "Queued video ID from YouTube notification", extra={"video_id": video_id})
        return func.HttpResponse("OK", status_code=200)

    except ET.ParseError as e:
        # logging.error("XML parse error: %s", e)
        log_event(LOGGER, "XML parse error in notification", extra={"error": str(e)})
        # Ack to avoid endless retries on malformed payload
        return func.HttpResponse("Bad XML", status_code=200)

    except Exception as e:
        logging.error("Unhandled error: %s", e, exc_info=True)
        log_event(LOGGER, "Unhandled exception in YouTube webhook", extra={"error": str(e)}, level=logging.ERROR)
        return func.HttpResponse("Internal error", status_code=500)