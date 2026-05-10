import azure.functions as func
import logging
import xml.etree.ElementTree as ET
import os
import requests

from src.shared.logging import get_logger, log_event, log_exception, new_corr_id
from src.shared.settings import get_settings
from src.shared.logging import get_logger, log_event, log_exception, new_corr_id

LOGGER = get_logger(__name__)
# -------------------------
# Resubscribe timer
# -------------------------
YOUTUBE_FEED_TMPL = "https://www.youtube.com/xml/feeds/videos.xml?channel_id={cid}"
LOGGER = get_logger(__name__)

def _extract_hub_url(feed_xml: str) -> str:
    root = ET.fromstring(feed_xml)

    # 1) Atom namespace links
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for link in root.findall("atom:link", ns):
        if link.attrib.get("rel") == "hub":
            return (link.attrib.get("href") or "").strip()

    # 2) Fallback: non-namespaced links
    for link in root.findall(".//link"):
        if link.attrib.get("rel") == "hub":
            return (link.attrib.get("href") or "").strip()

    return ""


def _subscribe(hub_url: str, topic_url: str, callback_url: str, secret: str = "") -> requests.Response:
    data = {
        "hub.mode": "subscribe",
        "hub.topic": topic_url,
        "hub.callback": callback_url,
        "hub.verify": "async",
    }
    if secret:
        data["hub.secret"] = secret
    print(f"Subscribing to {topic_url} via hub {hub_url} with callback {callback_url}")
    print(f"POST data: {data}")
    log_event(LOGGER, "Subscribing to YouTube channel feed", extra={"topic_url": topic_url, "hub_url": hub_url})    
    log_event(LOGGER, "Subscription request data", extra={"data": data})
    return requests.post(hub_url, data=data, timeout=15)

def resubscribe(timer: func.TimerRequest) -> None:
    try:
        channel_ids_raw = (os.getenv("YOUTUBE_CHANNEL_IDS") or "").strip()
        callback_url = (os.getenv("YOUTUBE_CALLBACK_URL") or "").strip()
        secret = (os.getenv("WEBSUB_SECRET") or "").strip()

        log_event(LOGGER, "Resubscribe timer triggered", extra={
            "YOUTUBE_CHANNEL_IDS_SET": channel_ids_raw,
            "YOUTUBE_CALLBACK_URL_SET": callback_url,
            "WEBSUB_SECRET_SET": secret
        })


    except Exception as e:
        LOGGER.exception("Resubscribe failed")
        return f"error: {str(e)}"


    if not channel_ids_raw:
        log_event(LOGGER, "YOUTUBE_CHANNEL_IDS is empty. Skipping resubscribe.")
        return
    if not callback_url:
        log_event(LOGGER, "Missing YOUTUBE_CALLBACK_URL. Cannot subscribe.")
        return

    channel_ids = [c.strip() for c in channel_ids_raw.split(",") if c.strip()]
    # logging.info("Resubscribe started. channels=%d", len(channel_ids))
    log_event(LOGGER, "Resubscribe started", extra={"channel_count": len(channel_ids)})

    ok, fail = 0, 0

    for cid in channel_ids:
        topic_url = YOUTUBE_FEED_TMPL.format(cid=cid)

        try:
            r = requests.get(topic_url, timeout=15)
            r.raise_for_status()

            hub_url = _extract_hub_url(r.text)
            if not hub_url:
                # logging.error("No hub URL found in feed for channel_id=%s", cid)
                log_event(LOGGER, "No hub URL found in feed", extra={"channel_id": cid}, level=logging.ERROR)   
                fail += 1
                continue

            resp = _subscribe(hub_url, topic_url, callback_url, secret=secret)

            if resp.status_code in (200, 202, 204):
                # logging.info("Subscribe OK channel_id=%s status=%d", cid, resp.status_code)
                log_event(LOGGER, "Subscribe successful", extra={"channel_id": cid, "status_code": resp.status_code})
                ok += 1
            else:
                # logging.error("Subscribe FAIL channel_id=%s status=%d body=%s",
                #               cid, resp.status_code, (resp.text or "")[:300])
                log_event(LOGGER, "Subscribe failed", extra={"channel_id": cid, "status_code": resp.status_code, "response_body": (resp.text or "")[:300]}, level=logging.ERROR)    
                fail += 1

        except Exception as e:
            # logging.error("Error subscribing channel_id=%s err=%s", cid, str(e), exc_info=True)
            log_event(LOGGER, "Exception during subscribe", extra={"channel_id": cid, "error": str(e)}, level=logging.ERROR)    
            fail += 1

    # logging.info("Resubscribe done. ok=%d fail=%d", ok, fail)
    log_event(LOGGER, "Resubscribe completed", extra={"ok_count": ok, "fail_count": fail})
