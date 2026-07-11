"""Odyssey configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "", "env_file": ".env", "extra": "ignore"}

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "odyssey_dev"

    # PostgreSQL
    postgres_dsn: str = "postgresql://odyssey:odyssey_dev@localhost:5433/odyssey"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Anthropic
    anthropic_api_key: str = ""

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_key: str = "odyssey-dev-key"

    # LLM defaults
    llm_model: str = "claude-haiku-4-5-20251001"
    llm_reasoning_model: str = "claude-haiku-4-5-20251001"
    llm_max_tokens: int = 4096


settings = Settings()
