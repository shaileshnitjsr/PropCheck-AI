"""Pydantic schemas for PropCheck AI property due diligence and cross-validation."""

from typing import Any
from pydantic import BaseModel, Field
from rera_verifier.base import RERAResult


class PropertyIdentifier(BaseModel):
    unit_flat_no: str | None = None
    tower_wing: str | None = None
    floor: str | None = None
    survey_no: str | None = None
    plot_no: str | None = None
    khasra_no: str | None = None
    village_taluka: str | None = None
    raw_unit_mention: str | None = None
    page: int | None = None
    start: int | None = None
    end: int | None = None


class PropertyArea(BaseModel):
    carpet_area_sqft: float | None = None
    built_up_area_sqft: float | None = None
    super_built_up_area_sqft: float | None = None
    raw_carpet_mention: str | None = None
    raw_super_built_mention: str | None = None
    carpet_page: int | None = None
    carpet_start: int | None = None
    carpet_end: int | None = None


class FinancialSummary(BaseModel):
    agreement_value_inr: float | None = None
    booking_amount_inr: float | None = None
    raw_value_mention: str | None = None
    payment_terms_summary: str | None = None
    value_page: int | None = None
    value_start: int | None = None
    value_end: int | None = None


class ImportantDates(BaseModel):
    agreement_date: str | None = None
    possession_date: str | None = None
    grace_period_months: int | None = None
    delay_penalty_clause: str | None = None
    raw_possession_mention: str | None = None
    possession_page: int | None = None
    possession_start: int | None = None
    possession_end: int | None = None


class PartiesInvolved(BaseModel):
    buyers: list[str] = []
    sellers_promoters: list[str] = []


class PropertyFactSheet(BaseModel):
    doc_id: str
    filename: str
    detected_state: str
    state_confidence: float
    state_evidence: list[str] = []
    project_name: str | None = None
    developer_name: str | None = None
    rera_records: list[RERAResult] = []
    identifiers: PropertyIdentifier = Field(default_factory=PropertyIdentifier)
    areas: PropertyArea = Field(default_factory=PropertyArea)
    financials: FinancialSummary = Field(default_factory=FinancialSummary)
    dates: ImportantDates = Field(default_factory=ImportantDates)
    parties: PartiesInvolved = Field(default_factory=PartiesInvolved)
    encumbrance_status: str | None = None
    extracted_at: float


class CrossDocMismatch(BaseModel):
    finding_id: str
    title: str
    category: str  # 'IDENTIFIER', 'AREA', 'FINANCIAL', 'DATE', 'RERA', 'PARTIES', 'LEGAL'
    severity: str  # 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO', 'PASS'
    status: str    # 'CONFIRMED_MISMATCH', 'POSSIBLE_DISCREPANCY', 'MATCHED', 'MISSING_IN_ONE', 'UNVERIFIED'
    explanation: str
    doc1_id: str
    doc1_name: str
    doc1_value: str | None = None
    doc1_excerpt: str | None = None
    doc1_page: int | None = None
    doc1_start: int | None = None
    doc1_end: int | None = None
    doc2_id: str
    doc2_name: str
    doc2_value: str | None = None
    doc2_excerpt: str | None = None
    doc2_page: int | None = None
    doc2_start: int | None = None
    doc2_end: int | None = None
    actionable_next_step: str


class RERAVerifyRequest(BaseModel):
    reg_no: str
    state: str | None = None
    project_name: str | None = None


class PropertyAnalyzeRequest(BaseModel):
    doc_id: str
    state: str | None = None


class PropertyDueDiligenceRequest(BaseModel):
    doc_ids: list[str]
    state_override: str | None = None


class PropertyDueDiligenceReport(BaseModel):
    property_name: str
    unit_identifier: str
    detected_state: str
    state_confirmed: str
    overall_score: int  # 0 to 100 PropCheck Reliability Index
    risk_category: str  # 'LOW_RISK', 'MODERATE_ATTENTION', 'HIGH_RISK_DISCREPANCY'
    summary: str
    documents_analyzed: list[dict[str, Any]]
    rera_verification: list[RERAResult]
    cross_document_findings: list[CrossDocMismatch]
    extracted_factsheets: list[PropertyFactSheet]
    homebuyer_action_checklist: list[str]
    disclaimer: str
    generated_at: float
