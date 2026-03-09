"""
EvidenceIQ — PDF Report Generator
Produces a professional, timestamped evidence report using ReportLab.
"""

import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, HRFlowable, PageBreak
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER


# Brand colors
DARK      = colors.HexColor("#0f172a")
ACCENT    = colors.HexColor("#3b82f6")
LIGHT_BG  = colors.HexColor("#f8fafc")
DANGER    = colors.HexColor("#ef4444")
WARNING   = colors.HexColor("#f59e0b")
SUCCESS   = colors.HexColor("#10b981")
MUTED     = colors.HexColor("#64748b")


def _severity_color(severity: str):
    return {
        "critical": DANGER,
        "high":     WARNING,
        "medium":   colors.HexColor("#f97316"),
        "low":      SUCCESS,
        "none":     MUTED,
    }.get(severity.lower(), MUTED)


def generate_pdf_report(timeline: dict, causal: dict, report: dict, filename: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    story  = []

    # ── Custom Styles ────────────────────────────────────────────
    title_style = ParagraphStyle(
        "EIQTitle",
        parent=styles["Title"],
        fontSize=24,
        textColor=DARK,
        spaceAfter=4,
        fontName="Helvetica-Bold",
    )
    subtitle_style = ParagraphStyle(
        "EIQSubtitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=MUTED,
        spaceAfter=16,
    )
    h1_style = ParagraphStyle(
        "EIQH1",
        parent=styles["Heading1"],
        fontSize=14,
        textColor=ACCENT,
        spaceBefore=16,
        spaceAfter=6,
        fontName="Helvetica-Bold",
        borderPad=4,
    )
    h2_style = ParagraphStyle(
        "EIQH2",
        parent=styles["Heading2"],
        fontSize=11,
        textColor=DARK,
        spaceBefore=10,
        spaceAfter=4,
        fontName="Helvetica-Bold",
    )
    body_style = ParagraphStyle(
        "EIQBody",
        parent=styles["Normal"],
        fontSize=9,
        textColor=DARK,
        leading=14,
        spaceAfter=6,
    )
    label_style = ParagraphStyle(
        "EIQLabel",
        parent=styles["Normal"],
        fontSize=8,
        textColor=MUTED,
        fontName="Helvetica-Bold",
    )

    # ── Header ────────────────────────────────────────────────────
    story.append(Paragraph("⚖ EvidenceIQ", title_style))
    story.append(Paragraph("Forensic Video Analysis Report", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=ACCENT))
    story.append(Spacer(1, 0.1 * inch))

    # Metadata table
    meta = report.get("report_metadata", {})
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    meta_data = [
        ["File", filename or "Unknown"],
        ["Report Type", meta.get("report_type", "incident").replace("_", " ").title()],
        ["Severity", meta.get("severity_classification", "Unknown").title()],
        ["Duration", meta.get("video_duration", "Unknown")],
        ["Events Detected", str(meta.get("total_events_detected", len(timeline.get("events", []))))],
        ["Generated", generated_at],
    ]
    meta_table = Table(
        [[Paragraph(k, label_style), Paragraph(v, body_style)] for k, v in meta_data],
        colWidths=[1.5 * inch, 5.5 * inch],
    )
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT_BG),
        ("GRID",       (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("PADDING",    (0, 0), (-1, -1), 6),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.15 * inch))

    # ── Executive Summary ─────────────────────────────────────────
    story.append(Paragraph("Executive Summary", h1_style))
    story.append(Paragraph(report.get("executive_summary", ""), body_style))

    # ── Chronological Narrative ───────────────────────────────────
    story.append(Paragraph("Incident Narrative", h1_style))
    story.append(Paragraph(report.get("chronological_narrative", ""), body_style))

    # ── Event Timeline ────────────────────────────────────────────
    story.append(Paragraph("Event Timeline", h1_style))
    events = timeline.get("events", [])
    if events:
        table_data = [[
            Paragraph("Time", label_style),
            Paragraph("Description", label_style),
            Paragraph("Severity", label_style),
            Paragraph("Category", label_style),
        ]]
        for event in events:
            sev = event.get("severity", "none")
            sev_color = _severity_color(sev)
            table_data.append([
                Paragraph(event.get("timestamp", ""), body_style),
                Paragraph(event.get("description", ""), body_style),
                Paragraph(sev.upper(), ParagraphStyle("sev", parent=body_style, textColor=sev_color, fontName="Helvetica-Bold")),
                Paragraph(event.get("category", "").replace("_", " ").title(), body_style),
            ])
        t = Table(table_data, colWidths=[0.75*inch, 4.25*inch, 0.9*inch, 1.1*inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("GRID",       (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
            ("PADDING",    (0, 0), (-1, -1), 6),
            ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(t)

    # ── Key Evidence ──────────────────────────────────────────────
    story.append(Paragraph("Key Evidence", h1_style))
    for ev in report.get("key_evidence", []):
        story.append(Paragraph(f"<b>{ev.get('timestamp', '')}:</b> {ev.get('description', '')}", body_style))
        story.append(Paragraph(f"<i>Evidentiary value: {ev.get('evidentiary_value', '')}</i>", label_style))
        story.append(Spacer(1, 0.05 * inch))

    # ── Fault & Liability ─────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Fault & Liability Assessment", h1_style))
    fault = report.get("fault_liability_assessment", {})
    story.append(Paragraph(
        f"<b>Primary Responsible Party:</b> {fault.get('primary_responsible_party', 'Undetermined')}",
        body_style
    ))
    story.append(Paragraph(
        f"<b>Confidence:</b> {fault.get('confidence_level', 'Unknown').title()}",
        body_style
    ))

    dist = fault.get("liability_distribution", [])
    if dist:
        dist_data = [[Paragraph(h, label_style) for h in ["Entity", "Liability %", "Basis"]]]
        for d in dist:
            dist_data.append([
                Paragraph(str(d.get("entity", "")), body_style),
                Paragraph(f"{d.get('percentage', 0)}%", body_style),
                Paragraph(str(d.get("basis", "")), body_style),
            ])
        dt = Table(dist_data, colWidths=[1.5*inch, 1*inch, 4.5*inch])
        dt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("GRID",       (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("PADDING",    (0, 0), (-1, -1), 6),
        ]))
        story.append(Spacer(1, 0.1*inch))
        story.append(dt)

    # ── Recommended Next Steps ────────────────────────────────────
    story.append(Paragraph("Recommended Next Steps", h1_style))
    for step in report.get("recommended_next_steps", []):
        priority = step.get("priority", "").replace("_", " ").upper()
        p_color = {"IMMEDIATE": DANGER, "WITHIN 24H": WARNING}.get(priority, SUCCESS)
        story.append(Paragraph(
            f'<font color="#{p_color.hexval()[2:]}"><b>[{priority}]</b></font> {step.get("action", "")}',
            body_style
        ))
        story.append(Paragraph(f'<i>{step.get("reason", "")}</i>', label_style))
        story.append(Spacer(1, 0.05*inch))

    # ── Disclaimer ────────────────────────────────────────────────
    story.append(Spacer(1, 0.2*inch))
    story.append(HRFlowable(width="100%", thickness=1, color=MUTED))
    story.append(Paragraph(
        "DISCLAIMER: This report is generated by AI and is intended for informational purposes only. "
        "It does not constitute legal advice. Consult qualified legal, insurance, or safety professionals "
        "before taking any action based on this report.",
        ParagraphStyle("disc", parent=body_style, fontSize=8, textColor=MUTED, italic=True)
    ))

    doc.build(story)
    return buffer.getvalue()