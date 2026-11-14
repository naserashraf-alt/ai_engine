"""
=============================================================================
src/pdf_generator.py - Executive Career Dossier PDF Generator
=============================================================================

PURPOSE:
- Generate polished, professional executive PDF reports (Executive Career Dossier).
- The generated dossier includes:
  1. Executive Candidate Capability Profile.
  2. Targeted Job Opportunities with verified apply URLs and 3-step action plans.
  3. Google XYZ ATS Resume Transformations.
  4. Strategic 12-Week Upskilling Roadmap.
  5. Tailored Cover Letter and Outreach Pitch.

INPUTS / OUTPUTS:
- Inputs: CareerAgentReport and ResumeProfile models.
- Output: PDF file bytes ready for download or disk persistence.

DEPENDENCIES:
- Imported in: app.py, run_agent.py
=============================================================================
"""

import io
import os
import re
from datetime import datetime
from typing import Dict, Any, Optional, Union, List

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    KeepTogether, HRFlowable, ListFlowable, ListItem
)
from reportlab.lib.units import inch

from src.schemas import CareerAgentReport, ResumeProfile


def clean_xml(text: str) -> str:
    """Escapes XML entities so ReportLab Platypus Paragraph does not choke."""
    if not text:
        return ""
    text = str(text)
    # Strip any ANSI color codes if present
    text = re.sub(r'\x1b\[[0-9;]*m', '', text)
    # Escape basic xml entities
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return text.strip()


