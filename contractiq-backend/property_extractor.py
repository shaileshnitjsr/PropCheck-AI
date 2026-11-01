"""High-precision extraction layer for Indian real estate property facts."""

import re
import time
from property_schemas import (
    FinancialSummary,
    ImportantDates,
    PartiesInvolved,
    PropertyArea,
    PropertyFactSheet,
    PropertyIdentifier,
)
from rera_verifier import extract_rera_numbers, verify_rera
from schemas import DocumentRecord
from state_detector import detect_state_from_texts


def parse_indian_currency(text: str) -> float | None:
    """Parse Indian currency representations like '50,00,000', '1.25 Crore', '75 Lakhs'."""
    clean = text.replace(",", "").strip()
    
    # Check words like Crore/Lakh
    cr_match = re.search(r"(\d+(?:\.\d+)?)\s*cr(?:ore|ores)?\b", clean, re.I)
    if cr_match:
        return float(cr_match.group(1)) * 10_000_000

    lakh_match = re.search(r"(\d+(?:\.\d+)?)\s*lakh(?:s)?\b", clean, re.I)
    if lakh_match:
        return float(lakh_match.group(1)) * 100_000

    num_match = re.search(r"\b(\d{5,12})\b", clean)
    if num_match:
        return float(num_match.group(1))

    return None


def parse_area_sqft(val_str: str, unit_str: str) -> float | None:
    """Parse area string and convert square meters to square feet if applicable."""
    try:
        val = float(val_str.replace(",", "").strip())
        if re.search(r"m(?:tr|eter)?s?|sq\.?\s*m", unit_str, re.I):
            # 1 sq.m = 10.7639 sq.ft
            return round(val * 10.7639, 2)
        return round(val, 2)
    except (ValueError, TypeError):
        return None


def locate_evidence_in_pages(pages: list[PageText], raw_mention: str | None) -> tuple[int | None, int, int]:
    """Find the page number, page_start, and page_end for an extracted text mention."""
    if not raw_mention or not pages:
        return (None, 0, 0)
    # Direct substring search
    for p in pages:
        if raw_mention in p.text:
            idx = p.text.index(raw_mention)
            return (p.page, idx, idx + len(raw_mention))
    # Case-insensitive substring search
    raw_lower = raw_mention.lower()
    for p in pages:
        p_lower = p.text.lower()
        if raw_lower in p_lower:
            idx = p_lower.index(raw_lower)
            return (p.page, idx, idx + len(raw_mention))
    # Partial word search (first 3 words)
    words = raw_mention.split()[:3]
    if len(words) >= 2:
        needle = " ".join(words).lower()
        for p in pages:
            p_lower = p.text.lower()
            if needle in p_lower:
                idx = p_lower.index(needle)
                return (p.page, idx, idx + len(raw_mention))
    # Fallback to page 1 or None with bounded range
    first_p = pages[0]
    return (first_p.page, 0, min(len(first_p.text), max(1, len(raw_mention))))


