"""Tests for shared AI analysis provider configuration, error mapping, and fallbacks."""
import io
import json
import os
import time
from pathlib import Path
from threading import Event
from unittest.mock import MagicMock, patch
from uuid import UUID
import pytest
import httpx
from fastapi.testclient import TestClient

from config import Settings
from errors import ServiceError
from llm import GroqLLM
from main import create_app
from product_schemas import WorkspaceQuestion
from providers import create_provider
from schemas import (
    AnswerResult,
    ChatRequest,
    Chunk,
    DocumentMetadata,
    DocumentRecord,
    DocumentRequest,
    Finding,
    MapResult,
    PageText,
)
from audit import deterministic_audit
from audit_schemas import AuditRequest, ClauseType, ContractClassification, IndiaContext, Risk
from storage import ChromaIndex, DocumentStore


def test_unconfigured_provider_error_message(tmp_path):
    settings = Settings(groq_api_key="", openai_api_key="", ollama_base_url="", data_dir=tmp_path)
    provider = create_provider(settings)

    # Provider should report unconfigured with actionable instructions
    with pytest.raises(ServiceError) as exc:
        provider.generate(AnswerResult, "test prompt", deadline=time.monotonic() + 10.0)

    assert exc.value.status == 503
    assert "The AI analysis provider is not configured" in exc.value.message
    assert "GROQ_API_KEY" in exc.value.message


def test_placeholder_api_key_considered_unconfigured(tmp_path):
    settings = Settings(groq_api_key="your_groq_api_key_here", data_dir=tmp_path)
    provider = create_provider(settings)
    with pytest.raises(ServiceError) as exc:
        provider.generate(AnswerResult, "test prompt", deadline=time.monotonic() + 10.0)
    assert exc.value.status == 503
    assert "The AI analysis provider is not configured" in exc.value.message


def test_provider_status_code_mappings(tmp_path):
    settings = Settings(data_dir=tmp_path)
    llm = GroqLLM(settings, api_key="mock-key", model="test-model")
    cancelled = Event()

    # Timeout -> 504
    with patch("httpx.Client.stream", side_effect=httpx.TimeoutException("Read timed out")):
        with pytest.raises(ServiceError) as exc:
            list(llm.stream_json(AnswerResult, "test", deadline=time.monotonic() + 10.0, cancelled=cancelled))
        assert exc.value.status == 504
        assert "timed out" in exc.value.message.lower()

    # Unreachable / ConnectError -> 503
    with patch("httpx.Client.stream", side_effect=httpx.ConnectError("Failed to connect")):
        with pytest.raises(ServiceError) as exc:
            list(llm.stream_json(AnswerResult, "test", deadline=time.monotonic() + 10.0, cancelled=cancelled))
        assert exc.value.status == 503
        assert "unreachable" in exc.value.message.lower()

    # Rate limit -> 503
    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429
    with patch("httpx.Client.stream") as mock_stream:
        mock_stream.return_value.__enter__.return_value = mock_resp_429
        with pytest.raises(ServiceError) as exc:
            list(llm.stream_json(AnswerResult, "test", deadline=time.monotonic() + 10.0, cancelled=cancelled))
        assert exc.value.status == 503
        assert "rate limited" in exc.value.message.lower()

    # Auth failure -> 502
    mock_resp_401 = MagicMock()
    mock_resp_401.status_code = 401
    with patch("httpx.Client.stream") as mock_stream:
        mock_stream.return_value.__enter__.return_value = mock_resp_401
        with pytest.raises(ServiceError) as exc:
            list(llm.stream_json(AnswerResult, "test", deadline=time.monotonic() + 10.0, cancelled=cancelled))
        assert exc.value.status == 502
        assert "authentication failed" in exc.value.message.lower()

    # Provider 400 Bad Request / 404 Not Found -> 502 with message
    mock_resp_400 = MagicMock()
    mock_resp_400.status_code = 400
    mock_resp_400.json.return_value = {"error": {"message": "The model 'deprecated-model' does not exist"}}
    with patch("httpx.Client.stream") as mock_stream:
        mock_stream.return_value.__enter__.return_value = mock_resp_400
        with pytest.raises(ServiceError) as exc:
            list(llm.stream_json(AnswerResult, "test", deadline=time.monotonic() + 10.0, cancelled=cancelled))
        assert exc.value.status == 502
        assert "rejected the request" in exc.value.message
        assert "deprecated-model" in exc.value.message


