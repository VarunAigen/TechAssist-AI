"""Application configuration loaded from environment variables."""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings:
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "dev")  # dev | staging | prod

    # Groq
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

    # JWT
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")  # PostgreSQL connection string
    SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "./app_data.db")

    # Embeddings
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "sentence-transformers")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"
    ST_MODEL_NAME: str = "all-MiniLM-L6-v2"

    # ChromaDB
    CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
    CHROMA_COLLECTION_PREFIX: str = "kb_"  # Each tenant gets kb_{tenant_id}

    # CORS
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")

    # Chunking
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50

    # Retrieval
    TOP_K_RESULTS: int = 5
    HIGH_CONFIDENCE_THRESHOLD: float = 0.80
    MEDIUM_CONFIDENCE_THRESHOLD: float = 0.50

    # Rate Limiting
    RATE_LIMIT_CHAT: str = os.getenv("RATE_LIMIT_CHAT", "30/minute")
    RATE_LIMIT_LOGIN: str = os.getenv("RATE_LIMIT_LOGIN", "5/minute")

    # Input Validation
    MAX_QUESTION_LENGTH: int = 2000
    MAX_UPLOAD_SIZE_MB: int = 10

    @classmethod
    def validate(cls):
        """Validate critical settings on startup."""
        errors = []
        if cls.ENVIRONMENT == "prod":
            if cls.JWT_SECRET == "change-me-in-production":
                errors.append("JWT_SECRET must be changed in production")
            if not cls.DATABASE_URL:
                errors.append("DATABASE_URL must be set in production")
            if not cls.GROQ_API_KEY:
                errors.append("GROQ_API_KEY must be set")
        if errors:
            raise ValueError(
                "Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors)
            )


settings = Settings()
