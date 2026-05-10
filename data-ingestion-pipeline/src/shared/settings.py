from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):


    # -----------------------------
    # Service Bus
    # -----------------------------
    service_bus_queue_name: str = Field(default="youtube", env="SERVICE_BUS_QUEUE_NAME")
    service_bus_fqdn: str = Field(..., env="SERVICE_BUS_FQDN")
    youtube_api: str = Field(..., env="YOUTUBE_API")
    youtube_proxy_http_url: str = Field(..., env="YOUTUBE_PROXY_HTTP_URL")
    youtube_proxy_https_url: str = Field(..., env="YOUTUBE_PROXY_HTTPS_URL")
    websub_secret: str = Field(..., env="WEBSUB_SECRET")

    # -----------------------------
    # Blob Storage
    # -----------------------------
    blob_account_url: str = Field(..., env="BLOB_ACCOUNT_URL")
    raw_container: str = Field(default="raw", env="RAW_CONTAINER")
    chunks_container: str = Field(default="chunks", env="CHUNKS_CONTAINER")
    embeds_container: str = Field(default="embeddings", env="EMBEDS_CONTAINER")

    # -----------------------------
    # Table Storage
    # -----------------------------
    table_account_url: str = Field(..., env="TABLE_ACCOUNT_URL")
    state_table_name: str = Field(default="IngestionState", env="STATE_TABLE_NAME")

    # -----------------------------
    # Gemini
    # -----------------------------
    gemini_api_key: str = Field(..., env="GEMINI_API_KEY")

    # -----------------------------
    # Azure Communication Services (Email)
    # -----------------------------
    communication_services_endpoint: str = Field(..., env="COMMUNICATION_SERVICES_ENDPOINT")
    sender_email_address: str = Field(..., env="SENDER_EMAIL_ADDRESS")
    approver_email_address: str = Field(..., env="APPROVER_EMAIL_ADDRESS")

    # -----------------------------
    # Pinecone
    # -----------------------------
    pinecone_api_key: str = Field(..., env="PINECONE_API_KEY")
    pinecone_index_name: str = Field(..., env="PINECONE_INDEX_NAME")
    pinecone_namespace: str = Field(default="", env="PINECONE_NAMESPACE")

    # -----------------------------
    # Approvals
    # -----------------------------
    approval_secret_key: str = Field(..., env="APPROVAL_SECRET_KEY")
    host_url: str = Field(..., env="HOST_URL")

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings loader.
    Safe to call from anywhere (triggers, activities, orchestrators).
    """
    return Settings()
