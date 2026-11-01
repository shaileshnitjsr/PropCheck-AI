"""Per-document Chroma directories and manifests, with TTL and physical deletion."""

import logging
import re
import shutil
import threading
import time
from collections.abc import Callable, Sequence
from hashlib import sha256
from pathlib import Path
from typing import Protocol, cast
from uuid import UUID, uuid4

from config import Settings
from errors import MissingDocument, ServiceError
from schemas import Chunk, DocumentMetadata, DocumentRecord, PageText

logger = logging.getLogger(__name__)
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class VectorIndex(Protocol):
    def add(self, directory: Path, chunks: list[Chunk]) -> None: ...
    def search(self, directory: Path, question: str, k: int) -> list[tuple[str, float]]: ...


class ChromaIndex:
    """Open/close each client so deletion releases SQLite and HNSW handles."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self._embed: Callable[[list[str]], list[list[float]]] | None = None

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self._embed is None:
            from fastembed import TextEmbedding

            model = TextEmbedding(EMBEDDING_MODEL, threads=1, cache_dir=str(self.cache_dir))
            self._embed = lambda values: [vector.tolist() for vector in model.embed(values, batch_size=16)]
        return self._embed(texts)

    def add(self, directory: Path, chunks: list[Chunk]) -> None:
        import chromadb
        from chromadb.api.client import Client
        from chromadb.config import Settings as ChromaSettings

        vectors: list[Sequence[float] | Sequence[int]] = list(self.embed([chunk.text for chunk in chunks]))
        client = cast(Client, chromadb.PersistentClient(
            path=str(directory), settings=ChromaSettings(anonymized_telemetry=False)
        ))
        try:
            collection = client.create_collection(
                "contract", embedding_function=None,
                configuration={"hnsw": {"space": "cosine", "num_threads": 1}},
            )
            collection.add(ids=[chunk.id for chunk in chunks], embeddings=vectors)
        finally:
            client.close()

    def search(self, directory: Path, question: str, k: int) -> list[tuple[str, float]]:
        import chromadb
        from chromadb.api.client import Client
        from chromadb.config import Settings as ChromaSettings

        vectors: list[Sequence[float] | Sequence[int]] = list(self.embed([question]))
        client = cast(Client, chromadb.PersistentClient(
            path=str(directory), settings=ChromaSettings(anonymized_telemetry=False)
        ))
        try:
            collection = client.get_collection("contract", embedding_function=None)
            result = collection.query(query_embeddings=vectors, n_results=k, include=["distances"])
            distances = result["distances"]
            if distances is None:
                return []
            return list(zip(result["ids"][0], distances[0], strict=True))
        finally:
            client.close()


def extract_meaningful_title(text: str) -> str | None:
    if not text or not text.strip():
        return None

    sample = text[:5000]

    # 1. Document Type Patterns
    doc_type = None
    doc_type_patterns = [
        (r"(?i)\bAgreement\s+for\s+Sale\b", "Agreement_for_Sale"),
        (r"(?i)\bAllotment\s+Letter\b", "Allotment_Letter"),
        (r"(?i)\bRegistration\s+Certificate(?:\s+of\s+Project)?\b", "Registration_Certificate"),
        (r"(?i)\bSale\s+Deed\b", "Sale_Deed"),
        (r"(?i)\bConveyance\s+Deed\b", "Conveyance_Deed"),
        (r"(?i)\bLeave\s+(?:and|&)\s+Licen[sc]e(?:\s+Agreement)?\b", "Leave_and_License"),
        (r"(?i)\bLease\s+Agreement\b", "Lease_Agreement"),
        (r"(?i)\bProject\s+Brochure\b|\bBrochure\b", "Brochure"),
        (r"(?i)\bPossession\s+Letter\b", "Possession_Letter"),
        (r"(?i)\bTripartite\s+Agreement\b", "Tripartite_Agreement"),
    ]
    for pattern, name in doc_type_patterns:
        if re.search(pattern, sample):
            doc_type = name
            break

    # 2. Project Name Patterns
    project_name = None
    proj_patterns = [
        r"(?i)\b(?:Project\s+Name|Project)\s*[:\-–]\s*[\"']?([A-Za-z0-9\s&'-]{3,35}?)[\"']?(?:\r?\n|$|\s{2,})",
        r"(?i)\b(?:known\s+as|project\s+named|project\s+called)\s+[\"'\u201c]([A-Za-z0-9\s&'-]{3,35}?)[\"'\u201d]",
        r"(?i)\b(?:residential|commercial)?\s*project\s+[\"'\u201c]([A-Za-z0-9\s&'-]{3,35}?)[\"'\u201d]",
        r"(?i)\b(?:Apartment\s+in|Flat\s+in|Unit\s+in|project\s+in)\s+[\"'\u201c]([A-Za-z0-9\s&'-]{3,35}?)[\"'\u201d]",
        r"(?i)\b(?:residential\s+project|commercial\s+project|project\s+known\s+as|project)\s+([A-Z][A-Za-z0-9\s&'-]{3,30}?(?:Residency|Enclave|Gardens|Heights|Towers|Greens|Palms|Estate|City|Park|Villas|Square|Grande|Pratham))\b",
    ]
    for pattern in proj_patterns:
        m = re.search(pattern, sample)
        if m:
            raw_proj = m.group(1).strip()
            clean_proj = re.sub(r"[^\w\s-]", "", raw_proj).strip()
            clean_proj = re.sub(r"[\s-]+", "_", clean_proj)
            if len(clean_proj) >= 3:
                project_name = clean_proj
                break

    if doc_type and project_name:
        return f"{doc_type}_{project_name}"
    if project_name:
        return project_name
    if doc_type:
        return doc_type
    return None


def resolve_unique_filename(
    candidate: str, existing_names: set[str], full_text: str = ""
) -> str:
    norm_candidate = candidate.strip()
    is_generic = (
        norm_candidate.lower().replace("-", "_").startswith("pasted_document")
        or norm_candidate.lower() in ("document.txt", "document", "contract.txt", "contract")
    )

    if is_generic:
        title = extract_meaningful_title(full_text)
        if title:
            base_name = f"{title}.txt"
            if base_name.lower() not in existing_names:
                return base_name
            counter = 2
            while f"{title}_{counter}.txt".lower() in existing_names:
                counter += 1
            return f"{title}_{counter}.txt"
        else:
            counter = 1
            while f"Pasted_Document_{counter}.txt".lower() in existing_names or (counter == 1 and "pasted-document.txt" in existing_names):
                counter += 1
            return f"Pasted_Document_{counter}.txt"

    # For normal file uploads
    if norm_candidate.lower() not in existing_names:
        return norm_candidate

    path = Path(norm_candidate)
    stem = path.stem
    suffix = path.suffix or ".txt"
    counter = 2
    while f"{stem}_{counter}{suffix}".lower() in existing_names:
        counter += 1
    return f"{stem}_{counter}{suffix}"


class DocumentStore:
    def __init__(self, settings: Settings, index: VectorIndex, clock: Callable[[], float] = time.time):
        self.settings = settings
        self.index = index
        self.clock = clock
        self.root = (settings.data_dir / "documents").resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()

    def directory(self, doc_id: str) -> Path:
        try:
            normalized = str(UUID(doc_id))
        except ValueError as exc:
            raise MissingDocument() from exc
        return self.root / normalized

    def create(
        self, filename: str, chars: int, chunks: list[Chunk], *,
        pages: list[PageText] | None = None, pdf: bytes | None = None,
        content_hash: str | None = None,
    ) -> DocumentMetadata:
        with self.lock:
            self.cleanup()
            calculated_hash = content_hash or (
                sha256(pdf).hexdigest() if pdf is not None
                else sha256("".join(chunk.text for chunk in chunks).encode("utf-8")).hexdigest()
            )
            # Idempotency check: see if an unexpired document with identical filename/stem and content already exists
            for child in self.root.iterdir():
                if not child.is_dir() or child.is_symlink():
                    continue
                try:
                    existing = self.get(child.name)
                except MissingDocument:
                    continue

                same_name = (existing.metadata.filename.lower() == filename.lower())
                same_stem = (Path(existing.metadata.filename).stem.lower() == Path(filename).stem.lower())
                if not (same_name or (same_stem and pdf is not None and not existing.metadata.has_pdf)):
                    continue

                match = False
                if existing.metadata.content_hash:
                    match = (existing.metadata.content_hash == calculated_hash)
                elif pdf is not None and (child / "source.pdf").exists():
                    try:
                        match = (sha256((child / "source.pdf").read_bytes()).hexdigest() == calculated_hash)
                    except OSError:
                        pass
                elif existing.chunks:
                    existing_chunk_hash = sha256("".join(c.text for c in existing.chunks).encode("utf-8")).hexdigest()
                    match = (existing_chunk_hash == calculated_hash)

                if match:
                    now = self.clock()
                    update_fields: dict[str, object] = {
                        "expires_at": now + self.settings.document_ttl_seconds,
                        "content_hash": calculated_hash,
                    }
                    if pdf is not None and not existing.metadata.has_pdf:
                        try:
                            (child / "source.pdf").write_bytes(pdf)
                            update_fields["has_pdf"] = True
                            if filename.lower().endswith(".pdf"):
                                update_fields["filename"] = filename
                        except OSError:
                            pass
                    updated_meta = existing.metadata.model_copy(update=update_fields)
                    updated_record = existing.model_copy(update={"metadata": updated_meta})
                    try:
                        (child / "document.json").write_text(updated_record.model_dump_json(), encoding="utf-8")
                    except OSError:
                        pass
                    return updated_meta

            if len(list(self.root.iterdir())) >= self.settings.max_documents:
                raise ServiceError(503, "Document capacity reached. Delete an earlier upload or retry later.")

            existing_names = set()
            for child in self.root.iterdir():
                if not child.is_dir() or child.is_symlink():
                    continue
                try:
                    existing_doc = self.get(child.name)
                    existing_names.add(existing_doc.metadata.filename.lower())
                except MissingDocument:
                    continue

            full_text = "\n".join(chunk.text for chunk in chunks)
            unique_filename = resolve_unique_filename(filename, existing_names, full_text=full_text)

            doc_id = uuid4()
            directory = self.directory(str(doc_id))
            directory.mkdir()
            now = self.clock()
            metadata = DocumentMetadata(
                doc_id=doc_id, filename=unique_filename, chars=chars, num_chunks=len(chunks),
                created_at=now, expires_at=now + self.settings.document_ttl_seconds,
                has_pdf=pdf is not None, ocr_pages=sum(page.ocr for page in pages or []),
                chunking_strategy=self.settings.chunking_strategy,
                content_hash=calculated_hash,
            )
            record = DocumentRecord(metadata=metadata, chunks=chunks, pages=pages or [])
            try:
                if pdf is not None:
                    (directory / "source.pdf").write_bytes(pdf)
                self.index.add(directory / "vectors", chunks)
                (directory / "document.json").write_text(record.model_dump_json(), encoding="utf-8")
            except Exception:
                self._remove(directory)
                raise
            self.get(str(doc_id))
            return metadata

    def pdf(self, doc_id: str) -> bytes:
        with self.lock:
            record = self.get(doc_id)
            if not record.metadata.has_pdf:
                raise ServiceError(404, "No original PDF is retained for this document. Re-upload if needed.")
            return (self.directory(doc_id) / "source.pdf").read_bytes()

    def get(self, doc_id: str) -> DocumentRecord:
        with self.lock:
            directory = self.directory(doc_id)
            try:
                record = DocumentRecord.model_validate_json(
                    (directory / "document.json").read_text(encoding="utf-8")
                )
            except (OSError, ValueError) as exc:
                raise MissingDocument() from exc
            if record.metadata.expires_at <= self.clock():
                self._remove(directory)
                raise MissingDocument()
            return record

    def search(self, doc_id: str, question: str, k: int = 4) -> list[tuple[Chunk, float]]:
        with self.lock:
            record = self.get(doc_id)
            by_id = {chunk.id: chunk for chunk in record.chunks}
            hits = self.index.search(self.directory(doc_id) / "vectors", question, min(k, len(by_id)))
            return [(by_id[key], distance) for key, distance in hits if key in by_id]

    def delete(self, doc_id: str) -> None:
        with self.lock:
            directory = self.directory(doc_id)
            if not directory.exists():
                return
            # Tombstone before unlinking: failed physical deletion cannot leave readable content.
            (directory / "document.json").unlink(missing_ok=True)
            if not self._remove(directory):
                raise ServiceError(503, "Deletion is pending cleanup. Please retry shortly.")

    def _remove(self, directory: Path) -> bool:
        if directory.parent.resolve() != self.root or directory.is_symlink():
            raise RuntimeError("Refusing deletion outside the document store")
        try:
            if directory.exists():
                shutil.rmtree(directory)
            return True
        except OSError:
            logger.error("document_cleanup_failed")
            return False

    def cleanup(self) -> int:
        removed = 0
        with self.lock:
            for directory in self.root.iterdir():
                if not directory.is_dir() or directory.is_symlink():
                    continue
                try:
                    UUID(directory.name)
                except ValueError:
                    continue
                try:
                    record = DocumentRecord.model_validate_json(
                        (directory / "document.json").read_text(encoding="utf-8")
                    )
                    expired = record.metadata.expires_at <= self.clock()
                except (OSError, ValueError):
                    expired = True
                if expired and self._remove(directory):
                    removed += 1
        return removed
