import os
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ENVIRONMENT: str = "development"

    # Sarvam Speech-to-Text & Text-to-Speech
    SARVAM_API_KEY: str = Field(default_factory=lambda: os.getenv("SARVAM_API_KEY", ""))
    SARVAM_STT_URL: str = Field(default="https://api.sarvam.ai/speech-to-text-translate")
    SARVAM_TTS_URL: str = Field(default="https://api.sarvam.ai/text-to-speech")
    SARVAM_TTS_SPEAKER: str = Field(default="meera")
    ENABLE_TTS: bool = Field(default=True)

    # LLM Configuration
    LLM_PROVIDER: str = Field(default="auto") # auto | gemini | openai | grounded_local
    GEMINI_API_KEY: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    OPENAI_API_KEY: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    GEMINI_MODEL: str = Field(default="gemini-2.0-flash")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini")
    LLM_MODEL: str = Field(default="gemini-2.0-flash")
    LLM_TEMPERATURE: float = Field(default=0.2)
    LLM_MAX_TOKENS: int = Field(default=256)

    # Embedding Model
    EMBEDDING_MODEL: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")

    # Paths
    INDEX_DIR: str = Field(default="data/indexes")
    DATASET_NAME: str = Field(default="ai4bharat/MSMARCO-XI")
    MAX_INGEST_DOCUMENTS: int = Field(default=1000)

    # Retrieval & Indexing parameters
    FAISS_INDEX_TYPE: str = Field(default="flat")  # flat | hnsw
    FAISS_HNSW_M: int = Field(default=32)
    FAISS_HNSW_EF_SEARCH: int = Field(default=64)
    RETRIEVAL_TOP_K: int = Field(default=5)
    RELEVANCE_THRESHOLD: float = Field(default=0.012)

    # Caching
    ENABLE_QUERY_CACHE: bool = Field(default=True)
    CACHE_MAX_ENTRIES: int = Field(default=1000)
    CACHE_SEMANTIC_THRESHOLD: float = Field(default=0.96)
    CACHE_TTL_SECONDS: int = Field(default=3600)

    # Rate Limiting & Security
    ENABLE_RATE_LIMITING: bool = Field(default=True)
    RATE_LIMIT_PER_MINUTE: int = Field(default=60)
    ENABLE_PII_REDACTION: bool = Field(default=True)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
