"""Deterministic Cross-Document Consistency Engine for Indian Real Estate."""

import time
from property_schemas import CrossDocMismatch, PropertyDueDiligenceReport, PropertyFactSheet


def normalize_str(s: str | None) -> str:
    if not s:
        return ""
    return "".join(c for c in s.lower() if c.isalnum())


def format_inr(number: float | None) -> str:
    """Format number in Indian numbering system (e.g. 9500000 -> ₹95,00,000)."""
    if number is None:
        return "Not stated"
    s = str(int(round(number)))
    if len(s) <= 3:
        return f"₹{s}"
    last_three = s[-3:]
    remaining = s[:-3]
    chunks = []
    while len(remaining) > 2:
        chunks.append(remaining[-2:])
        remaining = remaining[:-2]
    if remaining:
        chunks.append(remaining)
    chunks.reverse()
    return f"₹{','.join(chunks)},{last_three}"


def compare_factsheets(factsheets: list[PropertyFactSheet], state_override: str | None = None) -> PropertyDueDiligenceReport:
    findings: list[CrossDocMismatch] = []
    
    if not factsheets:
        return PropertyDueDiligenceReport(
            property_name="No documents provided",
            unit_identifier="N/A",
            detected_state="UNKNOWN",
            state_confirmed="UNKNOWN",
            overall_score=0,
            risk_category="HIGH_RISK_DISCREPANCY",
            summary="No documents available for property due-diligence.",
            documents_analyzed=[],
            rera_verification=[],
            cross_document_findings=[],
            extracted_factsheets=[],
            homebuyer_action_checklist=["Upload valid property agreements to begin due diligence."],
            disclaimer="Informational only. Not legal advice.",
            generated_at=time.time(),
        )

    primary = factsheets[0]
    effective_state = state_override or primary.detected_state

    # 1. Compare pairs of documents
    for i in range(len(factsheets)):
        for j in range(i + 1, len(factsheets)):
            d1 = factsheets[i]
            d2 = factsheets[j]

            # --- Check 1: Unit / Flat Number ---
            u1, u2 = d1.identifiers.unit_flat_no, d2.identifiers.unit_flat_no
            if u1 and u2:
                if normalize_str(u1) != normalize_str(u2):
                    findings.append(CrossDocMismatch(
                        finding_id=f"DISC-UNIT-{i}-{j}",
                        title="Unit / Flat Number Mismatch",
                        category="IDENTIFIER",
                        severity="CRITICAL",
                        status="CONFIRMED_MISMATCH",
                        explanation=f"Conflicting unit identifiers: '{u1}' in {d1.filename} versus '{u2}' in {d2.filename}.",
                        doc1_id=d1.doc_id, doc1_name=d1.filename, doc1_value=u1,
                        doc1_excerpt=d1.identifiers.raw_unit_mention,
                        doc1_page=d1.identifiers.page, doc1_start=d1.identifiers.start, doc1_end=d1.identifiers.end,
                        doc2_id=d2.doc_id, doc2_name=d2.filename, doc2_value=u2,
                        doc2_excerpt=d2.identifiers.raw_unit_mention,
                        doc2_page=d2.identifiers.page, doc2_start=d2.identifiers.start, doc2_end=d2.identifiers.end,
                        actionable_next_step="Immediately ask developer and legal counsel to clarify if these agreements pertain to different units or if an amendment deed is needed.",
                    ))
                else:
                    findings.append(CrossDocMismatch(
                        finding_id=f"PASS-UNIT-{i}-{j}",
                        title="Unit / Flat Number Verified Consistent",
                        category="IDENTIFIER",
                        severity="PASS",
                        status="MATCHED",
                        explanation=f"Both documents reference matching unit '{u1}'.",
                        doc1_id=d1.doc_id, doc1_name=d1.filename, doc1_value=u1,
                        doc1_excerpt=d1.identifiers.raw_unit_mention,
                        doc1_page=d1.identifiers.page, doc1_start=d1.identifiers.start, doc1_end=d1.identifiers.end,
                        doc2_id=d2.doc_id, doc2_name=d2.filename, doc2_value=u2,
                        doc2_excerpt=d2.identifiers.raw_unit_mention,
                        doc2_page=d2.identifiers.page, doc2_start=d2.identifiers.start, doc2_end=d2.identifiers.end,
                        actionable_next_step="Keep records aligned across all conveyance schedules.",
                    ))

            # --- Check 2: Survey / Plot / Khasra Number ---
            s1, s2 = d1.identifiers.survey_no, d2.identifiers.survey_no
            if s1 and s2:
                if normalize_str(s1) != normalize_str(s2):
                    findings.append(CrossDocMismatch(
                        finding_id=f"DISC-SURVEY-{i}-{j}",
                        title="Land Survey Number Mismatch",
                        category="IDENTIFIER",
                        severity="CRITICAL",
                        status="CONFIRMED_MISMATCH",
                        explanation=f"Land survey parcel discrepancy: '{s1}' in {d1.filename} vs '{s2}' in {d2.filename}.",
                        doc1_id=d1.doc_id, doc1_name=d1.filename, doc1_value=s1,
                        doc2_id=d2.doc_id, doc2_name=d2.filename, doc2_value=s2,
                        actionable_next_step="Have a property lawyer cross-verify the mother deed and revenue records (7/12 extract or RTC / Patta) for parcel boundaries.",
                    ))

            # --- Check 3: Carpet Area vs Carpet Area ---
            c1, c2 = d1.areas.carpet_area_sqft, d2.areas.carpet_area_sqft
            if c1 and c2:
                diff_pct = abs(c1 - c2) / max(c1, c2) * 100
                if diff_pct > 2.0:
                    findings.append(CrossDocMismatch(
                        finding_id=f"DISC-AREA-CARPET-{i}-{j}",
                        title="Carpet Area Discrepancy",
                        category="AREA",
                        severity="CRITICAL",
                        status="CONFIRMED_MISMATCH",
                        explanation=f"Carpet area differs by {diff_pct:.1f}%: {c1} sq.ft in {d1.filename} vs {c2} sq.ft in {d2.filename}.",
                        doc1_id=d1.doc_id, doc1_name=d1.filename, doc1_value=f"{c1} sq.ft",
                        doc1_excerpt=d1.areas.raw_carpet_mention,
                        doc1_page=d1.areas.carpet_page, doc1_start=d1.areas.carpet_start, doc1_end=d1.areas.carpet_end,
                        doc2_id=d2.doc_id, doc2_name=d2.filename, doc2_value=f"{c2} sq.ft",
                        doc2_excerpt=d2.areas.raw_carpet_mention,
                        doc2_page=d2.areas.carpet_page, doc2_start=d2.areas.carpet_start, doc2_end=d2.areas.carpet_end,
                        actionable_next_step="Under RERA, real estate sales must be strictly based on Carpet Area. Seek written clarification and survey verification from the promoter.",
                    ))
                else:
                    findings.append(CrossDocMismatch(
                        finding_id=f"PASS-AREA-CARPET-{i}-{j}",
                        title="Carpet Area Consistent",
                        category="AREA",
                        severity="PASS",
                        status="MATCHED",
                        explanation=f"Carpet area is consistent ({c1} sq.ft vs {c2} sq.ft, within 2% margin).",
                        doc1_id=d1.doc_id, doc1_name=d1.filename, doc1_value=f"{c1} sq.ft",
                        doc1_excerpt=d1.areas.raw_carpet_mention,
                        doc1_page=d1.areas.carpet_page, doc1_start=d1.areas.carpet_start, doc1_end=d1.areas.carpet_end,
                        doc2_id=d2.doc_id, doc2_name=d2.filename, doc2_value=f"{c2} sq.ft",
                        doc2_excerpt=d2.areas.raw_carpet_mention,
                        doc2_page=d2.areas.carpet_page, doc2_start=d2.areas.carpet_start, doc2_end=d2.areas.carpet_end,
                        actionable_next_step="Retain approved sanctioned architectural plan.",
                    ))
            elif (c1 and not c2 and d2.areas.super_built_up_area_sqft) or (c2 and not c1 and d1.areas.super_built_up_area_sqft):
                # Different area definitions: do NOT treat as direct contradiction!
                carpet_val = c1 if c1 else c2
                super_val = d2.areas.super_built_up_area_sqft if c1 else d1.areas.super_built_up_area_sqft
                findings.append(CrossDocMismatch(
                    finding_id=f"INFO-AREA-DEF-{i}-{j}",
                    title="Different Area Definitions Used (Carpet vs Super Built-Up)",
                    category="AREA",
                    severity="INFO",
                    status="POSSIBLE_DISCREPANCY",
                    explanation=(
                        f"One document quotes Carpet Area ({carpet_val} sq.ft), while another quotes Super Built-Up Area ({super_val} sq.ft). "
                        "These measure different dimensions (Super Built-Up includes common areas). This is not an explicit contradiction, but verify the loading percentage."
                    ),
                    doc1_id=d1.doc_id, doc1_name=d1.filename, doc1_value=str(c1 or d1.areas.super_built_up_area_sqft),
                    doc1_excerpt=d1.areas.raw_carpet_mention or d1.areas.raw_super_built_mention,
                    doc1_page=d1.areas.carpet_page, doc1_start=d1.areas.carpet_start, doc1_end=d1.areas.carpet_end,
                    doc2_id=d2.doc_id, doc2_name=d2.filename, doc2_value=str(c2 or d2.areas.super_built_up_area_sqft),
                    doc2_excerpt=d2.areas.raw_carpet_mention or d2.areas.raw_super_built_mention,
                    doc2_page=d2.areas.carpet_page, doc2_start=d2.areas.carpet_start, doc2_end=d2.areas.carpet_end,
                    actionable_next_step="Request the promoter to state the exact RERA Carpet Area on all official communications.",
                ))

            # --- Check 4: Total Consideration / Value ---
            v1, v2 = d1.financials.agreement_value_inr, d2.financials.agreement_value_inr
            if v1 and v2:
                if abs(v1 - v2) > 1000.0:
                    findings.append(CrossDocMismatch(
                        finding_id=f"DISC-FIN-VALUE-{i}-{j}",
                        title="Agreement Consideration Amount Mismatch",
                        category="FINANCIAL",
                        severity="HIGH",
                        status="CONFIRMED_MISMATCH",
                        explanation=f"Consideration differs: {format_inr(v1)} in {d1.filename} vs {format_inr(v2)} in {d2.filename}.",
                        doc1_id=d1.doc_id, doc1_name=d1.filename, doc1_value=format_inr(v1),
                        doc1_excerpt=d1.financials.raw_value_mention,
                        doc1_page=d1.financials.value_page, doc1_start=d1.financials.value_start, doc1_end=d1.financials.value_end,
                        doc2_id=d2.doc_id, doc2_name=d2.filename, doc2_value=format_inr(v2),
                        doc2_excerpt=d2.financials.raw_value_mention,
                        doc2_page=d2.financials.value_page, doc2_start=d2.financials.value_start, doc2_end=d2.financials.value_end,
                        actionable_next_step="Reconcile payment schedules, receipt acknowledgements, and GST/TDS components with the accounts department.",
                    ))

            # --- Check 5: Possession Dates ---
            p1, p2 = d1.dates.possession_date, d2.dates.possession_date
            if p1 and p2:
                if normalize_str(p1) != normalize_str(p2):
                    findings.append(CrossDocMismatch(
                        finding_id=f"DISC-DATE-POSS-{i}-{j}",
                        title="Possession Date Divergence",
                        category="DATE",
                        severity="HIGH",
                        status="POSSIBLE_DISCREPANCY",
                        explanation=f"Possession dates diverge: '{p1}' in {d1.filename} vs '{p2}' in {d2.filename}.",
                        doc1_id=d1.doc_id, doc1_name=d1.filename, doc1_value=p1,
                        doc1_excerpt=d1.dates.raw_possession_mention,
                        doc1_page=d1.dates.possession_page, doc1_start=d1.dates.possession_start, doc1_end=d1.dates.possession_end,
                        doc2_id=d2.doc_id, doc2_name=d2.filename, doc2_value=p2,
                        doc2_excerpt=d2.dates.raw_possession_mention,
                        doc2_page=d2.dates.possession_page, doc2_start=d2.dates.possession_start, doc2_end=d2.dates.possession_end,
                        actionable_next_step="Check if an extension clause or RERA revised project timeline was officially approved.",
                    ))

            # --- Check 6: RERA Number Consistency ---
            r1 = [r.registration_number for r in d1.rera_records]
            r2 = [r.registration_number for r in d2.rera_records]
            if r1 and r2:
                norm_r1 = {normalize_str(x) for x in r1}
                norm_r2 = {normalize_str(x) for x in r2}
                if not (norm_r1 & norm_r2):
                    findings.append(CrossDocMismatch(
                        finding_id=f"DISC-RERA-{i}-{j}",
                        title="Conflicting RERA Registration Numbers",
                        category="RERA",
                        severity="CRITICAL",
                        status="CONFIRMED_MISMATCH",
                        explanation=f"Documents cite differing RERA registrations: {r1} vs {r2}.",
                        doc1_id=d1.doc_id, doc1_name=d1.filename, doc1_value=", ".join(r1),
                        doc2_id=d2.doc_id, doc2_name=d2.filename, doc2_value=", ".join(r2),
                        actionable_next_step="Check whether this project is registered under separate phases or if the registration details were misstated.",
                    ))

    # Single-document checks (e.g. missing RERA, missing carpet area)
    for idx, d in enumerate(factsheets):
        if not d.rera_records:
            findings.append(CrossDocMismatch(
                finding_id=f"WARN-RERA-MISSING-{idx}",
                title=f"No RERA Registration Cited in {d.filename}",
                category="RERA",
                severity="HIGH",
                status="MISSING_IN_ONE",
                explanation=f"Document '{d.filename}' does not explicitly mention a RERA registration number.",
                doc1_id=d.doc_id, doc1_name=d.filename, doc1_value=None,
                doc2_id="", doc2_name="", doc2_value=None,
                actionable_next_step="Under Section 3 of RERA, residential projects over 500 sq.m or 8 apartments must be registered. Verify RERA registration status.",
            ))
        if not d.areas.carpet_area_sqft and d.areas.super_built_up_area_sqft:
            findings.append(CrossDocMismatch(
                finding_id=f"WARN-CARPET-MISSING-{idx}",
                title=f"Only Super Built-Up Area Quoted in {d.filename}",
                category="AREA",
                severity="MEDIUM",
                status="MISSING_IN_ONE",
                explanation=f"Document '{d.filename}' quotes Super Built-Up Area without specifying Carpet Area.",
                doc1_id=d.doc_id, doc1_name=d.filename, doc1_value=f"{d.areas.super_built_up_area_sqft} sq.ft",
                doc2_id="", doc2_name="", doc2_value=None,
                actionable_next_step="Insist on a specific Carpet Area clause as mandated by RERA.",
            ))

    if len(factsheets) == 1:
        single = factsheets[0]
        if single.areas.carpet_area_sqft:
            findings.append(CrossDocMismatch(
                finding_id="SINGLE-CARPET-EXTRACTED",
                title="RERA Carpet Area Found",
                category="AREA",
                severity="PASS",
                status="MATCHED",
                explanation=f"Carpet Area of {single.areas.carpet_area_sqft} sq.ft extracted from {single.filename}.",
                doc1_id=single.doc_id, doc1_name=single.filename, doc1_value=f"{single.areas.carpet_area_sqft} sq.ft",
                doc1_excerpt=single.areas.raw_carpet_mention,
                doc1_page=single.areas.carpet_page, doc1_start=single.areas.carpet_start, doc1_end=single.areas.carpet_end,
                doc2_id="", doc2_name="", doc2_value=None,
                actionable_next_step="Upload an Allotment Letter or Brochure to cross-verify area consistency.",
            ))
        if single.identifiers.unit_flat_no:
            findings.append(CrossDocMismatch(
                finding_id="SINGLE-UNIT-EXTRACTED",
                title=f"Unit Identifier Identified: {single.identifiers.unit_flat_no}",
                category="IDENTIFIER",
                severity="PASS",
                status="MATCHED",
                explanation=f"Unit / Flat {single.identifiers.unit_flat_no} detected in {single.filename}.",
                doc1_id=single.doc_id, doc1_name=single.filename, doc1_value=single.identifiers.unit_flat_no,
                doc1_excerpt=single.identifiers.raw_unit_mention,
                doc1_page=single.identifiers.page, doc1_start=single.identifiers.start, doc1_end=single.identifiers.end,
                doc2_id="", doc2_name="", doc2_value=None,
                actionable_next_step="Cross-check against allotment letter and builder demand letters.",
            ))

    # Deduplicate all collected RERA records across documents
    all_rera = []
    seen_rera = set()
    for d in factsheets:
        for r in d.rera_records:
            if r.registration_number not in seen_rera:
                seen_rera.add(r.registration_number)
                all_rera.append(r)

    # Compute PropCheck Score (0 to 100)
    score = 100
    for f in findings:
        if f.severity == "CRITICAL":
            score -= 25
        elif f.severity == "HIGH":
            score -= 15
        elif f.severity == "MEDIUM":
            score -= 5

    # If no RERA found across ANY document, apply penalty
    if not all_rera:
        score -= 15

    score = max(0, min(100, score))

    if score >= 80:
        risk_category = "LOW_RISK"
        summary = "Property documentation shows strong consistency across identifiers, areas, and key financial terms."
    elif score >= 50:
        risk_category = "MODERATE_ATTENTION"
        summary = "Several discrepancies or missing clauses were detected that require clarification from the promoter or legal counsel."
    else:
        risk_category = "HIGH_RISK_DISCREPANCY"
        summary = "Critical mismatches detected in property identifiers, carpet area, or registration terms. Require rigorous legal diligence before financial commitment."

    # Action checklist for the homebuyer
    checklist = [
        "Obtain a certified Search Report & Non-Encumbrance Certificate for 30 years from the Sub-Registrar's Office.",
        "Verify RERA registration number and quarterly project progress reports on the official State RERA portal.",
        "Ensure payment milestones strictly follow RERA slab schedules (maximum 10% before registered Agreement for Sale).",
        "Inspect original Sanctioned Building Plan and Commencement Certificate (CC) issued by local municipal authority.",
    ]
    if any(f.category == "AREA" and f.severity in ("CRITICAL", "HIGH") for f in findings):
        checklist.insert(0, "DEMAND written RERA Carpet Area breakdown from builder to resolve identified area discrepancy.")
    if any(f.category == "IDENTIFIER" and f.severity == "CRITICAL" for f in findings):
        checklist.insert(0, "CLARIFY flat / survey number discrepancy with builder legal department before signing.")

    # Property and unit summary
    prop_name = primary.project_name or (f"Property in {effective_state}" if effective_state != "UNKNOWN" else "Property Review")
    unit_id = primary.identifiers.unit_flat_no or primary.identifiers.plot_no or "Unspecified Unit"

    return PropertyDueDiligenceReport(
        property_name=prop_name,
        unit_identifier=unit_id,
        detected_state=effective_state,
        state_confirmed=effective_state,
        overall_score=score,
        risk_category=risk_category,
        summary=summary,
        documents_analyzed=[{"doc_id": d.doc_id, "filename": d.filename} for d in factsheets],
        rera_verification=all_rera,
        cross_document_findings=findings,
        extracted_factsheets=factsheets,
        homebuyer_action_checklist=checklist,
        disclaimer="PropCheck AI is an automated due-diligence analysis tool. Findings are informational and do not constitute a legal title opinion or conveyancing certificate.",
        generated_at=time.time(),
    )
