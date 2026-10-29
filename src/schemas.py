"""
=============================================================================
src/schemas.py - نماذج البيانات الصارمة (Pydantic V2 Schemas)
=============================================================================

الغرض (Purpose):
- تعريف الهياكل البيانية المنظمة الصارمة (Strongly-Typed Data Contracts) للنظام.
- يضمن التحقق الآلي من صحة بيانات السير الذاتية وتقارير الذكاء الاصطناعي وخلوها من الأخطاء.

النماذج الرئيسية (Core Models):
1. نماذج السيرة الذاتية (Resume Profile):
   - PersonalInfo: بيانات الاتصال والروابط (LinkedIn, GitHub).
   - ExperienceItem, EducationItem, ProjectItem, CertificationItem: الخبرات والتعليم.
   - SkillsCategorized: تصنيف المهارات (Technical, Tools, Soft).
   - ResumeProfile: البروفايل الكامل للمرشح.

2. نماذج المطابقة والوكيل الاستشاري (Matching & Agent):
   - CandidateJobSummary: بطاقة الوظيفة المرشحة للمطابقة.
   - AgentJobEvaluation: تقييم الوكيل الذكي للوظيفة وحساب الماتش والفجوات.
   - ResumeMakeover: صياغة نقاط السيرة الذاتية بمعادلة Google XYZ.
   - RoadmapPhase: مراحل خارطة الطريق المهنية (12 أسبوعاً).
   - CareerAgentReport: التقرير الاستراتيجي الشامل.

الاتصالات والتبعيات (Dependencies & Connections):
- يُستورد في: src/ai_extractor.py, src/matcher.py, src/agent_advisor.py, app.py, run_agent.py
=============================================================================
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


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


