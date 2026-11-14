"""
=============================================================================
src/schemas.py - Strongly-Typed Data Contracts (Pydantic V2 Schemas)
=============================================================================

Purpose:
- Defines standardized, strongly-typed data structures for the entire AI Engine.
- Guarantees automated validation, serialization, and error-free integration across
  CV parsing, hybrid matching, ATS scoring, and agent career advisement.

Core Models:
1. Resume Profile:
   - PersonalInfo: Contact information and verified profiles (LinkedIn, GitHub).
   - ExperienceItem, EducationItem, ProjectItem, CertificationItem: Career history.
   - SkillsCategorized: Grouped skills (Technical, Tools & Platforms, Soft).
   - ResumeProfile: Full candidate representation with Careerk export support.

2. Matching & Advisory Models:
   - CandidateJobSummary: Retrieved job record for matching.
   - AgentJobEvaluation: Multi-agent evaluation, match scoring, and gap analysis.
   - ResumeMakeover: Impact-driven bullet improvements using Google XYZ formula.
   - RoadmapPhase: Structured 12-week career growth roadmap.
   - CareerAgentReport: Full strategic advisory dossier.

Dependencies:
- Imported in: src/ai_extractor.py, src/matcher.py, src/agent_advisor.py,
  src/ats_scorer.py, src/api_server.py, app.py
=============================================================================
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
import re
from pydantic import BaseModel, Field


def parse_date_helper(date_str: Optional[str], is_end: bool = False) -> Optional[datetime]:
    """Helper to parse varied date representations into datetime objects."""
    if not date_str:
        return None
    s = str(date_str).strip().lower()
    if s in ['present', 'current', 'now', 'ongoing', 'active']:
        return datetime.now(timezone.utc)
    
    # Try YYYY-MM or YYYY/MM
    m = re.search(r'(\d{4})[-/.](\d{1,2})', s)
    if m:
        year, month = int(m.group(1)), int(m.group(2))
        return datetime(year, min(max(month, 1), 12), 1, tzinfo=timezone.utc)
        
    # Month name mapping
    month_map = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
        'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
        'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
    }
    # Try Month YYYY (e.g. Jan 2021 or January 2021)
    m = re.search(r'([a-zA-Z]+)[,\s]+(\d{4})', s)
    if m:
        month_str, year = m.group(1).lower(), int(m.group(2))
        month = month_map.get(month_str, 12 if is_end else 1)
        return datetime(year, month, 1, tzinfo=timezone.utc)

    # Try YYYY only
    m = re.search(r'\b(19\d{2}|20\d{2})\b', s)
    if m:
        year = int(m.group(1))
        month = 12 if is_end else 1
        return datetime(year, month, 1, tzinfo=timezone.utc)

    return None


def calculate_tenure_from_experiences(experiences: List[Any]) -> float:
    """Calculates verified total years of experience from a list of ExperienceItems."""
    total_months = 0
    now = datetime.now(timezone.utc)
    for exp in experiences:
        s_date = parse_date_helper(getattr(exp, 'start_date', None))
        e_date = parse_date_helper(getattr(exp, 'end_date', None), is_end=True)
        if getattr(exp, 'is_current', False) or (e_date is None and s_date is not None):
            e_date = now
            
        if s_date and e_date and e_date >= s_date:
            months = (e_date.year - s_date.year) * 12 + (e_date.month - s_date.month) + 1
            total_months += min(months, 180)  # Safe cap
            
    if total_months <= 0:
        return 0.0
    return round(total_months / 12.0, 1)


class PersonalInfo(BaseModel):
    full_name: str = Field(default="", description="Candidate's full name")
    headline: Optional[str] = Field(default=None, description="Professional headline (e.g., 'Senior Machine Learning Engineer')")
    email: Optional[str] = Field(default=None, description="Primary email address")
    phone: Optional[str] = Field(default=None, description="Phone number with country code")
    location: Optional[str] = Field(default=None, description="City, Country or current residence (e.g., 'Cairo, Egypt')")
    links: Dict[str, str] = Field(default_factory=dict, description="URLs like linkedin, github, portfolio, website, blog")


class ExperienceItem(BaseModel):
    job_title: str = Field(default="", description="Title of the role held")
    company: str = Field(default="", description="Company or organization name")
    location: Optional[str] = Field(default=None, description="Location or 'Remote'")
    start_date: Optional[str] = Field(default=None, description="Start date (e.g. 'Jan 2022', '2022')")
    end_date: Optional[str] = Field(default=None, description="End date (e.g. 'Present', 'Dec 2024')")
    is_current: bool = Field(default=False, description="True if this is the candidate's active current role")
    description: Optional[str] = Field(default=None, description="Overview of core duties")
    key_achievements: List[str] = Field(default_factory=list, description="Quantified achievements, accomplishments, or key project bullets")
    technologies_used: List[str] = Field(default_factory=list, description="Specific tech stack, frameworks, tools used in this role")


class EducationItem(BaseModel):
    degree: str = Field(default="", description="Degree type (e.g. 'Bachelor of Science', 'Master', 'PhD', 'Diploma')")
    field_of_study: Optional[str] = Field(default=None, description="Field of study or major (e.g. 'Computer Science', 'Data Engineering')")
    institution: str = Field(default="", description="University, college, or educational institution")
    graduation_year: Optional[str] = Field(default=None, description="Graduation year or date range (e.g. '2024', 'Expected 2025')")
    grade_or_gpa: Optional[str] = Field(default=None, description="GPA, grade, or honors if specified")


class ProjectItem(BaseModel):
    title: str = Field(default="", description="Name of the project")
    description: str = Field(default="", description="Brief description of the problem solved and architecture")
    technologies: List[str] = Field(default_factory=list, description="Languages, libraries, and tools used")
    url: Optional[str] = Field(default=None, description="Repository link, live demo, or case study URL")


class CertificationItem(BaseModel):
    name: str = Field(default="", description="Name of the certification or license")
    issuer: str = Field(default="", description="Issuing organization (e.g. AWS, Google Cloud, DeepLearning.AI)")
    issue_date: Optional[str] = Field(default=None, description="Date or year of certification")
    credential_url: Optional[str] = Field(default=None, description="Credential ID or verification link")


class LanguageItem(BaseModel):
    language: str = Field(default="", description="Language name (e.g., 'Arabic', 'English', 'German')")
    proficiency: str = Field(default="Proficient", description="Proficiency level (e.g. 'Native', 'Fluent', 'Professional', 'Intermediate')")


class SkillsCategorized(BaseModel):
    technical_skills: List[str] = Field(default_factory=list, description="Core programming languages, frameworks, libraries, databases")
    tools_and_platforms: List[str] = Field(default_factory=list, description="DevOps, cloud providers, developer tools, CI/CD, operating systems")
    soft_skills: List[str] = Field(default_factory=list, description="Interpersonal, problem-solving, collaboration, communication")


class ResumeProfile(BaseModel):
    personal_info: PersonalInfo = Field(default_factory=PersonalInfo)
    professional_summary: str = Field(default="", description="Executive career summary highlighting key experience and value proposition")
    primary_domain: str = Field(default="Software Engineering", description="Detected primary technical domain (e.g. 'AI / Machine Learning', 'Backend Engineering', 'Frontend Engineering', 'Full Stack', 'Data Science', 'DevOps / Cloud', 'Mobile Development', 'Cybersecurity')")
    seniority_level: str = Field(default="Junior", description="Calculated seniority level: 'Entry-Level / Intern', 'Junior', 'Mid-Level', 'Senior', 'Lead / Staff', 'Director / Executive'")
    total_years_experience: float = Field(default=0.0, description="Calculated total years of professional experience")
    skills: SkillsCategorized = Field(default_factory=SkillsCategorized)
    normalized_skills_flat: List[str] = Field(default_factory=list, description="Clean, lowercased, deduplicated list of all technical skills for job matching")
    work_experience: List[ExperienceItem] = Field(default_factory=list)
    education: List[EducationItem] = Field(default_factory=list)
    projects: List[ProjectItem] = Field(default_factory=list)
    certifications: List[CertificationItem] = Field(default_factory=list)
    languages: List[LanguageItem] = Field(default_factory=list)
    extraction_metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata about extraction (provider, model, token count, status)")

    def to_careerk_dict(self, job_seeker_id: str) -> Dict[str, Any]:
        """
        Transforms ResumeProfile into the exact NlpParseCvResponse schema
        expected by careerk NestJS backend (cv-parse.service.ts).
        """
        # Split first and last name
        name_parts = (self.personal_info.full_name or "Candidate").strip().split(maxsplit=1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        # Map DegreeTypeEnum
        def map_degree_type(deg: str) -> str:
            d = (deg or "").upper()
            if any(k in d for k in ["BACHELOR", "BSC", "B.S", "LICENCE", "ENGINEER"]):
                return "BACHELOR"
            if any(k in d for k in ["MASTER", "MSC", "M.S", "MBA"]):
                return "MASTER"
            if any(k in d for k in ["PHD", "DOCTOR"]):
                return "PHD"
            if "ASSOCIATE" in d:
                return "ASSOCIATE"
            if "BOOTCAMP" in d:
                return "BOOTCAMP"
            if "CERTIF" in d:
                return "CERTIFICATION"
            if any(k in d for k in ["HIGH SCHOOL", "SECONDARY", "THANAWEYA"]):
                return "HIGH_SCHOOL"
            return "BACHELOR"

        # Map Education
        education_payload = []
        for edu in self.education:
            # Parse dates
            grad_year = None
            if edu.graduation_year:
                m = re.search(r'\b(19\d{2}|20\d{2})\b', edu.graduation_year)
                if m:
                    grad_year = m.group(1)

            start_iso = f"{int(grad_year)-4}-09-01" if grad_year else "2018-09-01"
            end_iso = f"{grad_year}-06-30" if grad_year else "2022-06-30"

            gpa_float = None
            if edu.grade_or_gpa:
                gpa_match = re.search(r'(\d+(?:\.\d+)?)', edu.grade_or_gpa)
                if gpa_match:
                    try:
                        gpa_float = float(gpa_match.group(1))
                    except ValueError:
                        gpa_float = None

            education_payload.append({
                "institutionName": edu.institution or "University / Higher Institute",
                "degreeType": map_degree_type(edu.degree),
                "fieldOfStudy": edu.field_of_study or "Computer Science / Information Technology",
                "startDate": start_iso,
                "endDate": end_iso,
                "isCurrent": False,
                "gpa": gpa_float,
                "description": f"{edu.degree} in {edu.field_of_study or 'Computer Science'} from {edu.institution or 'Accredited Institution'}"
            })

        # Map Work Experience
        work_payload = []
        for exp in self.work_experience:
            s_parsed = parse_date_helper(exp.start_date)
            e_parsed = parse_date_helper(exp.end_date, is_end=True)
            
            s_iso = s_parsed.strftime("%Y-%m-%d") if s_parsed else "2022-01-01"
            is_active = exp.is_current or (exp.end_date and exp.end_date.strip().lower() in ["present", "current", "now", "ongoing"])
            e_iso = e_parsed.strftime("%Y-%m-%d") if (e_parsed and not is_active) else None

            desc_parts = []
            if exp.description:
                desc_parts.append(exp.description)
            if exp.key_achievements:
                desc_parts.extend([f"• {a}" for a in exp.key_achievements])
            desc_text = "\n".join(desc_parts) if desc_parts else f"Role of {exp.job_title} at {exp.company}"

            work_payload.append({
                "companyName": exp.company or "Company",
                "jobTitle": exp.job_title or "Software Engineer",
                "location": exp.location or self.personal_info.location or "Remote",
                "startDate": s_iso,
                "endDate": e_iso,
                "isCurrent": is_active,
                "description": desc_text
            })

        # Map Skills (deduplicated, verified technical vs soft)
        skills_payload = []
        seen_skills = set()
        for skill_name in self.normalized_skills_flat:
            clean = skill_name.strip()
            if clean and clean.lower() not in seen_skills:
                skills_payload.append({"name": clean, "verified": True})
                seen_skills.add(clean.lower())

        for skill_name in self.skills.soft_skills:
            clean = skill_name.strip()
            if clean and clean.lower() not in seen_skills:
                skills_payload.append({"name": clean, "verified": False})
                seen_skills.add(clean.lower())

        return {
            "jobSeekerId": job_seeker_id,
            "parsedAt": datetime.now(timezone.utc).isoformat(),
            "data": {
                "personalInfo": {
                    "firstName": first_name,
                    "lastName": last_name,
                    "email": self.personal_info.email or "",
                    "phone": self.personal_info.phone or "",
                    "location": self.personal_info.location,
                    "linkedinUrl": self.personal_info.links.get("linkedin"),
                    "githubUrl": self.personal_info.links.get("github"),
                    "portfolioUrl": self.personal_info.links.get("portfolio") or self.personal_info.links.get("website")
                },
                "professionalSummary": self.professional_summary or f"{self.seniority_level} {self.primary_domain} with proven experience in {', '.join(self.normalized_skills_flat[:5])}.",
                "title": self.personal_info.headline or f"{self.seniority_level} {self.primary_domain}",
                "education": education_payload,
                "workExperience": work_payload,
                "skills": skills_payload,
                "yearsOfExperience": self.total_years_experience,
                "expectedSalary": None,
                "workPreference": "HYBRID",
                "availabilityStatus": "OPEN_TO_WORK"
            }
        }


# ==============================================================
# Job Matching & Career Agent Schemas
# ==============================================================

class CandidateJobSummary(BaseModel):
    """Raw candidate job record retrieved from the dataset for AI evaluation."""
    job_id: str
    job_title: str
    company: str
    location: str
    source_url: str
    experience_level: str = "Mid-Level"
    required_skills: List[str] = Field(default_factory=list)
    description_snippet: str = ""


class AgentJobEvaluation(BaseModel):
    """Deep job matching and gap evaluation calculated directly by the AI Agent."""
    job_rank: int = Field(default=1, description="Ranking sequence number")
    job_id: str = Field(default="", description="Unique job identifier")
    job_title: str = Field(description="Job title")
    company: str = Field(description="Company name")
    location: str = Field(description="Location or Remote")
    source_url: str = Field(description="Direct URL to apply")
    agent_match_score: float = Field(description="Practical Job Execution Match Score (0.0 - 100.0%) answering: 'Can this candidate perform and deliver this job successfully?'")
    agent_skills_score: float = Field(description="Skills overlap score (0.0 - 100.0%) calculated by the AI Agent")
    agent_seniority_score: float = Field(description="Practical engineering execution readiness score (0.0 - 100.0%)")
    agent_gap_points_to_100: float = Field(description="Practical gap points needed to reach 100% execution capability (100.0 - agent_match_score)")
    matched_skills: List[str] = Field(default_factory=list, description="Skills verified present in candidate profile")
    missing_skills: List[str] = Field(default_factory=list, description="Crucial missing skills and tools required to perform this job")
    why_matched: str = Field(description="Practical execution strengths of candidate for this role")
    scoring_rationale: str = Field(description="Direct technical answer to: 'Can this candidate execute this job and why?'")
    exact_action_to_100: str = Field(description="Actionable 3-step application checklist: 'What does the candidate need to do right now to apply for this job?'")
    likely_interview_question: str = Field(description="Toughest technical or architectural interview question for this specific role")
    model_interview_answer_tip: str = Field(description="Winning answer framework/key points to mention")
    cover_letter: str = Field(default="", description="Tailored executive cover letter for this specific company and role")
    linkedin_pitch: str = Field(default="", description="Direct high-conversion LinkedIn / InMail recruiter outreach pitch")


class ResumeMakeover(BaseModel):
    section: str = Field(description="Resume section being improved (e.g., 'Work Experience', 'Skills', 'Summary')")
    before_bullet: str = Field(description="Original or typical generic resume bullet point")
    after_bullet: str = Field(description="ATS-optimized, impact-driven bullet point using Google XYZ formula (Accomplished [X], as measured by [Y], by doing [Z])")
    rationale: str = Field(description="Why this change dramatically improves ATS score and recruiter impressions")


class RoadmapPhase(BaseModel):
    phase_number: int = Field(description="Phase sequence (1, 2, 3)")
    phase_title: str = Field(description="Phase title (e.g., 'Foundation & Skill Gaps', 'Production Engineering', 'Capstone & System Design')")
    duration_weeks: str = Field(description="Duration (e.g., 'Weeks 1-4')")
    core_technologies: List[str] = Field(description="Technologies and tools mastered in this phase")
    weekly_milestones: List[str] = Field(description="Weekly learning goals and deliverables")
    capstone_project_title: str = Field(description="Hands-on portfolio project title")
    capstone_project_description: str = Field(description="Architecture and technical specs for the project")


class CareerAgentReport(BaseModel):
    candidate_name: str = Field(description="Candidate's full name")
    target_domain: str = Field(description="Primary engineering specialization")
    seniority_assessment: str = Field(description="Seniority assessment and readiness evaluation")
    executive_arabic_summary: str = Field(description="Professional, motivating executive coaching summary in Arabic")
    executive_english_summary: str = Field(description="Strategic executive career summary in English")
    job_evaluations: List[AgentJobEvaluation] = Field(description="Top ranked jobs with Match Score and Gap Analysis calculated directly by the AI Agent")
    ats_resume_makeovers: List[ResumeMakeover] = Field(description="Targeted resume bullet improvements")
    production_roadmap: List[RoadmapPhase] = Field(description="12-Week Production Career Roadmap")


