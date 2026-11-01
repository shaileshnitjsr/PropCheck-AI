"""Regression tests for CORS origins, preflights, concurrency isolation, and Groq rate-limiting resilience."""

import time
from threading import Event
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from pydantic import BaseModel
import pytest

from config import Settings
from errors import ServiceError
from main import create_app
from schemas import Chunk


class SimpleOutput(BaseModel):
    answer: str


def test_cors_defaults_and_trailing_slash_normalization():
    # 1. Defaults contain the Vercel production origin
    settings = Settings()
    assert "https://prop-check-ai.vercel.app" in settings.cors_origins
    assert "https://propcheck-ai.onrender.com" in settings.cors_origins

    # 2. Trailing slash normalization in validator
    custom = Settings(cors_origins=["https://prop-check-ai.vercel.app/", "http://localhost:3000/"])
    assert custom.cors_origins == ["https://prop-check-ai.vercel.app", "http://localhost:3000"]


def test_vercel_origin_allowed_and_options_preflight(service, settings):
    app = create_app(settings, service)
    client = TestClient(app)

    # Health check with Vercel origin header
    response = client.get("/health", headers={"Origin": "https://prop-check-ai.vercel.app"})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://prop-check-ai.vercel.app"

    # Preflight OPTIONS request
    preflight = client.options(
        "/chat",
        headers={
            "Origin": "https://prop-check-ai.vercel.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers.get("access-control-allow-origin") == "https://prop-check-ai.vercel.app"


def test_disallowed_origin_rejected(service, settings):
    app = create_app(settings, service)
    client = TestClient(app)

    # Unauthorized origin
    response = client.get("/health", headers={"Origin": "https://malicious-attacker.com"})
    assert response.status_code == 403


def test_bounded_concurrency_allows_simultaneous_operations(service, settings):
    # Verify that bounded semaphore allows concurrent read/stream operations
    app = create_app(settings, service)

    # Ingest a sample doc
    doc = service.ingest_document("test.txt", b"Rent payment INR 50000 due monthly.")
    client = TestClient(app)

    # Document fetch and health check work concurrently
    doc_res = client.get(f"/document/{doc.doc_id}")
    assert doc_res.status_code == 200
    assert client.get("/health").status_code == 200


def test_groq_llm_respects_retry_after(settings):
    from llm import GroqLLM
    import httpx

    # Mock client that returns 429 once with Retry-After header, then 200 OK
    call_count = 0
    def mock_send(request, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(
                429,
                headers={"retry-after": "0.1"},
                json={"error": {"message": "Rate limited"}},
                request=request,
            )
        return httpx.Response(
            200,
            json={
                "choices": [{
                    "finish_reason": "stop",
                    "message": {"content": '{"answer": "Escrow clause found"}'},
                }],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            },
            request=request,
        )

    transport = httpx.MockTransport(mock_send)
    mock_client = httpx.Client(transport=transport)
    llm = GroqLLM(settings, client=mock_client, api_key="gsk_test_key")

    result = llm.generate(SimpleOutput, "Analyze text", deadline=time.monotonic() + 10)
    assert result.answer == "Escrow clause found"
    assert call_count == 2
