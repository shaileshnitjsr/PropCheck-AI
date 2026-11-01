"""Paginated PropCheck AI Due Diligence Report generator using ReportLab."""

from datetime import UTC, datetime
from html import escape
from io import BytesIO
from pathlib import Path
from typing import Any

import reportlab
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from property_schemas import PropertyDueDiligenceReport

FONT = "PropCheckVera"
if FONT not in pdfmetrics.getRegisteredFontNames():
    pdfmetrics.registerFont(TTFont(FONT, str(Path(reportlab.__file__).parent / "fonts/Vera.ttf")))


def safe_text(text: str) -> str:
    # Ensure Indian currency and unicode characters are cleanly mapped without broken escapes
    sanitized = text.replace("₹", "INR ").replace("Rs.", "INR ").replace("–", "-").replace("—", "-")
    supported = pdfmetrics.getFont(FONT).face.charToGlyph
    clean = "".join(char if ord(char) in supported or char == "\n" else " " for char in sanitized)
    return escape(clean).replace("\n", "<br/>")


def render_due_diligence_report(report: PropertyDueDiligenceReport) -> bytes:
    output = BytesIO()
    doc = SimpleDocTemplate(
        output, pagesize=A4, rightMargin=44, leftMargin=44, topMargin=50, bottomMargin=50,
        title=f"PropCheck AI - {report.property_name}", author="PropCheck AI",
    )

    body = ParagraphStyle("body", fontName=FONT, fontSize=9, leading=14, spaceAfter=6, textColor=colors.HexColor("#222222"))
    heading = ParagraphStyle("heading", parent=body, fontSize=14, leading=18, spaceBefore=12, spaceAfter=8, keepWithNext=True, textColor=colors.HexColor("#a33324"))
    subheading = ParagraphStyle("subheading", parent=body, fontSize=11, leading=15, spaceBefore=8, spaceAfter=4, keepWithNext=True, textColor=colors.HexColor("#333333"))
    title_style = ParagraphStyle("title", parent=heading, fontSize=24, leading=28, textColor=colors.HexColor("#090909"))
    badge_style = ParagraphStyle("badge", parent=body, fontSize=10, leading=13, fontName=FONT, textColor=colors.whitesmoke)

    story: list[Any] = []

    def p(text: str, style: ParagraphStyle = body) -> None:
        story.append(Paragraph(safe_text(text), style))

    # Header
    p("PROPCHECK AI", title_style)
    p("Property Due-Diligence & Consistency Audit Report", heading)
    p(f"Project / Property: {report.property_name} (Unit: {report.unit_identifier})")
    p(f"Confirmed Jurisdiction: {report.state_confirmed} | Generated: {datetime.fromtimestamp(report.generated_at, UTC):%Y-%m-%d %H:%M UTC}")
    story.append(Spacer(1, 8))

    # Score Box
    score_color = colors.HexColor("#2e7d32") if report.overall_score >= 80 else (colors.HexColor("#ed6c02") if report.overall_score >= 50 else colors.HexColor("#d32f2f"))
    score_table = Table(
        [[
            Paragraph(f"<b>PROPCHECK INDEX: {report.overall_score}/100</b><br/>{report.risk_category.replace('_', ' ')}", badge_style),
            Paragraph(f"<b>Executive Summary:</b> {safe_text(report.summary)}", body),
        ]],
        colWidths=[160, 340],
    )
    score_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), score_color),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#f8f9fa")),
        ("PADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cccccc")),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 12))

    # Documents Examined
    p("1. Documents Examined in Cross-Verification", heading)
    doc_rows = [["#", "Document Filename", "Document Identifier"]]
    for idx, d in enumerate(report.documents_analyzed, 1):
        doc_rows.append([str(idx), d.get("filename", "Unknown"), d.get("doc_id", "")[:12] + "..."])
    t_docs = Table(doc_rows, colWidths=[30, 320, 150])
    t_docs.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ece9e0")),
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_docs)
    story.append(Spacer(1, 10))

    # RERA Verification
    p("2. RERA Official Registration Status", heading)
    if report.rera_verification:
        for r in report.rera_verification:
            p(f"Registration Number: {r.registration_number} ({r.authority})", subheading)
            p(f"Status: {r.status.value.replace('_', ' ')}")
            p(f"Status Details: {r.status_message}")
            p(f"Official Portal Link: {r.official_search_url}")
            p(f"Disclaimer: {r.disclaimer}")
    else:
        p("No RERA registration was cited across the analyzed documents. Section 3 of RERA mandates registration for projects exceeding 500 sq.m or 8 units.")
    story.append(Spacer(1, 10))

    # Cross-Document Consistency Matrix
    p("3. Cross-Document Verification Findings", heading)
    if report.cross_document_findings:
        for idx, f in enumerate(report.cross_document_findings, 1):
            status_tag = f"[{f.severity}] {f.title} ({f.status})"
            p(f"{idx}. {status_tag}", subheading)
            p(f"Explanation: {f.explanation}")
            if f.doc1_name and f.doc1_value:
                p(f"  • {f.doc1_name}: {f.doc1_value}")
            if f.doc1_name and f.doc1_excerpt:
                p(f"    Evidence quote: \"{f.doc1_excerpt}\"")
            if f.doc2_name and f.doc2_value:
                p(f"  • {f.doc2_name}: {f.doc2_value}")
            if f.doc2_name and f.doc2_excerpt:
                p(f"    Evidence quote: \"{f.doc2_excerpt}\"")
            p(f"Actionable Next Step: {f.actionable_next_step}")
    else:
        p("No cross-document discrepancies detected.")
    story.append(Spacer(1, 10))

    # Action Checklist for Homebuyer
    p("4. Recommended Action Checklist for Homebuyer", heading)
    for idx, action in enumerate(report.homebuyer_action_checklist, 1):
        p(f"[  ] {idx}. {action}")
    story.append(Spacer(1, 12))

    # Legal Disclaimer
    p("Important Legal Notice", heading)
    p(report.disclaimer)

    def footer(canvas: Any, document: Any) -> None:
        canvas.saveState()
        canvas.setFont(FONT, 8)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawString(44, 25, "PropCheck AI - Informational Property Due-Diligence Only.")
        canvas.drawRightString(A4[0] - 44, 25, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
