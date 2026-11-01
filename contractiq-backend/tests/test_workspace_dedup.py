"""Tests for workspace deduplication, content hashing idempotency, and cleanup."""
import pytest
from hashlib import sha256
from pathlib import Path

from config import Settings
from product_store import ProductStore
from schemas import Chunk
from storage import DocumentStore


class DummyIndex:
    def add(self, directory: Path, chunks: list[Chunk]) -> None:
        pass

    def search(self, directory: Path, question: str, k: int) -> list[tuple[str, float]]:
        return []


def test_content_hashing_upload_idempotency(tmp_path):
    settings = Settings(data_dir=tmp_path, max_documents=10)
    store = DocumentStore(settings, DummyIndex())
    
    chunks = [Chunk(id="c0", text="Standard residential sale agreement between Promoter and Buyer.", page=1)]
    meta1 = store.create("Agreement.pdf", 60, chunks, pdf=b"%PDF-sample-bytes-1")
    
    # Uploading identical content again
    meta2 = store.create("Agreement.pdf", 60, chunks, pdf=b"%PDF-sample-bytes-1")
    
    # Should return existing document ID without creating a duplicate directory
    assert meta1.doc_id == meta2.doc_id
    dirs = [d for d in (tmp_path / "documents").iterdir() if d.is_dir()]
    assert len(dirs) == 1


def test_distinct_content_creates_distinct_documents(tmp_path):
    settings = Settings(data_dir=tmp_path, max_documents=10)
    store = DocumentStore(settings, DummyIndex())
    
    c1 = [Chunk(id="c0", text="Document 1 content", page=1)]
    meta1 = store.create("Doc1.pdf", 20, c1, pdf=b"%PDF-1")
    
    c2 = [Chunk(id="c0", text="Document 2 content", page=1)]
    meta2 = store.create("Doc2.pdf", 20, c2, pdf=b"%PDF-2")
    
    assert meta1.doc_id != meta2.doc_id
    dirs = [d for d in (tmp_path / "documents").iterdir() if d.is_dir()]
    assert len(dirs) == 2


def test_workspace_listing_prioritizes_pdf_over_txt(tmp_path):
    settings = Settings(data_dir=tmp_path, max_documents=10)
    store = DocumentStore(settings, DummyIndex())
    p_store = ProductStore(store)
    
    c1 = [Chunk(id="c0", text="Same Agreement Content", page=1)]
    # Create TXT version
    store.create("Sample_Agreement.txt", 25, c1)
    # Create PDF version with different hash or explicit PDF
    c2 = [Chunk(id="c0", text="Same Agreement Content Different Hash", page=1)]
    store.create("Sample_Agreement.pdf", 40, c2, pdf=b"%PDF-Agreement")
    
    docs = p_store.documents()
    # Workspace listing should prioritize PDF and hide redundant TXT of same stem
    filenames = [d.filename for d in docs]
    assert "Sample_Agreement.pdf" in filenames
    assert "Sample_Agreement.txt" not in filenames


def test_two_distinct_pasted_texts_get_unique_meaningful_filenames(tmp_path):
    settings = Settings(data_dir=tmp_path, max_documents=10)
    store = DocumentStore(settings, DummyIndex())
    p_store = ProductStore(store)

    paste1 = (
        "RAJASTHAN REAL ESTATE REGULATORY AUTHORITY\n"
        "FORM 'REP-III' REGISTRATION CERTIFICATE OF PROJECT\n"
        "residential project “Aravali Heights” in Jaipur, Rajasthan."
    )
    paste2 = (
        "AGREEMENT FOR SALE\n"
        "Project Name: Green Valley Residency\n"
        "Developer: Sunrise Homes Private Limited"
    )

    c1 = [Chunk(id="c0", text=paste1, page=1)]
    c2 = [Chunk(id="c0", text=paste2, page=1)]

    # Both uploaded as pasted-document.txt
    meta1 = store.create("pasted-document.txt", len(paste1), c1)
    meta2 = store.create("pasted-document.txt", len(paste2), c2)

    assert meta1.filename != meta2.filename
    assert "Aravali_Heights" in meta1.filename
    assert "Green_Valley_Residency" in meta2.filename
    assert meta1.doc_id != meta2.doc_id

    # Persistence check via ProductStore.documents()
    docs = p_store.documents()
    doc_filenames = {d.filename for d in docs}
    assert meta1.filename in doc_filenames
    assert meta2.filename in doc_filenames
    assert "pasted-document.txt" not in doc_filenames


def test_repeated_identical_pasted_titles_disambiguated(tmp_path):
    settings = Settings(data_dir=tmp_path, max_documents=10)
    store = DocumentStore(settings, DummyIndex())

    text1 = "Agreement for Sale for project Palm Greens. Consideration Rs. 50,00,000."
    text2 = "Agreement for Sale for project Palm Greens. Consideration Rs. 95,00,000. Extended clauses."

    c1 = [Chunk(id="c0", text=text1, page=1)]
    c2 = [Chunk(id="c0", text=text2, page=1)]

    meta1 = store.create("pasted-document.txt", len(text1), c1)
    meta2 = store.create("pasted-document.txt", len(text2), c2)

    assert meta1.filename != meta2.filename
    assert "Palm_Greens" in meta1.filename
    assert "Palm_Greens" in meta2.filename
    assert meta1.filename.endswith(".txt")
    assert meta2.filename.endswith(".txt")
    assert meta1.doc_id != meta2.doc_id


def test_repeated_normal_filenames_do_not_overwrite(tmp_path):
    settings = Settings(data_dir=tmp_path, max_documents=10)
    store = DocumentStore(settings, DummyIndex())

    c1 = [Chunk(id="c0", text="Version 1 text", page=1)]
    c2 = [Chunk(id="c0", text="Version 2 completely different content", page=1)]

    meta1 = store.create("Custom_Contract.txt", len("Version 1 text"), c1)
    meta2 = store.create("Custom_Contract.txt", len("Version 2 completely different content"), c2)

    assert meta1.filename == "Custom_Contract.txt"
    assert meta2.filename == "Custom_Contract_2.txt"
    assert meta1.doc_id != meta2.doc_id
    # Both documents exist and are independently readable
    assert store.get(str(meta1.doc_id)).chunks[0].text == "Version 1 text"
    assert store.get(str(meta2.doc_id)).chunks[0].text == "Version 2 completely different content"
