"""Validated limits and explicit local/production infrastructure configuration."""

import os
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True, hide_input_in_errors=True)

    data_dir: Path = Path("data")
    model_cache_dir: Path = Path("model-cache")
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
        "http://127.0.0.1:3003",
    ]
    groq_api_key: str = Field(default="", repr=False)
    groq_model: str = "llama-3.3-70b-versatile"
    openai_api_key: str = Field(default="", repr=False)
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    ollama_base_url: str = ""
    ollama_model: str = "llama3"
    structured_mode: str = "json_schema"
    max_upload_bytes: int = Field(default=2 * 1024 * 1024, ge=1024, le=20 * 1024 * 1024)
    max_text_chars: int = Field(default=100_000, ge=1000, le=500_000)
    max_chunks: int = Field(default=120, ge=1, le=600)
    max_documents: int = Field(default=100, ge=1, le=1000)
    document_ttl_seconds: int = Field(default=3600, ge=1)
    cleanup_interval_seconds: int = Field(default=60, ge=1, le=3600)
    rate_limit_requests: int = Field(default=120, ge=1)
    rate_limit_window_seconds: int = Field(default=60, ge=1)
    llm_timeout_seconds: int = Field(default=45, ge=1, le=120)
    analysis_timeout_seconds: int = Field(default=240, ge=1, le=1800)
    structured_retries: int = Field(default=1, ge=0, le=2)
    map_batch_chars: int = Field(default=6000, ge=1000, le=12000)
    chunking_strategy: Literal["recursive", "clause"] = "clause"
    retriever_strategy: Literal["dense", "hybrid", "hybrid_rerank"] = "hybrid_rerank"
    retrieval_candidates: int = Field(default=12, ge=4, le=40)
    reranker_model: str = "Xenova/ms-marco-MiniLM-L-6-v2"
    pii_mode: Literal["standard", "patterns"] = "standard"
    pii_model: str = "en_core_web_sm"
    ocr_enabled: bool = True
    ocr_language: str = "eng"
    max_ocr_pages: int = Field(default=10, ge=1, le=30)
    ocr_timeout_seconds: int = Field(default=20, ge=1, le=60)
    india_rule_pack: bool = True
    audit_max_clauses: int = Field(default=200, ge=1, le=600)
    app_mode: Literal["local", "production"] = "local"
    database_url: str = Field(default="", repr=False)
    redis_url: str = Field(default="", repr=False)
    supabase_url: str = ""
    s3_endpoint: str = ""
    s3_public_endpoint: str = ""
    s3_bucket: str = "contractiq"
    s3_region: str = "us-east-1"
    s3_access_key: str = Field(default="", repr=False)
    s3_secret_key: str = Field(default="", repr=False)
    signed_url_seconds: int = Field(default=60, ge=1, le=300)
    ingestion_timeout_seconds: int = Field(default=600, ge=30, le=1800)
    cache_ttl_seconds: int = Field(default=120, ge=1, le=600)
    fallback_api_key: str = Field(default="", repr=False)
    fallback_base_url: str = ""
    fallback_model: str = ""
    fallback_structured_mode: Literal["json_schema", "json_object"] = "json_object"
    sentry_dsn: str = Field(default="", repr=False)
    langfuse_public_key: str = Field(default="", repr=False)
    langfuse_secret_key: str = Field(default="", repr=False)
    langfuse_base_url: str = "https://cloud.langfuse.com"
    telemetry_enabled: bool = False

    @model_validator(mode="after")
    def production_configuration(self) -> "Settings":
        if self.app_mode == "production":
            for name in ("database_url", "redis_url", "supabase_url", "s3_endpoint", "s3_access_key", "s3_secret_key"):
                if not getattr(self, name):
                    raise ValueError(f"Production requires {name.upper()}")
            if not self.supabase_url.startswith("https://"):
                raise ValueError("Supabase must use HTTPS")
        if any((self.fallback_api_key, self.fallback_base_url, self.fallback_model)):
            if not all((self.fallback_api_key, self.fallback_base_url, self.fallback_model)):
                raise ValueError("Configure all three fallback provider values")
            parsed = urlsplit(self.fallback_base_url)
            if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.query or parsed.fragment:
                raise ValueError("Fallback provider requires a trusted HTTPS base URL")
        return self

    @field_validator("cors_origins")
    @classmethod
    def explicit_origins(cls, origins: list[str]) -> list[str]:
        if not origins:
            raise ValueError("CORS_ORIGINS must contain at least one explicit origin")
        for origin in origins:
            parts = urlsplit(origin)
            if (
                "*" in origin or parts.scheme not in {"http", "https"}
                or not parts.netloc or parts.path or parts.query or parts.fragment
                or parts.username or parts.password
            ):
                raise ValueError("CORS_ORIGINS must contain exact http(s) origins without paths")
        return origins

    @field_validator("structured_mode")
    @classmethod
    def supported_mode(cls, mode: str) -> str:
        if mode not in {"json_schema", "json_object"}:
            raise ValueError("STRUCTURED_MODE must be json_schema or json_object")
        return mode

    @property
    def has_llm_provider(self) -> bool:
        return bool(self.groq_api_key or self.openai_api_key or self.ollama_base_url or self.fallback_api_key)

    @classmethod
    def from_env(cls) -> "Settings":
        try:
            from dotenv import load_dotenv
            backend_dir = Path(__file__).resolve().parent
            candidates = [
                backend_dir / ".env",
                backend_dir / ".env.local",
                backend_dir.parent / ".env",
                backend_dir.parent / ".env.local",
                Path.cwd() / "contractiq-backend" / ".env",
                Path.cwd() / ".env",
            ]
            explicit_env = {k: v for k, v in os.environ.items() if v.strip()}
            for env_path in candidates:
                if env_path.is_file():
                    load_dotenv(env_path, override=True)
            # Retain non-empty explicit environment variables from shell/process
            os.environ.update(explicit_env)
        except Exception:
            pass
        values: dict[str, object] = {}
        for name in cls.model_fields:
            value = os.getenv(name.upper())
            if value is not None:
                if isinstance(value, str):
                    s = value.strip().strip("'\"")
                    if s:
                        values[name] = s
                else:
                    values[name] = value
        if "cors_origins" in values:
            values["cors_origins"] = [
                v.strip() for v in str(values["cors_origins"]).split(",") if v.strip()
            ]
        if "data_dir" not in values and (backend_dir / "data").exists():
            values["data_dir"] = backend_dir / "data"
        if "model_cache_dir" not in values and (backend_dir / "model-cache").exists():
            values["model_cache_dir"] = backend_dir / "model-cache"
        return cls.model_validate(values)
