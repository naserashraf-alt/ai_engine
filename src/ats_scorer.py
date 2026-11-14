"""
=============================================================================
src/ats_scorer.py - Applicant Tracking System (ATS) Compatibility Engine
=============================================================================

Purpose:
- Evaluates CV/Resume documents against enterprise ATS parsing criteria.
- Calculates an objective ATS Readiness Score (0 - 100%).
- Provides actionable recommendations to optimize CV layout, keyword density,
  section structure, and quantifiable metrics for automated screening.
=============================================================================
"""

import re
from typing import Dict, Any, List
from pydantic import BaseModel, Field

from src.schemas import ResumeProfile


class ATSScoreBreakdown(BaseModel):
    section_structure_score: float = Field(description="Completeness of core resume sections (0-100)")
    quantifiable_impact_score: float = Field(description="Presence of metrics, numbers, and impact verbs (0-100)")
    skill_density_score: float = Field(description="Clarity and itemization of technical skills (0-100)")
    contact_online_presence_score: float = Field(description="Completeness of contact and profile links (0-100)")
    content_length_score: float = Field(description="Ideal length and reading density (0-100)")


class ATSScoreResult(BaseModel):
    overall_score: float = Field(description="Final composite ATS compatibility score (0-100)")
    grade: str = Field(description="Letter grade (A+, A, B, C, Needs Work)")
    verdict: str = Field(description="Executive summary of ATS compliance")
    strengths: List[str] = Field(default_factory=list, description="Compliant elements identified")
    improvements: List[str] = Field(default_factory=list, description="Actionable recommendations to improve score")
    breakdown: ATSScoreBreakdown = Field(description="Category breakdown scores")


