"""Unit tests for deterministic cross-document consistency engine."""

from cross_validation import compare_factsheets
from property_schemas import (
    FinancialSummary,
    ImportantDates,
    PartiesInvolved,
    PropertyArea,
    PropertyFactSheet,
    PropertyIdentifier,
)
from rera_verifier.base import RERAResult, RERAStatus


def create_sample_factsheet(
    doc_id: str,
    filename: str,
    unit: str = "402",
    carpet: float | None = 1050.0,
    super_built: float | None = None,
    value: float = 7500000.0,
    possession: str = "31-12-2026",
    rera_num: str = "P51800000001",
    state: str = "Maharashtra",
) -> PropertyFactSheet:
    rera_records = []
    if rera_num:
        rera_records.append(RERAResult(
            registration_number=rera_num,
            state=state,
            authority="MahaRERA",
            status=RERAStatus.FORMAT_VALID_OFFLINE_VERIFICATION_PENDING,
            status_message="Format valid",
            verified_at=1000.0,
            official_portal_url="https://maharera.maharashtra.gov.in",
            official_search_url="https://maharera.maharashtra.gov.in",
        ))

    return PropertyFactSheet(
        doc_id=doc_id,
        filename=filename,
        detected_state=state,
        state_confidence=0.9,
        state_evidence=["Pune, Maharashtra"],
        project_name="Godrej Green",
        developer_name="Godrej Properties Ltd",
        rera_records=rera_records,
        identifiers=PropertyIdentifier(unit_flat_no=unit, tower_wing="Tower B", survey_no="45/2"),
        areas=PropertyArea(carpet_area_sqft=carpet, super_built_up_area_sqft=super_built),
        financials=FinancialSummary(agreement_value_inr=value),
        dates=ImportantDates(possession_date=possession),
        parties=PartiesInvolved(buyers=["Rahul Verma"], sellers_promoters=["Godrej Properties Ltd"]),
        extracted_at=1000.0,
    )


def test_consistent_matching_documents():
    d1 = create_sample_factsheet("doc-1", "Agreement_for_Sale.pdf")
    d2 = create_sample_factsheet("doc-2", "Allotment_Letter.pdf")

    report = compare_factsheets([d1, d2])
    assert report.overall_score >= 80
    assert report.risk_category == "LOW_RISK"
    assert report.detected_state == "Maharashtra"
    assert any(f.status == "MATCHED" for f in report.cross_document_findings)
    assert not any(f.severity == "CRITICAL" for f in report.cross_document_findings)


def test_unit_mismatch_detection():
    d1 = create_sample_factsheet("doc-1", "Agreement_for_Sale.pdf", unit="402")
    d2 = create_sample_factsheet("doc-2", "Allotment_Letter.pdf", unit="502")

    report = compare_factsheets([d1, d2])
    critical_findings = [f for f in report.cross_document_findings if f.severity == "CRITICAL"]
    assert len(critical_findings) >= 1
    unit_finding = next(f for f in critical_findings if f.category == "IDENTIFIER")
    assert unit_finding.status == "CONFIRMED_MISMATCH"
    assert "402" in unit_finding.doc1_value
    assert "502" in unit_finding.doc2_value
    assert report.overall_score < 80


def test_carpet_area_discrepancy():
    d1 = create_sample_factsheet("doc-1", "Sale_Deed.pdf", carpet=1000.0)
    d2 = create_sample_factsheet("doc-2", "Agreement_for_Sale.pdf", carpet=1250.0)

    report = compare_factsheets([d1, d2])
    area_finding = next(f for f in report.cross_document_findings if f.category == "AREA" and f.severity == "CRITICAL")
    assert area_finding.status == "CONFIRMED_MISMATCH"
    assert "1000.0 sq.ft" in area_finding.doc1_value
    assert "1250.0 sq.ft" in area_finding.doc2_value


def test_differing_area_definitions_not_contradiction():
    # Doc 1 has Carpet Area, Doc 2 has Super Built-Up Area.
    # Must NOT generate a CRITICAL contradiction!
    d1 = create_sample_factsheet("doc-1", "Agreement_for_Sale.pdf", carpet=1000.0, super_built=None)
    d2 = create_sample_factsheet("doc-2", "Brochure_Quote.pdf", carpet=None, super_built=1350.0)

    report = compare_factsheets([d1, d2])
    # No CRITICAL area mismatch
    assert not any(f.category == "AREA" and f.severity == "CRITICAL" for f in report.cross_document_findings)
    # But should have INFO note explaining the difference between carpet and super built-up
    info_area = next(f for f in report.cross_document_findings if f.category == "AREA" and f.severity == "INFO")
    assert info_area.status == "POSSIBLE_DISCREPANCY"
    assert "Super Built-Up includes common areas" in info_area.explanation


def test_consideration_amount_mismatch():
    d1 = create_sample_factsheet("doc-1", "Agreement.pdf", value=7500000.0)
    d2 = create_sample_factsheet("doc-2", "Payment_Demand.pdf", value=8200000.0)

    report = compare_factsheets([d1, d2])
    fin_finding = next(f for f in report.cross_document_findings if f.category == "FINANCIAL")
    assert fin_finding.severity == "HIGH"
    assert fin_finding.status == "CONFIRMED_MISMATCH"


def test_missing_rera_flag():
    d1 = create_sample_factsheet("doc-1", "Unregistered_Agreement.pdf", rera_num="")
    report = compare_factsheets([d1])
    rera_warn = next(f for f in report.cross_document_findings if f.category == "RERA")
    assert rera_warn.status == "MISSING_IN_ONE"
    assert rera_warn.severity == "HIGH"