def test_generate_error_mappings(tmp_path):
    settings = Settings(data_dir=tmp_path, structured_retries=0)
    llm = GroqLLM(settings, api_key="mock-key", model="test-model")

    # 401 Auth error in generate
    mock_resp_401 = MagicMock()
    mock_resp_401.status_code = 401
    with patch("httpx.Client.post", return_value=mock_resp_401):
        with pytest.raises(ServiceError) as exc:
            llm.generate(AnswerResult, "test", deadline=time.monotonic() + 10.0)
        assert exc.value.status == 502
        assert "authentication failed" in exc.value.message.lower()

    # 400 Model not found error in generate
    mock_resp_400 = MagicMock()
    mock_resp_400.status_code = 400
    mock_resp_400.json.return_value = {"error": {"message": "Invalid model specified"}}
    with patch("httpx.Client.post", return_value=mock_resp_400):
        with pytest.raises(ServiceError) as exc:
            llm.generate(AnswerResult, "test", deadline=time.monotonic() + 10.0)
        assert exc.value.status == 502
        assert "Invalid model specified" in exc.value.message

    # Timeout in generate -> 504
    with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Read timed out")):
        with pytest.raises(ServiceError) as exc:
            llm.generate(AnswerResult, "test", deadline=time.monotonic() + 10.0)
        assert exc.value.status == 504


def test_env_loading_and_model_configuration(tmp_path, monkeypatch):
    backend_dir = Path(__file__).resolve().parent.parent
    env_file = backend_dir / ".env"
    existing_content = env_file.read_text() if env_file.exists() else None

    test_key = "gsk_test_groq_key_12345"
    test_model = "llama-3.3-70b-versatile"

    try:
        # Write temporary .env in contractiq-backend
        env_file.write_text(f"GROQ_API_KEY={test_key}\nGROQ_MODEL={test_model}\n")

        # Simulate empty env var in shell
        monkeypatch.setenv("GROQ_API_KEY", "")
        monkeypatch.delenv("GROQ_MODEL", raising=False)

        # Run from_env() while changing cwd to an arbitrary directory
        arbitrary_dir = tmp_path / "arbitrary"
        arbitrary_dir.mkdir()
        monkeypatch.chdir(arbitrary_dir)

        loaded_settings = Settings.from_env()
        assert loaded_settings.groq_api_key == test_key
        assert loaded_settings.groq_model == test_model
    finally:
        if existing_content is not None:
            env_file.write_text(existing_content)
        elif env_file.exists():
            env_file.unlink()


def test_default_groq_model_is_current():
    settings = Settings()
    # Ensure default model is not the deprecated or fake ID
    assert settings.groq_model == "llama-3.3-70b-versatile"
    assert "gpt-oss-20b" not in settings.groq_model
    assert "8192" not in settings.groq_model


def test_provider_chain_selection(tmp_path):
    # Only Groq
    s_groq = Settings(groq_api_key="groq-key", data_dir=tmp_path)
    chain_groq = create_provider(s_groq)
    assert len(chain_groq.providers) == 1
    assert chain_groq.providers[0].name == "groq"
    assert chain_groq.providers[0].api_key == "groq-key"
    assert chain_groq.providers[0].model == "llama-3.3-70b-versatile"

    # OpenAI configured
    s_openai = Settings(openai_api_key="openai-key", data_dir=tmp_path)
    chain_openai = create_provider(s_openai)
    assert len(chain_openai.providers) == 1
    assert chain_openai.providers[0].name == "openai"
    assert chain_openai.providers[0].api_key == "openai-key"

    # Ollama configured
    s_ollama = Settings(ollama_base_url="http://localhost:11434", data_dir=tmp_path)
    chain_ollama = create_provider(s_ollama)
    assert len(chain_ollama.providers) == 1
    assert chain_ollama.providers[0].name == "ollama"

    # Multiple providers ordered: Groq first, then OpenAI, then Ollama
    s_multi = Settings(groq_api_key="g-key", openai_api_key="o-key", ollama_base_url="http://ollama", data_dir=tmp_path)
    chain_multi = create_provider(s_multi)
    assert len(chain_multi.providers) == 3
    assert [p.name for p in chain_multi.providers] == ["groq", "openai", "ollama"]


def test_deterministic_india_audit_without_ai(tmp_path):
    settings = Settings(data_dir=tmp_path)
    metadata = DocumentMetadata(
        doc_id="00000000-0000-0000-0000-000000000001",
        filename="Sample_Agreement_For_Sale.pdf",
        chars=500,
        num_chunks=2,
        created_at=1000.0,
        expires_at=2000.0,
        has_pdf=True,
    )
    chunks = [
        Chunk(
            id="c1",
            text="The Promoter shall provide a 5-year defect liability period under RERA.",
            page=1,
            start=0,
            end=65,
            page_start=0,
            page_end=65,
        ),
        Chunk(
            id="c2",
            text="Any dispute shall be subject to exclusive jurisdiction of Mumbai courts.",
            page=1,
            start=70,
            end=140,
            page_start=70,
            page_end=140,
        ),
    ]
    record = DocumentRecord(metadata=metadata, chunks=chunks)
    context = IndiaContext(enabled=True)

    result = deterministic_audit(record, settings, context)
    assert result.doc_id == metadata.doc_id
    assert len(result.rule_checks) == 7
    assert all(c.status in ("pass", "warning", "context_needed", "info") for c in result.rule_checks)
    assert "informational" in result.summary.lower() or "statutory" in result.summary.lower()


