"""
Configuration Settings for NL2SQL AI Agent Backend
Uses pydantic-settings for type-safe configuration management
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # ========================================================================
    # Database Configuration
    # ========================================================================
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "Adventureworks"
    DATABASE_USER: str
    DATABASE_PASSWORD: str

    @property
    def database_url(self) -> str:
        """PostgreSQL connection URL for psycopg2"""
        return f"postgresql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"

    @property
    def async_database_url(self) -> str:
        """Async PostgreSQL connection URL for SQLAlchemy"""
        return f"postgresql+asyncpg://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"

    # ========================================================================
    # AI API Keys
    # ========================================================================
    OPENAI_API_KEY: str
    ANTHROPIC_API_KEY: str

    # ========================================================================
    # Embedding Configuration
    # ========================================================================
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536

    # ========================================================================
    # LLM Configuration
    # ========================================================================
    # Fast model for routing and validation (cost-effective)
    CLAUDE_HAIKU_MODEL: str = "claude-haiku-4-5"
    # Premium model for SQL generation and analysis (quality-critical)
    CLAUDE_SONNET_MODEL: str = "claude-sonnet-4-5"

    LLM_MODEL: str = "claude-sonnet-4-5"  # Default model
    LLM_TEMPERATURE: float = 0.0
    LLM_MAX_TOKENS: int = 4000

    # ========================================================================
    # RAG Configuration
    # ========================================================================
    TOP_K_TABLES: int = 5  # Optimized: reduced from 8 to 5 for token efficiency
    ENABLE_ANCHOR_TABLES: bool = True

    # ========================================================================
    # Redis Configuration
    # ========================================================================
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0

    @property
    def redis_url(self) -> str:
        """Redis connection URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ========================================================================
    # Authentication Configuration
    # ========================================================================
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120

    # ========================================================================
    # Application Settings
    # ========================================================================
    DEBUG: bool = False
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_TITLE: str = "NL2SQL AI Agent API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "Advanced NL2SQL with Visualization Intelligence"

    # CORS Settings - Allow all origins for Cloudflare tunnel access
    CORS_ORIGINS: list[str] = ["*"]

    # ========================================================================
    # Pydantic Configuration
    # ========================================================================
    class Config:
        # Look for .env in project root (parent of backend/)
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        env_file = str(project_root / ".env")
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields in .env


# Global settings instance
settings = Settings()


def validate_settings():
    """
    Validate critical settings on startup
    Raises ValueError if critical configs are missing
    """
    critical_fields = [
        "DATABASE_USER",
        "DATABASE_PASSWORD",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "JWT_SECRET_KEY"
    ]

    missing = []
    for field in critical_fields:
        value = getattr(settings, field, None)
        if not value:
            missing.append(field)

    if missing:
        raise ValueError(
            f"Missing critical configuration fields: {', '.join(missing)}\n"
            f"Please check your .env file."
        )

    print(" Configuration validated successfully")
    return True
