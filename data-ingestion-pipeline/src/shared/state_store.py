import datetime
from typing import Optional, Dict, Any
from azure.data.tables import TableClient, UpdateMode
from azure.core.exceptions import ResourceExistsError
from azure.identity import DefaultAzureCredential
from src.shared.settings import get_settings
from src.shared.logging import get_logger, log_event

LOGGER = get_logger(__name__)

class IngestionStateRepository:
    def __init__(self):
        settings = get_settings()
        self.table_name = settings.state_table_name
        self.table_client = TableClient(
            endpoint=settings.table_account_url,
            table_name=self.table_name,
            credential=DefaultAzureCredential()
        )
        try:
            self.table_client.create_table()
        except ResourceExistsError:
            pass
        except Exception as e:
            log_event(LOGGER, f"Failed to create table {self.table_name}: {e}")

    def _get_partition_key(self) -> str:
        return "video_ingestion"

    def _get_now_iso(self) -> str:
        return datetime.datetime.now(datetime.timezone.utc).isoformat()

    def _update_entity(self, video_id: str, updates: Dict[str, Any]):
        try:
            entity = self.table_client.get_entity(partition_key=self._get_partition_key(), row_key=video_id)
            for k, v in updates.items():
                entity[k] = v
            entity["updated_at"] = self._get_now_iso()
            self.table_client.update_entity(mode=UpdateMode.MERGE, entity=entity)
        except Exception as e:
            log_event(LOGGER, f"Error updating entity for {video_id}: {e}")
            raise

    def create_or_get(self, video_id: str, orchestration_id: str, content_version: str = None):
        try:
            entity = {
                "PartitionKey": self._get_partition_key(),
                "RowKey": video_id,
                "video_id": video_id,
                "orchestration_id": orchestration_id,
                "content_version": content_version or "1.0",
                "pipeline_status": "RECEIVED",
                "transcript_status": "NOT_STARTED",
                "chunk_status": "NOT_STARTED",
                "approval_status": "NOT_STARTED",
                "embedding_status": "NOT_STARTED",
                "upsert_status": "NOT_STARTED",
                "created_at": self._get_now_iso(),
                "updated_at": self._get_now_iso(),
            }
            self.table_client.create_entity(entity=entity)
            return entity
        except ResourceExistsError:
            return self.table_client.get_entity(partition_key=self._get_partition_key(), row_key=video_id)

    def mark_transcript_started(self, video_id: str):
        self._update_entity(video_id, {
            "pipeline_status": "TRANSCRIPT_IN_PROGRESS",
            "transcript_status": "IN_PROGRESS"
        })

    def mark_transcript_completed(self, video_id: str, transcript_blob_path: str, transcript_metadata: str = None):
        self._update_entity(video_id, {
            "transcript_status": "COMPLETED",
            "transcript_blob_path": transcript_blob_path,
        })

    def mark_chunking_started(self, video_id: str):
        self._update_entity(video_id, {
            "pipeline_status": "CHUNKING_IN_PROGRESS",
            "chunk_status": "IN_PROGRESS"
        })

    def mark_chunking_completed(self, video_id: str, chunks_blob_path: str, chunk_count: int, chunk_metadata: str = None):
        self._update_entity(video_id, {
            "chunk_status": "COMPLETED",
            "chunks_blob_path": chunks_blob_path,
            "chunk_count": chunk_count
        })

    def mark_pending_approval(self, video_id: str, approval_token_hash: str, approval_expires_at: str):
        self._update_entity(video_id, {
            "pipeline_status": "PENDING_APPROVAL",
            "approval_status": "WAITING",
            "approval_token_hash": approval_token_hash,
            "approval_expires_at": approval_expires_at
        })

    def mark_approved(self, video_id: str, approved_by: str, approved_at: str):
        self._update_entity(video_id, {
            "pipeline_status": "APPROVED",
            "approval_status": "APPROVED",
            "approved_by": approved_by,
            "approved_at": approved_at
        })

    def mark_rejected(self, video_id: str, rejected_by: str, rejected_at: str, reason: str = None):
        self._update_entity(video_id, {
            "pipeline_status": "REJECTED",
            "approval_status": "REJECTED",
            "rejected_by": rejected_by,
            "rejected_at": rejected_at,
            "reject_reason": reason or ""
        })

    def mark_approval_expired(self, video_id: str):
        self._update_entity(video_id, {
            "pipeline_status": "APPROVAL_EXPIRED",
            "approval_status": "EXPIRED"
        })

    def mark_embedding_started(self, video_id: str, embedding_model: str):
        self._update_entity(video_id, {
            "pipeline_status": "EMBEDDING_IN_PROGRESS",
            "embedding_status": "IN_PROGRESS",
            "embedding_model": embedding_model
        })

    def mark_embedding_progress(self, video_id: str, embedded_chunk_count: int, failed_batch_count: int = 0):
        self._update_entity(video_id, {
            "embedded_chunk_count": embedded_chunk_count
        })

    def mark_embedding_completed(self, video_id: str, embeddings_blob_path: str, embedded_chunk_count: int):
        self._update_entity(video_id, {
            "embedding_status": "COMPLETED",
            "embeddings_blob_path": embeddings_blob_path,
            "embedded_chunk_count": embedded_chunk_count
        })

    def mark_embedding_failed(self, video_id: str, error: str):
        self._update_entity(video_id, {
            "pipeline_status": "FAILED",
            "embedding_status": "FAILED",
            "last_error": error,
            "failed_stage": "EMBEDDING"
        })

    def mark_upsert_started(self, video_id: str, pinecone_index: str, namespace: str):
        self._update_entity(video_id, {
            "pipeline_status": "UPSERT_IN_PROGRESS",
            "upsert_status": "IN_PROGRESS",
            "pinecone_index": pinecone_index,
            "pinecone_namespace": namespace
        })

    def mark_upsert_completed(self, video_id: str, vector_count: int, namespace: str):
        self._update_entity(video_id, {
            "pipeline_status": "COMPLETED",
            "upsert_status": "COMPLETED",
            "upserted_vector_count": vector_count
        })

    def mark_upsert_failed(self, video_id: str, error: str):
        self._update_entity(video_id, {
            "pipeline_status": "FAILED",
            "upsert_status": "FAILED",
            "last_error": error,
            "failed_stage": "UPSERT"
        })

    def mark_completed(self, video_id: str):
        self._update_entity(video_id, {
            "pipeline_status": "COMPLETED"
        })

    def mark_failed(self, video_id: str, stage: str, error: str):
        self._update_entity(video_id, {
            "pipeline_status": "FAILED",
            "failed_stage": stage,
            "last_error": error
        })

    def get_state(self, video_id: str):
        try:
            return self.table_client.get_entity(partition_key=self._get_partition_key(), row_key=video_id)
        except Exception:
            return None
