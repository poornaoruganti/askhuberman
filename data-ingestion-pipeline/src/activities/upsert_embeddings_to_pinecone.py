from pinecone import Pinecone
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from src.shared.blob_storage import read_json
from src.shared.settings import get_settings
from src.shared.logging import get_logger, log_event

LOGGER = get_logger(__name__)

@retry(reraise=True, stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=20),
       retry=retry_if_exception_type(Exception))
def upsert_with_retry(index, vectors, namespace):
    index.upsert(vectors=vectors, namespace=namespace)

def upsert_embeddings_to_pinecone(input_data: dict) -> dict:
    settings = get_settings()
    video_id = input_data.get("video_id")
    embeddings_blob = input_data.get("embeddings_blob_path")
    pinecone_index_name = input_data.get("pinecone_index", settings.pinecone_index_name)
    namespace = input_data.get("namespace", settings.pinecone_namespace)

    if not video_id or not embeddings_blob:
        raise ValueError("video_id and embeddings_blob_path are required")

    log_event(LOGGER, "Starting upsert_embeddings_to_pinecone", extra={"video_id": video_id})

    # 1. Read embeddings from blob
    embeddings_data = read_json(container=settings.embeds_container, blob_path=embeddings_blob)
    if not isinstance(embeddings_data, list):
        raise ValueError("Embeddings data is not a list")

    if len(embeddings_data) == 0:
        log_event(LOGGER, "No embeddings to upsert", extra={"video_id": video_id})
        return {
            "video_id": video_id,
            "vector_count": 0,
            "namespace": namespace,
            "pinecone_index": pinecone_index_name
        }

    # 2. Init Pinecone
    pc = Pinecone(api_key=settings.pinecone_api_key)
    index = pc.Index(pinecone_index_name)

    # 3. Batch vectors (e.g., 100 per batch)
    #batch_size = 100
    #
        #batch = embeddings_data[i:i + batch_size]
    try:
        upsert_with_retry(index, embeddings_data, namespace)
        log_event(LOGGER, f"Upserted {len(embeddings_data)} vectors", extra={"video_id": video_id})
    except Exception as e:
        log_event(LOGGER, f"Failed to upsert batch  for {video_id}", extra={"error": str(e)})
        raise

    log_event(LOGGER, "Completed upsert_embeddings_to_pinecone", extra={"video_id": video_id, "count": len(embeddings_data)})

    return {
        "video_id": video_id,
        "vector_count": len(embeddings_data),
        "namespace": namespace,
        "pinecone_index": pinecone_index_name
    }