def extract_property_facts(record: DocumentRecord, state_override: str | None = None) -> PropertyFactSheet:
    all_chunks = record.chunks
    chunk_texts = [c.text for c in all_chunks]
    full_text = "\n\n".join(chunk_texts[:40])  # Inspect up to first 40 chunks

    # 1. State Detection
    state_res = detect_state_from_texts(chunk_texts)
    effective_state = state_override or state_res.state

    # 2. RERA numbers
    rera_found = extract_rera_numbers(full_text)
    rera_records = []
    for reg_no, excerpt in rera_found:
        rera_rec = verify_rera(reg_no, state=effective_state, evidence=[excerpt])
        rera_records.append(rera_rec)

    # 3. Property Identifiers
    unit_flat = None
    tower_wing = None
    floor_num = None
    survey_no = None
    plot_no = None
    khasra_no = None

    # Flat / Unit No
    # Prefer explicit matches with 'No/Number/#' or following property allotment/description
    # Exclude allottee residence matches like "residing at Flat 301"
    raw_unit = None
    unit_pat = r"(?i)\b(?:Unit|Flat|Apartment|Dwelling\s+Unit)\s*(?:(?:No\.?|Number|#|:|-|/)\s*)*(?:(?:Flat|Apartment|Unit)\s*(?:(?:No\.?|Number|#|:|-)\s*)*)?([0-9]+[A-Za-z0-9\-]*|[A-Za-z]+[-/]?[0-9]+)\b"
    unit_matches = list(re.finditer(unit_pat, full_text))
    for um in unit_matches:
        candidate_val = um.group(1).strip()
        start_idx = max(0, um.start() - 60)
        prefix_context = full_text[start_idx:um.start()].lower()
        if "residing at" in prefix_context or "living at" in prefix_context:
            continue
        unit_flat = candidate_val
        raw_unit = um.group(0).strip()
        break

    # Tower / Wing
    tower_match = re.search(
        r"(?i)\b(?:Tower|Wing|Block|Building)\s+(?:No\.?|Name)?\s*([A-Z0-9\-]+)\b",
        full_text,
    )
    if tower_match:
        tower_wing = tower_match.group(1).strip()

    # Floor
    floor_match = re.search(
        r"(?i)\b(\d{1,2}(?:st|nd|rd|th)?)\s+Floor\b|\bFloor\s+(?:No\.?|#)?\s*(\d{1,2})\b",
        full_text,
    )
    if floor_match:
        floor_num = (floor_match.group(1) or floor_match.group(2)).strip()

    # Survey No
    survey_match = re.search(
        r"(?i)\b(?:Survey|Sy\.?|S\.?No\.?)\s*(?:No\.?|Number)?\s*([0-9]+(?:/[0-9A-Za-z]+)*)\b",
        full_text,
    )
    if survey_match:
        survey_no = survey_match.group(1).strip()

    # Plot No
    plot_match = re.search(
        r"(?i)\b(?:Plot)\s*(?:No\.?|Number)?\s*([0-9]+[A-Za-z\-0-9]*)\b",
        full_text,
    )
    if plot_match:
        plot_no = plot_match.group(1).strip()

    # Khasra No
    khasra_match = re.search(
        r"(?i)\b(?:Khasra)\s*(?:No\.?|Number)?\s*([0-9]+(?:/[0-9]+)*)\b",
        full_text,
    )
    if khasra_match:
        khasra_no = khasra_match.group(1).strip()

    u_page, u_start, u_end = locate_evidence_in_pages(record.pages, raw_unit)
    identifiers = PropertyIdentifier(
        unit_flat_no=unit_flat,
        tower_wing=tower_wing,
        floor=floor_num,
        survey_no=survey_no,
        plot_no=plot_no,
        khasra_no=khasra_no,
        raw_unit_mention=raw_unit,
        page=u_page,
        start=u_start,
        end=u_end,
    )

    # 4. Area Extraction (Carpet vs Built-up vs Super Built-up)
    carpet_sqft = None
    built_up_sqft = None
    super_built_up_sqft = None
    raw_carpet = None
    raw_super = None

    carpet_match = re.search(
        r"(?i)\bcarpet\s+area\b[^\w\n]{0,30}?(?:measuring|admeasuring|of)?\s*(\d+(?:[.,]\d+)?)\s*(sq\.?\s*ft\.?|square\s*feet|sq\.?\s*mtrs?|square\s*met(?:er|re)s|sqm)\b",
        full_text,
    )
    if carpet_match:
        raw_carpet = carpet_match.group(0).strip()
        carpet_sqft = parse_area_sqft(carpet_match.group(1), carpet_match.group(2))

    built_match = re.search(
        r"(?i)\bbuilt[- ]?up\s+area\b[^\w\n]{0,30}?(?:measuring|admeasuring|of)?\s*(\d+(?:[.,]\d+)?)\s*(sq\.?\s*ft\.?|square\s*feet|sq\.?\s*mtrs?|square\s*met(?:er|re)s|sqm)\b",
        full_text,
    )
    if built_match:
        built_up_sqft = parse_area_sqft(built_match.group(1), built_match.group(2))

    super_match = re.search(
        r"(?i)\b(?:super\s+built[- ]?up|saleable)\s+area\b[^\w\n]{0,30}?(?:measuring|admeasuring|of)?\s*(\d+(?:[.,]\d+)?)\s*(sq\.?\s*ft\.?|square\s*feet|sq\.?\s*mtrs?|square\s*met(?:er|re)s|sqm)\b",
        full_text,
    )
    if super_match:
        raw_super = super_match.group(0).strip()
        super_built_up_sqft = parse_area_sqft(super_match.group(1), super_match.group(2))

    c_page, c_start, c_end = locate_evidence_in_pages(record.pages, raw_carpet)
    areas = PropertyArea(
        carpet_area_sqft=carpet_sqft,
        built_up_area_sqft=built_up_sqft,
        super_built_up_area_sqft=super_built_up_sqft,
        raw_carpet_mention=raw_carpet,
        raw_super_built_mention=raw_super,
        carpet_page=c_page,
        carpet_start=c_start,
        carpet_end=c_end,
    )

    # 5. Financials
    agreement_val = None
    booking_amt = None
    raw_val_mention = None

    # Total consideration / sale value
    val_match = re.search(
        r"(?i)\b(?:total\s+(?:sale\s+)?(?:consideration|price|cost)|agreement\s+value|agreed\s+consideration|starting\s+consideration)\b[^\d\n]{0,40}?(?:Rs\.?|INR|\u20B9)?\s*([\d,]+(?:\.\d+)?|\d+(?:\.\d+)?\s*(?:crore|lakh)s?)",
        full_text,
    )
    if val_match:
        raw_val_mention = val_match.group(0).strip()
        agreement_val = parse_indian_currency(val_match.group(1))

    # Booking amount / earnest money / advance
    booking_match = re.search(
        r"(?i)\b(?:booking\s+amount(?:(?:\s+received)?)|earnest\s+money|advance\s+payment)\b[^\d\n]{0,40}?(?:Rs\.?|INR|\u20B9)?\s*([\d,]+(?:\.\d+)?|\d+(?:\.\d+)?\s*(?:crore|lakh)s?)",
        full_text,
    )
    if booking_match:
        booking_amt = parse_indian_currency(booking_match.group(1))

    v_page, v_start, v_end = locate_evidence_in_pages(record.pages, raw_val_mention)
    financials = FinancialSummary(
        agreement_value_inr=agreement_val,
        booking_amount_inr=booking_amt,
        raw_value_mention=raw_val_mention,
        value_page=v_page,
        value_start=v_start,
        value_end=v_end,
    )

    # 6. Dates
    possession_date_str = None
    agreement_date_str = None
    grace_period = None
    raw_poss_mention = None

    poss_match = re.search(
        r"(?i)\b(?:possession|handover|target\s+possession|completion)[^\d\n]{0,60}?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}(?:st|nd|rd|th)?\s+\w+\s+\d{4}|\w+\s+\d{4})\b",
        full_text,
    )
    if poss_match:
        possession_date_str = poss_match.group(1).strip()
        raw_poss_mention = poss_match.group(0).strip()

    grace_match = re.search(r"(?i)\bgrace\s+period\s+of\s+(\d+)\s+months\b", full_text)
    if grace_match:
        grace_period = int(grace_match.group(1))

    ag_date_match = re.search(
        r"(?i)\b(?:executed\s+on|dated|date\s+of\s+agreement)\b[^\w\n]{0,25}?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}(?:st|nd|rd|th)?\s+(?:day\s+of\s+)?\w+[, ]+\d{4})\b",
        full_text,
    )
    if ag_date_match:
        agreement_date_str = ag_date_match.group(1).strip()

    p_page, p_start, p_end = locate_evidence_in_pages(record.pages, raw_poss_mention)
    dates = ImportantDates(
        agreement_date=agreement_date_str,
        possession_date=possession_date_str,
        grace_period_months=grace_period,
        raw_possession_mention=raw_poss_mention,
        possession_page=p_page,
        possession_start=p_start,
        possession_end=p_end,
    )

    # 7. Project Name & Developer
    project_name = None
    proj_match = re.search(
        r"(?i)\b(?:known\s+as|project\s+named|project\s+called|project|complex)\s+[\"']?([A-Z][A-Za-z0-9\s&]{3,35}?(?:Residency|Enclave|Gardens|Heights|Towers|Greens|Palms|Estate|City|Park|Villas|Square|Grande|Pratham))[\"']?\b",
        full_text,
    )
    if proj_match:
        project_name = proj_match.group(1).strip()

    developer_name = None
    dev_match = re.search(
        r"(?i)\b(?:M/s\.?|Messrs\.?)\s+([A-Z][A-Za-z0-9\s&.,]{3,45}?(?:Developers?|Builders?|Realt(?:y|ors?)|Infratech|Projects?|Infra|Constructions?|Promoters?|LLP|Pvt\.?\s*Ltd\.?|Limited))\b",
        full_text,
    )
    if dev_match:
        developer_name = dev_match.group(0).strip()

    # 8. Parties
    parties = PartiesInvolved()
    if developer_name:
        parties.sellers_promoters.append(developer_name)

    allottee_match = re.search(
        r"(?i)\b(?:Allottee|Purchaser|Buyer)\s*(?:hereinafter\s+referred\s+to\s+as)?[^\w\n]{0,20}?(?:Mr\.?|Mrs\.?|Ms\.?|Shri\.?|Smt\.?)\s+([A-Z][A-Za-z\s]{3,35})\b",
        full_text,
    )
    if allottee_match:
        parties.buyers.append(allottee_match.group(1).strip())

    return PropertyFactSheet(
        doc_id=str(record.metadata.doc_id),
        filename=record.metadata.filename,
        detected_state=effective_state,
        state_confidence=state_res.confidence,
        state_evidence=state_res.evidence,
        project_name=project_name,
        developer_name=developer_name,
        rera_records=rera_records,
        identifiers=identifiers,
        areas=areas,
        financials=financials,
        dates=dates,
        parties=parties,
        extracted_at=time.time(),
    )
