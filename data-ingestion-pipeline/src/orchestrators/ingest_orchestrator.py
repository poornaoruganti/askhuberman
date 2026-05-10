import datetime
import azure.durable_functions as df
from pydantic import json
from src.shared.logging import get_logger, log_event
from src.shared.settings import get_settings
import json

LOGGER = get_logger(__name__)

def run_orchestrator(context: df.DurableOrchestrationContext):
    """
    Durable orchestrator = generator function.
    """
    inp = context.get_input() or {}
    video_id = inp.get("video_id")
    corr_id = inp.get("corr_id")

    if not video_id:
        return {"status": "failed", "reason": "missing_video_id"}

    try:
        # ---------- Step 1: transcript -> blob ----------
        yield context.call_activity("update_state", {"video_id": video_id, "method": "mark_transcript_started"})
        
        step1 = yield context.call_activity("fetch_transcript_to_blob", {"video_id": video_id, "corr_id": corr_id})
        transcript_blob = step1.get("raw_blob")
        
        yield context.call_activity("update_state", {"video_id": video_id, "method": "mark_transcript_completed", "kwargs": {"transcript_blob_path": transcript_blob}})

        # ---------- Step 2: chunk -> blob ----------
        yield context.call_activity("update_state", {"video_id": video_id, "method": "mark_chunking_started"})
        
        step2 = yield context.call_activity("chunk_transcript_to_blob", {"video_id": video_id, "corr_id": corr_id})
        chunks_blob = step2.get("chunks_blob")
        chunks_count = step2.get("chunks_count", 0)
        video_title = step2.get("video_title", "Unknown")
        video_url = step2.get("url", f"https://www.youtube.com/watch?v={video_id}")
        published_at = step2.get("published_at", "Unknown")
        duration_sec = step2.get("duration_sec", 0)
        chapters_count = step2.get("chapters_count", 0)
        
        yield context.call_activity("update_state", {"video_id": video_id, "method": "mark_chunking_completed", "kwargs": {"chunks_blob_path": chunks_blob, "chunk_count": chunks_count}})

        # ---------- Step 3: approval ----------
        token_data = yield context.call_activity("generate_approval_token", {})
        token = token_data["token"]
        token_hash = token_data["token_hash"]
        
        expiration_time = context.current_utc_datetime + datetime.timedelta(hours=24)
        
        yield context.call_activity("update_state", {
            "video_id": video_id, 
            "method": "mark_pending_approval", 
            "kwargs": {"approval_token_hash": token_hash, "approval_expires_at": expiration_time.isoformat()}
        })

        yield context.call_activity("send_approval_email", {
            "video_id": video_id,
            "chunk_count": chunks_count,
            "transcript_blob_path": transcript_blob,
            "chunks_blob_path": chunks_blob,
            "token": token,
            "video_title": video_title,
            "video_url": video_url,
            "published_at": published_at,
            "duration_sec": duration_sec,
            "chapters_count": chapters_count
        })

        approval_event = context.wait_for_external_event("approval_response")
        timeout_task = context.create_timer(expiration_time)
        
        winner = yield context.task_any([approval_event, timeout_task])

        if winner == timeout_task:
            yield context.call_activity("update_state", {"video_id": video_id, "method": "mark_approval_expired"})
            yield context.call_activity("send_notification_email", {"video_id": video_id, "status": "failed", "reason": "Approval expired"})
            return {"status": "approval_expired", "video_id": video_id}
            
        timeout_task.cancel()
        approval_data = approval_event.result

        log_event(LOGGER, "Received approval event", extra={"approval_data": approval_data, "approval_data_type": type(approval_data).__name__})
        if isinstance(approval_data, str):
            approval_data = json.loads(approval_data)
        
        decision = approval_data.get("decision")
        
        if decision == "rejected":
            yield context.call_activity("update_state", {
                "video_id": video_id, 
                "method": "mark_rejected", 
                "kwargs": {"rejected_by": approval_data.get("approved_by"), "rejected_at": approval_data.get("approved_at")}
            })
            yield context.call_activity("send_notification_email", {"video_id": video_id, "status": "failed", "reason": "Approval rejected"})
            return {"status": "rejected", "video_id": video_id}

        yield context.call_activity("update_state", {
            "video_id": video_id, 
            "method": "mark_approved", 
            "kwargs": {"approved_by": approval_data.get("approved_by"), "approved_at": approval_data.get("approved_at")}
        })

        # ---------- Step 4: Embeddings ----------
        embedding_model = "gemini-embedding-001"
        yield context.call_activity("update_state", {"video_id": video_id, "method": "mark_embedding_started", "kwargs": {"embedding_model": embedding_model}})
        
        step4 = yield context.call_activity("embed_chunks_to_blob", {
            "video_id": video_id,
            "chunks_blob_path": chunks_blob,
            "embedding_model": embedding_model
        })
        embeds_blob = step4.get("embeddings_blob_path")
        embedded_count = step4.get("embedded_chunk_count", 0)
        
        yield context.call_activity("update_state", {
            "video_id": video_id, 
            "method": "mark_embedding_completed", 
            "kwargs": {"embeddings_blob_path": embeds_blob, "embedded_chunk_count": embedded_count}
        })

        # ---------- Step 5: Pinecone Upsert ----------
        yield context.call_activity("update_state", {
            "video_id": video_id, 
            "method": "mark_upsert_started", 
            "kwargs": {"pinecone_index": "youtube-index", "namespace": ""}
        })
        
        step5 = yield context.call_activity("upsert_embeddings_to_pinecone", {
            "video_id": video_id,
            "embeddings_blob_path": embeds_blob
        })
        upserted_count = step5.get("vector_count", 0)
        namespace = step5.get("namespace", "")
        
        yield context.call_activity("update_state", {
            "video_id": video_id, 
            "method": "mark_upsert_completed", 
            "kwargs": {"vector_count": upserted_count, "namespace": namespace}
        })

        yield context.call_activity("update_state", {"video_id": video_id, "method": "mark_completed"})

        yield context.call_activity("send_notification_email", {"video_id": video_id, "status": "success"})

        return {
            "status": "completed",
            "video_id": video_id,
            "instance_id": context.instance_id
        }

    except Exception as e:
        error_msg = str(e)
        log_event(LOGGER, f"Orchestrator failed for {video_id}", extra={"error": error_msg})
        # If it failed during a step, we mark the whole pipeline failed
        yield context.call_activity("update_state", {
            "video_id": video_id, 
            "method": "mark_failed", 
            "kwargs": {"stage": "ORCHESTRATOR", "error": error_msg[:500]}
        })
        
        yield context.call_activity("send_notification_email", {"video_id": video_id, "status": "failed", "reason": error_msg[:500]})
        
        raise