def test_ai_endpoints_with_mocked_groq_provider(tmp_path):
    """Verify Chat, Benefits, Workspace Chat, and Property Due Diligence work with Groq."""
    settings = Settings(
        data_dir=tmp_path,
        groq_api_key="mock-groq-key",
        rate_limit_requests=1000,
        retriever_strategy="dense",
        pii_mode="patterns",
        ocr_enabled=False,
    )

    class FakeIndex:
        def add(self, directory: Path, chunks: list[Chunk]) -> None:
            directory.mkdir(parents=True, exist_ok=True)
            (directory / "ids.json").write_text(json.dumps([chunk.id for chunk in chunks]))

        def search(self, directory: Path, question: str, k: int) -> list[tuple[str, float]]:
            return [(key, 0.1) for key in json.loads((directory / "ids.json").read_text())[:k]]

        def embed(self, texts: list[str]) -> list[list[float]]:
            return [[0.1] * 384 for _ in texts]

    def mock_post(request):
        payload = json.loads(request.content)
        schema_name = payload.get("response_format", {}).get("json_schema", {}).get("name", "")
        if "MapResult" in schema_name:
            content = json.dumps({"items": []})
        elif "WorkspaceResult" in schema_name:
            user_msg = payload.get("messages", [{}])[-1].get("content", "")
            if "Document 2" in user_msg:
                content = json.dumps({"answer": "Both documents state 3 year term [Excerpt 1] [Excerpt 2].", "excerpt_ids": [1, 2]})
            else:
                content = json.dumps({"answer": "The single document states 3 year term [Excerpt 1].", "excerpt_ids": [1]})
        elif "ContractClassification" in schema_name:
            content = json.dumps({"contract_type": "lease", "confidence": 0.95})
        elif "ClauseBatch" in schema_name:
            content = json.dumps({"clauses": []})
        else:
            content = json.dumps({"answer": "The lease duration is 3 years [Excerpt 1].", "excerpt_ids": [1]})

        return httpx.Response(200, json={
            "choices": [{"finish_reason": "stop", "message": {"content": content}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        })

    transport = httpx.MockTransport(mock_post)
    client_mock = httpx.Client(transport=transport)
    llm = GroqLLM(settings, client=client_mock, api_key="mock-groq-key")

    from rag_pipeline import RAGService
    store = DocumentStore(settings, FakeIndex())
    service = RAGService(settings, store, llm)

    doc1 = service.ingest_document("doc1.txt", b"The lease duration is 3 years. Rent is payable monthly.")
    doc2 = service.ingest_document("doc2.txt", b"The agreement shall remain in force for 3 years. Maintenance is included.")

    app = create_app(settings=settings, service=service)
    with TestClient(app, raise_server_exceptions=False) as client:
        # 1. Chat
        chat_resp = client.post("/chat", json={"doc_id": str(doc1.doc_id), "question": "What is the lease duration?"})
        assert chat_resp.status_code == 200
        assert "lease duration" in chat_resp.json()["answer"]

        # 2. Benefits
        benefits_resp = client.post("/benefits", json={"doc_id": str(doc1.doc_id)})
        assert benefits_resp.status_code == 200
        assert isinstance(benefits_resp.json()["items"], list)

        # 3. Workspace Chat (Ask Across Documents - Multi Document)
        ws_resp = client.post("/workspace/chat", json={
            "doc_ids": [str(doc1.doc_id), str(doc2.doc_id)],
            "question": "What is the term across both contracts?",
        })
        assert ws_resp.status_code == 200
        assert "Both documents" in ws_resp.json()["answer"]

        # 3b. Workspace Chat (Ask Across Documents - Exactly ONE Document)
        single_ws_resp = client.post("/workspace/chat", json={
            "doc_ids": [str(doc1.doc_id)],
            "question": "What is the term for this agreement?",
        })
        assert single_ws_resp.status_code == 200
        assert "The single document" in single_ws_resp.json()["answer"]
        assert len(single_ws_resp.json()["sources"]) == 1

        # 4. Property Due Diligence (Deterministic cross-validation)
        dd_resp = client.post("/property/due-diligence", json={"doc_ids": [str(doc1.doc_id), str(doc2.doc_id)]})
        assert dd_resp.status_code == 200
        assert "cross_document_findings" in dd_resp.json()
