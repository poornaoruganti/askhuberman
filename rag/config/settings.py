from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Literal
import os

ENV = os.getenv("ENV", "dev") 

ENV_FILE = ".env" if ENV == "dev" else None

class GeminiSettings(BaseSettings):
    api_key: str = Field(..., alias="GEMINI_API_KEY")
    flash_model: str = "models/gemini-2.5-flash"
    pro_model: str = "models/gemini-2.5-pro"
    embedding_model: str = "models/gemini-embedding-001"
    embedding_dims: int = 3072

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

class PineconeSettings(BaseSettings):
    api_key: str = Field(..., alias="PINECONE_API_KEY")
    index_name: str = Field(..., alias="PINECONE_INDEX_NAME")
    namespace: str = Field(..., alias="NAMESPACE")
    cloud_type: Literal["serverless", "pod"] = "serverless"

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

class CohereSettings(BaseSettings):
    api_key: str = Field(..., alias="COHERE_API_KEY")
    model: str = "rerank-english-v3.0"

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

class Settings(BaseSettings):
    gemini: GeminiSettings = Field(default_factory=GeminiSettings)
    pinecone: PineconeSettings = Field(default_factory=PineconeSettings)
    cohere: CohereSettings = Field(default_factory=CohereSettings)
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

settings = Settings()
