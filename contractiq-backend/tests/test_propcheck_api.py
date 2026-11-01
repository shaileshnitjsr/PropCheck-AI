"""API integration tests for PropCheck AI endpoints."""

import io


def test_propcheck_api_state_and_due_diligence_flow(client):
    # 1. Upload a property deed (txt format)
    content1 = b"Agreement for Sale. Flat No. 402, Tower B, Godrej Green, Pune, Maharashtra 411001.\nCarpet area 1050 sq.ft. Total consideration Rs. 75,00,000.\nRegistered under MahaRERA No. P51800000001."
    res1 = client.post("/upload", files={"file": ("agreement.txt", io.BytesIO(content1), "text/plain")})
    assert res1.status_code == 200
    doc1 = res1.json()
    doc1_id = doc1["doc_id"]

    # 2. Upload a matching allotment letter with carpet area
    content2 = b"Allotment Letter. Flat No. 402, Tower B, Godrej Green, Pune, Maharashtra 411001.\nCarpet area 1050 sq.ft. Consideration Rs. 75,00,000.\nRERA No. P51800000001."
    res2 = client.post("/upload", files={"file": ("allotment.txt", io.BytesIO(content2), "text/plain")})
    assert res2.status_code == 200
    doc2 = res2.json()
    doc2_id = doc2["doc_id"]

    # 3. Test State Detect Endpoint
    state_res = client.post("/property/state-detect", json={"doc_id": doc1_id})
    assert state_res.status_code == 200
    state_data = state_res.json()
    assert state_data["state"] == "Maharashtra"
    assert state_data["confidence"] >= 0.7

    # 4. Test Single Document Factsheet Endpoint
    facts_res = client.post("/property/factsheet", json={"doc_id": doc1_id})
    assert facts_res.status_code == 200
    facts = facts_res.json()
    assert facts["detected_state"] == "Maharashtra"
    assert facts["identifiers"]["unit_flat_no"] == "402"
    assert facts["areas"]["carpet_area_sqft"] == 1050.0
    assert facts["financials"]["agreement_value_inr"] == 7500000.0
    assert len(facts["rera_records"]) >= 1
    assert facts["rera_records"][0]["registration_number"] == "P51800000001"

    # 5. Test Cross-Document Due Diligence Endpoint
    dd_res = client.post("/property/due-diligence", json={"doc_ids": [doc1_id, doc2_id]})
    assert dd_res.status_code == 200
    report = dd_res.json()
    assert report["overall_score"] >= 80
    assert report["detected_state"] == "Maharashtra"
    assert report["risk_category"] == "LOW_RISK"
    assert len(report["documents_analyzed"]) == 2
    assert len(report["homebuyer_action_checklist"]) > 0

    # 6. Test RERA Verify Endpoint standalone
    rera_res = client.post("/property/rera-verify", json={"reg_no": "P51800000001", "state": "Maharashtra"})
    assert rera_res.status_code == 200
    rera_data = rera_res.json()
    assert rera_data["authority"] == "MahaRERA"
    assert rera_data["status"] == "FORMAT_VALID_OFFLINE_VERIFICATION_PENDING"

    # 7. Test PDF Report Generation Endpoint
    pdf_res = client.get(f"/property/report?doc_ids={doc1_id},{doc2_id}&state=Maharashtra")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["Content-Type"] == "application/pdf"
    assert len(pdf_res.content) > 1000
    assert pdf_res.content.startswith(b"%PDF")


def test_propcheck_sample_documents_end_to_end_flow(client):
    from pathlib import Path
    samples_dir = Path(__file__).parent.parent.parent / "sample-documents"
    
    with open(samples_dir / "Sample_Agreement_For_Sale.txt", "rb") as f:
        res1 = client.post("/upload", files={"file": ("Sample_Agreement_For_Sale.txt", f, "text/plain")})
    assert res1.status_code == 200
    doc1_id = res1.json()["doc_id"]

    with open(samples_dir / "Sample_Allotment_Letter.txt", "rb") as f:
        res2 = client.post("/upload", files={"file": ("Sample_Allotment_Letter.txt", f, "text/plain")})
    assert res2.status_code == 200
    doc2_id = res2.json()["doc_id"]

    with open(samples_dir / "Sample_Discrepant_Brochure.txt", "rb") as f:
        res3 = client.post("/upload", files={"file": ("Sample_Discrepant_Brochure.txt", f, "text/plain")})
    assert res3.status_code == 200
    doc3_id = res3.json()["doc_id"]

    # Run Due Diligence across all 3 sample documents
    dd_res = client.post("/property/due-diligence", json={"doc_ids": [doc1_id, doc2_id, doc3_id]})
    assert dd_res.status_code == 200
    report = dd_res.json()

    assert report["detected_state"] == "Uttar Pradesh"
    assert report["overall_score"] < 50
    assert report["risk_category"] == "HIGH_RISK_DISCREPANCY"

    # Verify Financial Mismatch
    fin_finding = next(
        f for f in report["cross_document_findings"]
        if f["category"] == "FINANCIAL" and f["severity"] == "HIGH"
    )
    assert "95,00,000" in fin_finding["doc1_value"] or "9,500,000" in fin_finding["doc1_value"]
    assert "99,00,000" in fin_finding["doc2_value"] or "9,900,000" in fin_finding["doc2_value"]
    assert fin_finding["doc1_excerpt"] is not None
    assert fin_finding["doc2_excerpt"] is not None

    # Verify Possession Date Divergence
    date_finding = next(
        f for f in report["cross_document_findings"]
        if f["category"] == "DATE" and f["severity"] == "HIGH"
    )
    assert "31-12-2025" in date_finding["doc1_value"]
    assert "30-06-2025" in date_finding["doc2_value"]
    assert date_finding["doc1_excerpt"] is not None
    assert date_finding["doc2_excerpt"] is not None

    # Verify RERA verification status
    assert len(report["rera_verification"]) >= 1
    rera_rec = report["rera_verification"][0]
    assert rera_rec["authority"] == "UP-RERA"
    assert rera_rec["status"] == "FORMAT_VALID_OFFLINE_VERIFICATION_PENDING"
    assert "up-rera.in" in rera_rec["official_search_url"]

    # Verify PDF Report Download
    pdf_res = client.get(f"/property/report?doc_ids={doc1_id},{doc2_id},{doc3_id}")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["Content-Type"] == "application/pdf"
    assert len(pdf_res.content) > 5000
    assert pdf_res.content.startswith(b"%PDF")