class ATSCompatibilityScorer:
    """Enterprise ATS Parsing and Compliance Analyzer."""

    ACTION_VERBS = {
        "architected", "engineered", "developed", "spearheaded", "orchestrated",
        "implemented", "optimized", "accelerated", "reduced", "increased",
        "designed", "streamlined", "deployed", "scaled", "delivered",
        "automated", "managed", "led", "established", "formulated",
        "collaborated", "built", "maintained", "analyzed", "resolved"
    }

    @classmethod
    def evaluate(cls, profile: ResumeProfile) -> ATSScoreResult:
        """
        Evaluates a parsed ResumeProfile and returns structured ATS evaluation.
        """
        strengths = []
        improvements = []

        # -------------------------------------------------------------
        # 1. Section Structure Score (Weight: 25%)
        # -------------------------------------------------------------
        section_points = 0.0
        total_sections = 5

        # Summary
        if profile.professional_summary and len(profile.professional_summary.split()) >= 15:
            section_points += 20.0
            strengths.append("Executive Professional Summary is clear and comprehensive.")
        else:
            improvements.append("Add a concise 3-4 sentence Professional Summary at the top of your resume.")

        # Work Experience
        if len(profile.work_experience) >= 1:
            section_points += 20.0
            strengths.append(f"Work Experience section contains {len(profile.work_experience)} distinct roles.")
        else:
            improvements.append("Include relevant internships, freelance work, or employment experience.")

        # Education
        if len(profile.education) >= 1 and profile.education[0].institution:
            section_points += 20.0
            strengths.append("Education section clearly specifies institution and degree credentials.")
        else:
            improvements.append("Clearly state your university, degree type, and field of study.")

        # Skills
        if len(profile.normalized_skills_flat) >= 5:
            section_points += 20.0
            strengths.append("Skills section contains well-itemized technical keywords.")
        else:
            improvements.append("Itemize at least 8-12 core technical skills for automated keyword scanning.")

        # Projects or Certifications
        if len(profile.projects) >= 1 or len(profile.certifications) >= 1:
            section_points += 20.0
            strengths.append("Highlights verifiable projects or industry certifications.")
        else:
            improvements.append("Add 2-3 technical projects with GitHub links or case study outcomes.")

        structure_score = min(100.0, section_points)

        # -------------------------------------------------------------
        # 2. Quantifiable Impact & Action Verbs (Weight: 25%)
        # -------------------------------------------------------------
        achievements_text = " ".join([
            " ".join(exp.key_achievements) + " " + (exp.description or "")
            for exp in profile.work_experience
        ])
        for proj in profile.projects:
            achievements_text += " " + proj.description

        words = achievements_text.lower().split()
        
        # Check action verbs
        matched_verbs = [v for v in cls.ACTION_VERBS if v in words]
        verb_score = min(50.0, len(matched_verbs) * 10.0)
        if len(matched_verbs) >= 3:
            strengths.append(f"Strong action verbs detected ({', '.join(matched_verbs[:3])}).")
        else:
            improvements.append("Begin accomplishment bullets with strong action verbs (e.g., 'Engineered', 'Optimized', 'Spearheaded').")

        # Check numbers and metrics (e.g. 20%, $50K, 2x, 500ms)
        metrics_matches = re.findall(r'(\d+[\%\+]?|\$\d+|\d+x|\d+\s*(?:ms|sec|users|clients|nodes))', achievements_text, re.IGNORECASE)
        metric_score = min(50.0, len(metrics_matches) * 12.5)
        if len(metrics_matches) >= 2:
            strengths.append("Bullet points include quantifiable business and performance metrics.")
        else:
            improvements.append("Quantify achievements with concrete numbers or percentages (e.g., 'reduced latency by 35%').")

        impact_score = min(100.0, verb_score + metric_score)

        # -------------------------------------------------------------
        # 3. Skill Density & Canonical Clarity (Weight: 20%)
        # -------------------------------------------------------------
        skill_count = len(profile.normalized_skills_flat)
        if 8 <= skill_count <= 25:
            skill_score = 100.0
            strengths.append(f"Optimal technical skill density ({skill_count} relevant technologies).")
        elif skill_count > 25:
            skill_score = 80.0
            improvements.append("Curate skills list to focus on high-impact technologies to avoid keyword stuffing.")
        else:
            skill_score = max(40.0, skill_count * 10.0)
            improvements.append("Expand your technical stack with relevant tools, frameworks, and databases.")

        # -------------------------------------------------------------
        # 4. Contact & Online Presence (Weight: 15%)
        # -------------------------------------------------------------
        contact_points = 0.0
        p_info = profile.personal_info

        if p_info.email and "@" in p_info.email:
            contact_points += 25.0
        else:
            improvements.append("Ensure your professional email address is prominently visible.")

        if p_info.phone:
            contact_points += 25.0
        else:
            improvements.append("Include an accessible phone number with international country code.")

        if p_info.location:
            contact_points += 20.0
        else:
            improvements.append("Specify your city and country of residence.")

        links = p_info.links or {}
        if links.get("linkedin"):
            contact_points += 15.0
            strengths.append("Verified LinkedIn profile link is present.")
        else:
            improvements.append("Include your complete LinkedIn profile URL.")

        if links.get("github") or links.get("portfolio"):
            contact_points += 15.0
            strengths.append("GitHub / Portfolio link provides verifiable code evidence.")
        else:
            improvements.append("Include your GitHub or online portfolio link.")

        contact_score = min(100.0, contact_points)

        # -------------------------------------------------------------
        # 5. Content Length & Reading Flow (Weight: 15%)
        # -------------------------------------------------------------
        meta = profile.extraction_metadata or {}
        word_count = meta.get("word_count", len(achievements_text.split()) + 150)

        if 300 <= word_count <= 1100:
            length_score = 100.0
            strengths.append(f"Balanced document length (~{word_count} words).")
        elif word_count < 300:
            length_score = 65.0
            improvements.append("Your resume appears brief; elaborate on responsibilities and project outcomes.")
        else:
            length_score = 75.0
            improvements.append("Consider condensing resume content to maintain a tight 1-2 page executive format.")

        # -------------------------------------------------------------
        # Composite Calculation
        # -------------------------------------------------------------
        overall = round(
            (0.25 * structure_score) +
            (0.25 * impact_score) +
            (0.20 * skill_score) +
            (0.15 * contact_score) +
            (0.15 * length_score),
            1
        )

        if overall >= 90.0:
            grade = "A+"
            verdict = "Exceptional ATS Compliance — Highly optimized for enterprise recruitment parsers."
        elif overall >= 80.0:
            grade = "A"
            verdict = "Strong ATS Compliance — Standard layout with clear structure and good keyword coverage."
        elif overall >= 70.0:
            grade = "B"
            verdict = "Good ATS Baseline — Legible by automated parsers with minor room for metric quantification."
        elif overall >= 55.0:
            grade = "C"
            verdict = "Moderate ATS Compliance — Missing some key metrics or contact links."
        else:
            grade = "Needs Work"
            verdict = "Low ATS Compatibility — Requires structural formatting and content elaboration."

        breakdown = ATSScoreBreakdown(
            section_structure_score=structure_score,
            quantifiable_impact_score=impact_score,
            skill_density_score=skill_score,
            contact_online_presence_score=contact_score,
            content_length_score=length_score
        )

        return ATSScoreResult(
            overall_score=overall,
            grade=grade,
            verdict=verdict,
            strengths=strengths,
            improvements=improvements,
            breakdown=breakdown
        )
