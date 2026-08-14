import os
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ENVIRONMENT: str = "development"

    # Sarvam Speech-to-Text
    SARVAM_API_KEY: str = Field(default_factory=lambda: os.getenv("SARVAM_API_KEY", ""))
    SARVAM_STT_URL: str = Field(default="https://api.sarvam.ai/speech-to-text-translate")

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

    # Retrieval parameters
    RETRIEVAL_TOP_K: int = Field(default=5)
    RELEVANCE_THRESHOLD: float = Field(default=0.012)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