def test_propcheck_api_error_handling(client):
    # 1. Empty doc_ids to /property/due-diligence
    res_empty = client.post("/property/due-diligence", json={"doc_ids": []})
    assert res_empty.status_code == 422

    # 2. Empty doc_ids to /property/report
    res_empty_rep = client.get("/property/report?doc_ids=")
    assert res_empty_rep.status_code == 422

    # 3. Malformed PDF (does not start with %PDF-)
    fake_pdf = b"NOT_A_REAL_PDF_HEADER"
    res_bad_pdf = client.post("/upload", files={"file": ("fake.pdf", io.BytesIO(fake_pdf), "application/pdf")})
    assert res_bad_pdf.status_code == 422

    # 4. Empty text file
    res_empty_file = client.post("/upload", files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")})
    assert res_empty_file.status_code == 422

    # 5. Unsupported file format returns 415 Unsupported Media Type
    res_bad_ext = client.post("/upload", files={"file": ("malicious.exe", io.BytesIO(b"MZ12345"), "application/octet-stream")})
    assert res_bad_ext.status_code == 415


def test_propcheck_pdf_regression_suite(client):
    from reportlab.pdfgen import canvas
    
    # 1. Real PDF generated with reportlab
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 700, "Genuine Property Allotment Letter. Flat 402 Tower B Noida UP.")
    c.save()
    real_pdf_bytes = buf.getvalue()

    res_real = client.post("/upload", files={"file": ("genuine.pdf", io.BytesIO(real_pdf_bytes), "application/pdf")})
    assert res_real.status_code == 200
    doc_real = res_real.json()
    assert doc_real["has_pdf"] is True
    assert doc_real["chars"] > 0

    # 2. Real PDF with leading UTF-8 BOM and newlines (ISO 32000-1 § 7.5.2)
    bom_pdf_bytes = b"\xef\xbb\xbf\r\n" + real_pdf_bytes
    res_bom = client.post("/upload", files={"file": ("bom_doc.pdf", io.BytesIO(bom_pdf_bytes), "application/pdf")})
    assert res_bom.status_code == 200
    assert res_bom.json()["has_pdf"] is True

    # 3. Valid TXT file
    valid_txt = b"Agreement for Sale. Flat 402 Tower B Noida UP. Carpet area 850 sq.ft."
    res_txt = client.post("/upload", files={"file": ("agreement.txt", io.BytesIO(valid_txt), "text/plain")})
    assert res_txt.status_code == 200
    assert res_txt.json()["has_pdf"] is False

    # 4. Fake PDF containing plain text (renamed .txt to .pdf)
    fake_pdf = b"This is plain text agreement, not a real PDF file."
    res_fake = client.post("/upload", files={"file": ("renamed_text.pdf", io.BytesIO(fake_pdf), "application/pdf")})
    assert res_fake.status_code == 422
    assert "The file does not have a PDF signature." in res_fake.json()["detail"]

    # 5. Empty file
    res_empty = client.post("/upload", files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")})
    assert res_empty.status_code == 422
    assert "The file is empty." in res_empty.json()["detail"]

    # 6. Corrupted PDF (valid signature but corrupted truncated body)
    corrupted_pdf = b"%PDF-1.4\n%corrupted trailer << garbage >> \x00\xff\xfe incomplete EOF"
    res_corrupt = client.post("/upload", files={"file": ("corrupt.pdf", io.BytesIO(corrupted_pdf), "application/pdf")})
    assert res_corrupt.status_code == 422

    # 7. Field name contract: 'file', 'document', or 'files' are accepted
    res_field_doc = client.post("/upload", files={"document": ("genuine_doc.pdf", io.BytesIO(real_pdf_bytes), "application/pdf")})
    assert res_field_doc.status_code == 200
    assert res_field_doc.json()["has_pdf"] is True

    res_field_files = client.post("/upload", files={"files": ("genuine_files.pdf", io.BytesIO(real_pdf_bytes), "application/pdf")})
    assert res_field_files.status_code == 200
    assert res_field_files.json()["has_pdf"] is True

    # 8. Missing file parameter returns 422 with clear message
    res_no_file = client.post("/upload", data={"other_field": "val"})
    assert res_no_file.status_code == 422
    assert "No file provided in request." in res_no_file.json()["detail"]