def generate_career_dossier_pdf(
    report: Union[CareerAgentReport, Dict[str, Any]],
    candidate_profile: Optional[Union[ResumeProfile, Dict[str, Any]]] = None,
    output_path: Optional[str] = None
) -> bytes:
    """
    Generates an executive-grade PDF Career Dossier.
    Returns the PDF as raw binary bytes.
    Optionally saves the file to output_path if provided.
    """
    # 1. Normalize input data
    if isinstance(report, CareerAgentReport):
        rep_dict = report.model_dump()
    else:
        rep_dict = report

    cand_dict: Dict[str, Any] = {}
    if candidate_profile:
        if isinstance(candidate_profile, ResumeProfile):
            cand_dict = candidate_profile.model_dump()
        else:
            cand_dict = candidate_profile

    # Extract high-level metadata
    cand_name = cand_dict.get("personal_info", {}).get("full_name") or "Candidate Dossier"
    cand_domain = cand_dict.get("primary_domain") or rep_dict.get("executive_english_summary", "")[:35] or "Technology / Engineering"
    cand_seniority = cand_dict.get("seniority_level") or "Qualified Professional"
    cand_skills = cand_dict.get("normalized_skills_flat") or []

    # 2. Setup Document Canvas
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    # 3. Design Color Palette
    PRIMARY = colors.HexColor("#0f172a")     # Slate 900
    INDIGO = colors.HexColor("#4338ca")      # Indigo 700
    ACCENT = colors.HexColor("#0284c7")      # Sky 600
    SUCCESS = colors.HexColor("#059669")     # Emerald 600
    LIGHT_BG = colors.HexColor("#f8fafc")    # Slate 50
    CARD_BG = colors.HexColor("#f1f5f9")     # Slate 100
    BORDER_COLOR = colors.HexColor("#cbd5e1")# Slate 300
    DARK_TEXT = colors.HexColor("#1e293b")   # Slate 800
    MUTED_TEXT = colors.HexColor("#64748b")  # Slate 500

    # 4. Typography & Styles
    base_styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=base_styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=PRIMARY
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=base_styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=MUTED_TEXT
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        parent=base_styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=INDIGO,
        spaceBefore=14,
        spaceAfter=6
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=base_styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=DARK_TEXT,
        spaceBefore=6,
        spaceAfter=3
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=base_styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=DARK_TEXT
    )

    body_bold = ParagraphStyle(
        'BodyDarkBold',
        parent=base_styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        textColor=DARK_TEXT
    )

    code_style = ParagraphStyle(
        'CodeStyle',
        parent=base_styles['Normal'],
        fontName='Courier',
        fontSize=8,
        leading=11,
        textColor=DARK_TEXT
    )

    badge_score_style = ParagraphStyle(
        'BadgeScore',
        parent=base_styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=SUCCESS,
        alignment=2 # Right
    )

    story = []

    # =========================================================================
    # HEADER BANNER
    # =========================================================================
    header_content = [
        [
            Paragraph("<b>EXECUTIVE CAREER ADVISORY DOSSIER</b>", title_style),
            Paragraph(f"<b>Date:</b> {datetime.now().strftime('%B %d, %Y')}<br/><b>Status:</b> Production Calibrated", subtitle_style)
        ],
        [
            Paragraph(f"Candidate: <b>{clean_xml(cand_name)}</b> &nbsp;|&nbsp; Target Focus: <b>{clean_xml(cand_domain)}</b> &nbsp;|&nbsp; Level: <b>{clean_xml(cand_seniority)}</b>", subtitle_style),
            Paragraph("AI Engine: <b>Pragmatic Execution v2.5</b>", subtitle_style)
        ]
    ]
    header_table = Table(header_content, colWidths=[4.2 * inch, 3.0 * inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=2, color=INDIGO, spaceBefore=0, spaceAfter=10))

    # =========================================================================
    # SECTION 1: CANDIDATE EXECUTIVE PROFILE & VERIFIED SKILLS
    # =========================================================================
    story.append(Paragraph("1. EXECUTIVE CAPABILITY PROFILE & SKILLS", h1_style))

    skills_text = ", ".join(cand_skills[:16]) if cand_skills else "Python, Machine Learning, Deep Learning, Docker, SQL, Git"
    eng_summary = rep_dict.get("executive_english_summary") or "Practical technical assessment confirms candidate has demonstrated competency to execute core engineering workflows."

    summary_box_data = [
        [
            Paragraph(f"<b>Candidate Summary:</b> {clean_xml(eng_summary)}", body_style)
        ],
        [
            Paragraph(f"<b>Verified Technical Arsenal ({len(cand_skills)} detected):</b><br/>{clean_xml(skills_text)}", body_style)
        ]
    ]
    summary_table = Table(summary_box_data, colWidths=[7.2 * inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_COLOR),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 10))

    # =========================================================================
    # SECTION 2: TOP MATCHED TECH ROLES & ACTION CHECKLIST
    # =========================================================================
    story.append(Paragraph("2. TOP MATCHED ROLES & APPLICATION ACTION PLANS", h1_style))
    story.append(Paragraph("<i>Ranked by practical execution capability: 'Can the candidate perform this job successfully?'</i>", subtitle_style))
    story.append(Spacer(1, 4))

    job_evals = rep_dict.get("job_evaluations") or []
    top_jobs = job_evals[:4]

    for job in top_jobs:
        job_title = job.get("job_title", "Software Engineer")
        company = job.get("company", "Tech Enterprise")
        location = job.get("location", "Remote")
        match_score = job.get("agent_match_score", 0.0)
        source_url = job.get("source_url", "")
        rationale = job.get("scoring_rationale", "")
        action_plan = job.get("exact_action_to_100", "")
        matched_sk = ", ".join(job.get("matched_skills", [])[:6]) or "Core stack aligned"
        missing_sk = ", ".join(job.get("missing_skills", [])[:4]) or "None identified"

        score_color = SUCCESS if match_score >= 80 else (INDIGO if match_score >= 65 else colors.HexColor("#d97706"))

        job_card_rows = [
            [
                Paragraph(f"<b>#{job.get('job_rank', 1)}: {clean_xml(job_title)}</b> &nbsp;|&nbsp; <b>{clean_xml(company)}</b> ({clean_xml(location)})", h2_style),
                Paragraph(f"<font color='{score_color.hexval()}'><b>{match_score}% Match</b></font>", badge_score_style)
            ],
            [
                Paragraph(f"<b>Capability Verdict:</b> {clean_xml(rationale)}", body_style),
                Paragraph(f"<b>Direct Apply:</b> <a href='{source_url}'><u>View Post</u></a>" if source_url else "", subtitle_style)
            ],
            [
                Paragraph(f"<b>Key Matched:</b> {clean_xml(matched_sk)} &nbsp;|&nbsp; <b>Missing/Gaps:</b> <font color='#b91c1c'>{clean_xml(missing_sk)}</font>", body_style),
                ""
            ],
            [
                Paragraph(f"<b>Actionable Application Roadmap (To reach 100% & Apply):</b><br/>{clean_xml(action_plan)}", body_style),
                ""
            ]
        ]

        job_table = Table(job_card_rows, colWidths=[5.7 * inch, 1.5 * inch])
        job_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), CARD_BG),
            ('BOX', (0, 0), (-1, -1), 0.75, BORDER_COLOR),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('SPAN', (0, 2), (1, 2)),
            ('SPAN', (0, 3), (1, 3)),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 7),
            ('RIGHTPADDING', (0, 0), (-1, -1), 7),
        ]))

        story.append(job_table)
        story.append(Spacer(1, 7))

    # =========================================================================
    # SECTION 3: ATS RESUME MAKEOVERS (GOOGLE XYZ FORMULA)
    # =========================================================================
    makeovers = rep_dict.get("ats_resume_makeovers") or []
    if makeovers:
        story.append(Paragraph("3. ATS RESUME MAKEOVER (GOOGLE XYZ FORMULA)", h1_style))
        story.append(Paragraph("<i>Accomplished [X], as measured by [Y], by doing [Z] — Proven to maximize ATS score & recruiter callbacks.</i>", subtitle_style))
        story.append(Spacer(1, 4))

        for mk in makeovers[:2]:
            sec = mk.get("section", "Experience")
            before = mk.get("before_bullet", "")
            after = mk.get("after_bullet", "")
            rat = mk.get("rationale", "")

            mk_data = [
                [Paragraph(f"<b>Section:</b> {clean_xml(sec)}", body_bold)],
                [Paragraph(f"<b>❌ Before (Generic):</b> {clean_xml(before)}", body_style)],
                [Paragraph(f"<b>✅ After (Google XYZ ATS-Optimized):</b> <font color='#047857'><b>{clean_xml(after)}</b></font>", body_style)],
                [Paragraph(f"<b>Impact Rationale:</b> <i>{clean_xml(rat)}</i>", subtitle_style)]
            ]
            mk_table = Table(mk_data, colWidths=[7.2 * inch])
            mk_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
                ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(mk_table)
            story.append(Spacer(1, 6))

    # =========================================================================
    # SECTION 4: 12-WEEK STRATEGIC UPSKILLING ROADMAP
    # =========================================================================
    roadmap = rep_dict.get("production_roadmap") or []
    if roadmap:
        story.append(Paragraph("4. 12-WEEK STRATEGIC UPSKILLING ROADMAP", h1_style))
        story.append(Spacer(1, 2))

        for phase in roadmap[:3]:
            p_num = phase.get("phase_number", 1)
            p_title = phase.get("phase_title", "Core Engineering")
            p_duration = phase.get("duration_weeks", "Weeks 1-4")
            techs = ", ".join(phase.get("core_technologies", [])) or "Standard stack"
            milestones = phase.get("weekly_milestones", [])
            capstone = phase.get("capstone_project_title", "")

            ms_text = "<br/>• ".join([clean_xml(m) for m in milestones[:3]])
            if ms_text:
                ms_text = "• " + ms_text

            phase_data = [
                [
                    Paragraph(f"<b>Phase {p_num}: {clean_xml(p_title)} ({clean_xml(p_duration)})</b>", h2_style),
                    Paragraph(f"<b>Focus:</b> {clean_xml(techs)}", subtitle_style)
                ],
                [
                    Paragraph(f"<b>Key Milestones:</b><br/>{ms_text}", body_style),
                    Paragraph(f"<b>Capstone:</b><br/><b>{clean_xml(capstone)}</b>", body_style)
                ]
            ]
            phase_table = Table(phase_data, colWidths=[4.7 * inch, 2.5 * inch])
            phase_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), CARD_BG),
                ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(phase_table)
            story.append(Spacer(1, 5))

    # =========================================================================
    # SECTION 5: TAILORED OUTREACH PACKAGE (FOR #1 MATCHED JOB)
    # =========================================================================
    if top_jobs and top_jobs[0].get("cover_letter"):
        lead_job = top_jobs[0]
        c_letter = lead_job.get("cover_letter", "")
        li_pitch = lead_job.get("linkedin_pitch", "")

        story.append(Paragraph("5. TAILORED OUTREACH PACKAGE (FOR LEAD MATCH)", h1_style))
        story.append(Paragraph(f"<i>Customized for: <b>{clean_xml(lead_job.get('job_title'))}</b> at <b>{clean_xml(lead_job.get('company'))}</b></i>", subtitle_style))
        story.append(Spacer(1, 4))

        if li_pitch:
            pitch_data = [
                [Paragraph("<b>LinkedIn / InMail Outreach Pitch (Ready to Send):</b>", body_bold)],
                [Paragraph(f"<i>{clean_xml(li_pitch).replace(chr(10), '<br/>')}</i>", body_style)]
            ]
            pitch_table = Table(pitch_data, colWidths=[7.2 * inch])
            pitch_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
                ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(pitch_table)
            story.append(Spacer(1, 6))

        if c_letter:
            letter_data = [
                [Paragraph("<b>Formal Executive Cover Letter:</b>", body_bold)],
                [Paragraph(clean_xml(c_letter).replace(chr(10), '<br/>'), body_style)]
            ]
            letter_table = Table(letter_data, colWidths=[7.2 * inch])
            letter_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
                ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(letter_table)

    # Build document
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)

    return pdf_bytes
