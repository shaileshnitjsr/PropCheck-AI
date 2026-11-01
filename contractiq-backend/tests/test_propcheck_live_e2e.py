import os
import time
import pytest
import requests

BASE_URL = "http://127.0.0.1:8000"

def _is_live_server_up() -> bool:
    try:
        return requests.get(f"{BASE_URL}/health", timeout=0.5).status_code == 200
    except Exception:
        return False

pytestmark = pytest.mark.skipif(not _is_live_server_up(), reason="Live server not running at http://127.0.0.1:8000")

def test_propcheck_end_to_end_flow():
    # 1. Health check
    res = requests.get(f"{BASE_URL}/health", timeout=5)
    assert res.status_code == 200, f"Backend health check failed: {res.text}"

    # 2. Upload the 3 sample files
    sample_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "sample-documents"))
    if not os.path.exists(sample_dir):
        sample_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sample-documents"))
    files_to_upload = [
        "Sample_Agreement_For_Sale.pdf",
        "Sample_Allotment_Letter.pdf",
        "Sample_Discrepant_Brochure.pdf",
    ]

    uploaded_doc_ids = []
    for fname in files_to_upload:
        fpath = os.path.join(sample_dir, fname)
        assert os.path.exists(fpath), f"Sample file not found: {fpath}"
        with open(fpath, "rb") as f:
            upload_res = requests.post(
                f"{BASE_URL}/upload",
                files={"file": (fname, f, "application/pdf")},
                timeout=10,
            )
        assert upload_res.status_code in (200, 202), f"Upload failed for {fname}: {upload_res.status_code} {upload_res.text}"
        data = upload_res.json()
        doc_id = data.get("doc_id")
        assert doc_id, f"No doc_id returned for {fname}"
        uploaded_doc_ids.append((fname, doc_id))
        print(f"Uploaded {fname} -> {doc_id}")

    # If 202, wait for documents to be fully processed/ready
    for fname, doc_id in uploaded_doc_ids:
        ready = False
        for _ in range(10):
            status_res = requests.get(f"{BASE_URL}/document/{doc_id}", timeout=5)
            if status_res.status_code == 200:
                ready = True
                break
            time.sleep(0.5)
        assert ready, f"Document {fname} ({doc_id}) was not ready in time"

    # 3. Call Due-Diligence analysis endpoint
    doc_ids_only = [did for _, did in uploaded_doc_ids]
    dd_res = requests.post(
        f"{BASE_URL}/property/due-diligence",
        json={"doc_ids": doc_ids_only},
        timeout=15,
    )
    assert dd_res.status_code == 200, f"Due-diligence failed: {dd_res.text}"
    report = dd_res.json()

    print(f"Report Property Name: {report.get('property_name')}")
    print(f"Report Unit: {report.get('unit_identifier')}")
    print(f"Report State: {report.get('state_confirmed')}")
    print(f"PropCheck Score: {report.get('overall_score')}/100")
    print(f"Risk Category: {report.get('risk_category')}")

    assert report.get("property_name") in ("Palm Greens", "Godrej Woods")
    assert "402" in (report.get("unit_identifier") or "")
    assert "Uttar Pradesh" in (report.get("state_confirmed") or "")

    # 4. Verify RERA verification status
    rera_list = report.get("rera_verification", [])
    assert len(rera_list) > 0, "No RERA records detected"
    rera_item = rera_list[0]
    print(f"RERA Registration: {rera_item.get('registration_number')}, Status: {rera_item.get('status')}")
    assert rera_item.get("status") == "FORMAT_VALID_OFFLINE_VERIFICATION_PENDING"
    assert "UPRERAPRJ" in rera_item.get("registration_number")
    assert "up-rera.in" in rera_item.get("official_search_url")

    # 5. Verify Cross-Document Discrepancies
    findings = report.get("cross_document_findings", [])
    assert len(findings) > 0, "No cross-document findings generated"

    # Find the ₹95L vs ₹99L mismatch
    fin_mismatch = next((f for f in findings if "Consideration Amount Mismatch" in f.get("title", "")), None)
    assert fin_mismatch is not None, "Financial consideration mismatch finding not found"
    print(f"Found financial mismatch: {fin_mismatch['explanation']}")
    assert "₹95,00,000" in fin_mismatch.get("doc1_value", "") or "9500000" in fin_mismatch.get("doc1_value", "") or "₹95,00,000" in fin_mismatch.get("explanation", "")
    assert "₹99,00,000" in fin_mismatch.get("doc2_value", "") or "9900000" in fin_mismatch.get("doc2_value", "") or "₹99,00,000" in fin_mismatch.get("explanation", "")
    # Check offsets exist and are valid numbers
    assert fin_mismatch.get("doc1_start") is not None
    assert fin_mismatch.get("doc1_end") is not None
    assert fin_mismatch.get("doc2_start") is not None
    assert fin_mismatch.get("doc2_end") is not None
    print(f"Doc1 Offsets: page={fin_mismatch.get('doc1_page')}, start={fin_mismatch.get('doc1_start')}, end={fin_mismatch.get('doc1_end')}")
    print(f"Doc2 Offsets: page={fin_mismatch.get('doc2_page')}, start={fin_mismatch.get('doc2_start')}, end={fin_mismatch.get('doc2_end')}")

    # Verify inspecting source for Doc1 returns exact text
    src1_res = requests.get(f"{BASE_URL}/document/{fin_mismatch['doc1_id']}/source", timeout=5)
    assert src1_res.status_code == 200
    src1 = src1_res.json()
    page1 = next(p for p in src1["pages"] if p["page"] == (fin_mismatch.get("doc1_page") or 1))
    extracted_slice1 = page1["text"][fin_mismatch["doc1_start"]:fin_mismatch["doc1_end"]]
    print(f"Doc1 Extracted Slice: {extracted_slice1!r}")
    assert "95,00,000" in extracted_slice1 or "95" in extracted_slice1

    # Verify inspecting source for Doc2 returns exact text
    src2_res = requests.get(f"{BASE_URL}/document/{fin_mismatch['doc2_id']}/source", timeout=5)
    assert src2_res.status_code == 200
    src2 = src2_res.json()
    page2 = next(p for p in src2["pages"] if p["page"] == (fin_mismatch.get("doc2_page") or 1))
    extracted_slice2 = page2["text"][fin_mismatch["doc2_start"]:fin_mismatch["doc2_end"]]
    print(f"Doc2 Extracted Slice: {extracted_slice2!r}")
    assert "99,00,000" in extracted_slice2 or "99" in extracted_slice2

    # Find the Possession Date Divergence
    date_mismatch = next((f for f in findings if "Possession Date Divergence" in f.get("title", "")), None)
    assert date_mismatch is not None, "Possession date divergence finding not found"
    print(f"Found possession date mismatch: {date_mismatch['explanation']}")
    assert date_mismatch.get("doc1_start") is not None
    assert date_mismatch.get("doc2_start") is not None

    # Find the Carpet Area Consistent check
    area_match = next((f for f in findings if "Carpet Area Consistent" in f.get("title", "")), None)
    assert area_match is not None, "Carpet area consistency finding not found"
    print(f"Carpet Area Finding: {area_match['explanation']}")
    assert "850 sq.ft" in area_match.get("doc1_value", "") or "850" in area_match.get("doc1_value", "")

    # 6. Verify PDF Report Generation
    pdf_res = requests.get(
        f"{BASE_URL}/property/report?doc_ids={','.join(doc_ids_only)}",
        timeout=15,
    )
    assert pdf_res.status_code == 200, f"PDF report generation failed: {pdf_res.status_code}"
    assert pdf_res.headers.get("content-type") == "application/pdf"
    assert pdf_res.content.startswith(b"%PDF-"), "Generated report does not have valid %PDF- signature"
    print(f"PDF Report generated successfully! Size: {len(pdf_res.content)} bytes")

    print("\nALL END-TO-END PROPCHECK AI VERIFICATIONS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_propcheck_end_to_end_flow()
