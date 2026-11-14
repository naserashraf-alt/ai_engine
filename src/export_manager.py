"""
=============================================================================
src/export_manager.py - Multi-Format Career Dossier Exporter
=============================================================================

Purpose:
- Serializes career agent reports into executive document formats:
  1. PDF: Executive dossier with styled tables via ReportLab Platypus.
  2. Word (DOCX): Fully editable, professional corporate document via python-docx.
  3. Markdown (MD): Clean GitHub Flavored Markdown for developer documentation.

Dependencies:
- Calls: src/schemas.py, src/pdf_generator.py
- Imported in: app.py, run_agent.py
=============================================================================
"""

import io
from typing import Optional
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

from src.schemas import CareerAgentReport, ResumeProfile
from src.pdf_generator import generate_career_dossier_pdf


class ExportManager:
    """Handles multi-format document serialization (PDF, DOCX, Markdown)."""

    @staticmethod
    def to_pdf(report: CareerAgentReport, profile: Optional[ResumeProfile] = None) -> bytes:
        """Generates Executive Dossier PDF bytes."""
        return generate_career_dossier_pdf(report, candidate_profile=profile)

    @staticmethod
    def to_markdown(report: CareerAgentReport, profile: Optional[ResumeProfile] = None) -> str:
        """Generates comprehensive GitHub Flavored Markdown career dossier."""
        cand_name = report.candidate_name or "Candidate"
        domain = report.target_domain or "Technology"
        seniority = report.seniority_assessment or "Mid-Level"

        md = []
        md.append(f"# 🚀 Executive Career Dossier: {cand_name}")
        md.append(f"**Target Domain:** {domain} | **Seniority Level:** {seniority}\n")
        md.append("---\n")

        # Executive Summary
        md.append("## 🌟 Strategic Executive Assessment")
        if getattr(report, "executive_english_summary", ""):
            md.append(f"{report.executive_english_summary}\n")
        if getattr(report, "executive_arabic_summary", ""):
            md.append(f"### 🌍 Executive Advisory Insights")
            md.append(f"> {report.executive_arabic_summary}\n")

        # Top Matched Opportunities
        md.append(f"## 🏆 Top Matched Opportunities ({len(report.job_evaluations)} Target Roles)\n")
        for ev in report.job_evaluations:
            md.append(f"### #{ev.job_rank} | {ev.job_title} — **{ev.agent_match_score}% Match**")
            md.append(f"🏢 **Company:** {ev.company} | 📍 **Location:** {ev.location} | [🔗 Apply Link]({ev.source_url})\n")
            md.append(f"- **Practical Capability Rationale:** {ev.scoring_rationale}")
            md.append(f"- **Key Competitive Advantage:** {ev.why_matched}")
            md.append(f"- **Actionable Steps to Apply:** {ev.exact_action_to_100}")
            if ev.matched_skills:
                md.append(f"- **Matched Stack:** `{', '.join(ev.matched_skills)}`")
            if ev.missing_skills:
                md.append(f"- **Technical Gaps:** `{', '.join(ev.missing_skills)}`")
            if getattr(ev, "cover_letter", ""):
                md.append(f"\n<details><summary>📄 View Tailored Cover Letter</summary>\n\n```text\n{ev.cover_letter}\n```\n</details>")
            if getattr(ev, "linkedin_pitch", ""):
                md.append(f"\n<details><summary>📱 View LinkedIn / InMail Pitch</summary>\n\n```text\n{ev.linkedin_pitch}\n```\n</details>")
            md.append("\n---\n")

        # ATS Resume Makeovers
        if report.ats_resume_makeovers:
            md.append("## 📝 ATS Resume Makeovers (Google XYZ Formula)\n")
            for idx, m in enumerate(report.ats_resume_makeovers, 1):
                md.append(f"#### Makeover #{idx}: {m.section}")
                md.append(f"- **Before (Generic):** *\"{m.before_bullet}\"*")
                md.append(f"- **After (Optimized):** **\"{m.after_bullet}\"**")
                md.append(f"- **XYZ Breakdown:** `{m.rationale}`\n")

        # 12-Week Roadmap
        if report.production_roadmap:
            md.append("## 🗺️ 12-Week Adaptive Production Upskilling Roadmap\n")
            for p in report.production_roadmap:
                md.append(f"### Phase {p.phase_number}: {p.phase_title} ({p.duration_weeks})")
                md.append(f"**Core Technologies:** `{', '.join(p.core_technologies)}`\n")
                md.append("**Weekly Deliverables:**")
                for w in p.weekly_milestones:
                    md.append(f"- [ ] {w}")
                md.append(f"\n**Capstone Project:** **{p.capstone_project_title}**")
                md.append(f"> {p.capstone_project_description}\n")

        return "\n".join(md)

    @staticmethod
    def to_docx(report: CareerAgentReport, profile: Optional[ResumeProfile] = None) -> bytes:
        """Generates an executive styled Word (.docx) document."""
        doc = docx.Document()

        # Set page margins (0.75 inch)
        for section in doc.sections:
            section.top_margin = Inches(0.75)
            section.bottom_margin = Inches(0.75)
            section.left_margin = Inches(0.75)
            section.right_margin = Inches(0.75)

        cand_name = report.candidate_name or "Candidate"
        domain = report.target_domain or "Technology"

        # Document Title
        title_p = doc.add_paragraph()
        run_title = title_p.add_run(f"CareerAI Executive Dossier: {cand_name}")
        run_title.font.size = Pt(22)
        run_title.font.bold = True
        run_title.font.color.rgb = RGBColor(15, 23, 42)

        subtitle_p = doc.add_paragraph()
        run_sub = subtitle_p.add_run(f"Target Domain: {domain} | Seniority: {report.seniority_assessment or 'Mid-Level'}")
        run_sub.font.size = Pt(11)
        run_sub.font.color.rgb = RGBColor(100, 116, 139)

        doc.add_heading("1. Strategic Executive Assessment", level=1)
        if getattr(report, "executive_english_summary", ""):
            doc.add_paragraph(report.executive_english_summary)
        if getattr(report, "executive_arabic_summary", ""):
            p_ar = doc.add_paragraph()
            p_ar.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            run_ar = p_ar.add_run(report.executive_arabic_summary)
            run_ar.font.size = Pt(10.5)

        doc.add_heading("2. Top Matched Opportunities & Actionable Steps", level=1)
        for ev in report.job_evaluations:
            h = doc.add_heading(f"#{ev.job_rank} {ev.job_title} @ {ev.company} ({ev.agent_match_score}% Match)", level=2)
            p_meta = doc.add_paragraph()
            p_meta.add_run(f"Location: {ev.location} | Apply Link: {ev.source_url}\n").font.italic = True
            
            doc.add_paragraph(f"• Practical Capability: {ev.scoring_rationale}")
            doc.add_paragraph(f"• Action Plan: {ev.exact_action_to_100}")
            if ev.matched_skills:
                doc.add_paragraph(f"• Matched Skills: {', '.join(ev.matched_skills)}")
            if ev.missing_skills:
                doc.add_paragraph(f"• Technical Gaps: {', '.join(ev.missing_skills)}")

        if report.ats_resume_makeovers:
            doc.add_heading("3. ATS Resume Makeovers (Google XYZ Formula)", level=1)
            for m in report.ats_resume_makeovers:
                p_m = doc.add_paragraph()
                p_m.add_run(f"Section: {m.section}\n").font.bold = True
                p_m.add_run(f"Before: {m.before_bullet}\n").font.italic = True
                run_opt = p_m.add_run(f"Optimized: {m.after_bullet}\n")
                run_opt.font.bold = True
                p_m.add_run(f"Breakdown: {m.rationale}\n")

        if report.production_roadmap:
            doc.add_heading("4. 12-Week Production Upskilling Roadmap", level=1)
            for phase in report.production_roadmap:
                doc.add_heading(f"Phase {phase.phase_number}: {phase.phase_title} ({phase.duration_weeks})", level=2)
                p_tools = doc.add_paragraph()
                p_tools.add_run(f"Core Stack: {', '.join(phase.core_technologies)}\n").font.bold = True
                for mile in phase.weekly_milestones:
                    doc.add_paragraph(f"✓ {mile}")
                doc.add_paragraph(f"Capstone Deliverable: {phase.capstone_project_title} — {phase.capstone_project_description}")

        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()
