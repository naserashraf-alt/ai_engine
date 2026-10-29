"""
=============================================================================
src/agent_advisor.py - الوكيل الاستشاري المهني الذكي (AI Career Advisor Agent)
=============================================================================

الغرض (Purpose):
- الوكيل الذكي المستقل (Autonomous Agent) المسؤول عن تقييم الوظائف وحساب النتائج:
  1. حساب نسبة التوافق الفعلي المباشر (agent_match_score) من 0.0 إلى 100.0%.
  2. تحليل فجوة المهارات (Skill Gap Analysis) وحساب النقاط المطلوبة للوصول إلى 100%.
  3. كتابة التعليل الفني (Scoring Rationale) الذي يبرر النسبة المحسوبة.
  4. إعادة صياغة نقاط السيرة الذاتية وفق معادلة Google XYZ لصالح أنظمة ATS.
  5. تصميم خارطة طريق هندسية تكيفية لـ 12 أسبوعاً لسد الفجوات مع مواصفات مشروع تخرج.
  6. صياغة تقرير استراتيجي تنفيذي باللغتين العربية والإنجليزية.

النماذج المدعومة (Supported Models):
- Google Gemini (Gemini 2.5 Pro, 2.0 Pro, 2.0 Flash Thinking, 1.5 Pro).
- OpenAI (GPT-4o, o3-mini, o1).
- Smart Heuristic Evaluator (يعمل محلياً وأوفلاين بدون استهلاك رصيد).

الاتصالات والتبعيات (Dependencies & Connections):
- يستدعي: src/schemas.py
- يُستورد في: app.py, run_agent.py
=============================================================================
"""

import os
import sys
import json
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

from src.schemas import (
    ResumeProfile, CandidateJobSummary, CareerAgentReport,
    AgentJobEvaluation, ResumeMakeover, RoadmapPhase
)

# Check modern google.genai SDK
GOOGLE_GENAI_AVAILABLE = False
try:
    from google import genai
    from google.genai import types
    GOOGLE_GENAI_AVAILABLE = True
except ImportError:
    pass


CAREER_AGENT_SYSTEM_PROMPT = """You are an elite Principal AI Technical Hiring Director and Silicon Valley Career Architect.
Your core mission is to DEEPLY EVALUATE a candidate's profile against target job opportunities and CALCULATE the precise match score and gap analysis yourself.

INPUT PROVIDED:
1. Candidate's verified profile (technical skills, work history, seniority level, domain, education).
2. A shortlist of active job opportunities with company names, locations, required skills, and descriptions.

FOR EACH TARGET JOB, YOU (THE AI AGENT) MUST CALCULATE AND PRODUCE:
1. agent_match_score: Realistic hiring match percentage (0.0 to 100.0%). Evaluate how competitive the candidate is in an actual hiring pool.
2. agent_skills_score: Skills overlap percentage (0.0 to 100.0%).
3. agent_seniority_score: Seniority level alignment score (0.0 to 100.0%).
4. agent_gap_points_to_100: Exact gap percentage (100.0 - agent_match_score).
5. matched_skills: Array of skills the candidate possesses that match this role.
6. missing_skills: Crucial missing skills, tools, or architectural depth needed.
7. scoring_rationale: Concise, highly technical reasoning explaining WHY you calculated this exact match score.
8. why_matched: Core competitive advantages of the candidate for this position.
9. exact_action_to_100: Specific technical steps to bridge the gap to 100% fit.
10. likely_interview_question: The toughest system design or technical question for this role.
11. model_interview_answer_tip: Winning architectural answer and mental framework.
12. cover_letter: Tailored, high-impact executive cover letter connecting candidate's exact skills to this company and role.
13. linkedin_pitch: High-conversion, concise (< 120 words) LinkedIn / InMail recruiter outreach message ready to send.

CRITICAL DOMAIN CONSISTENCY RULE:
- Strictly evaluate domain specialization! If the candidate specializes in AI / Machine Learning, their highest match scores (80-99%) MUST be awarded to roles in AI, Machine Learning, Data Science, Deep Learning, and Computer Vision.
- Purely non-AI roles (such as generic Java Backend, PHP Developer, Frontend Developer, Sales, or HR) MUST be heavily penalized and assigned low match scores (below 45%), unless the role explicitly requires AI/ML engineering.

CORE EVALUATION PRINCIPLE: PRACTICAL JOB EXECUTION CAPABILITY ("Can the candidate do the job?")
- You must evaluate every job by answering ONE CORE PRAGMATIC QUESTION:
  "Can the person who submitted this CV actually execute and perform this job successfully in a production environment?"
- Do NOT base your score on rigid title bureaucracy or arbitrary seniority labels. Assess practical execution feasibility:
  * Does the candidate possess the demonstrated technical skills, tools, and engineering foundation to deliver the core responsibilities of this role?
  * If a candidate has strong mastery of Python, Machine Learning, Deep Learning, PyTorch, Docker, they HAVE the execution capability to perform machine learning & AI engineering jobs!
  * If the job requires specialized production tools the candidate hasn't used, identify the practical capability gap.

PRAGMATIC CAPABILITY GAP ANALYSIS:
- For missing_skills and agent_gap_points_to_100, answer directly:
  "What is specifically preventing the candidate from stepping into this role and executing it tomorrow?"
  List concrete tools, frameworks, or production practices needed.

ACTIONABLE APPLICATION ROADMAP (WHAT TO DO TO APPLY - REQUIRED FOR EVERY JOB):
- In exact_action_to_100, provide a concrete, job-specific action plan answering:
  "What does the candidate have left to do right now so they can confidently apply for this specific job?"
  Structure it as an actionable 3-step checklist:
  1. Bridge: Exact technology/tool to master.
  2. Proof: Specific hands-on project or working demo to build to prove capability.
  3. Tailor: Specific bullet point or project to highlight in their resume when applying for this role.

GLOBAL STRATEGIC OUTPUTS:
- executive_arabic_summary: A comprehensive, motivating, and highly professional career coaching assessment in Arabic (تحليل استراتيجي لموقف المرشح، أسباب احتساب الدرجات، وخطة اقتناص الوظائف).
- executive_english_summary: A strategic executive career summary in English.
- ats_resume_makeovers: Minimum 2 high-impact bullet rewrites using Google XYZ Formula: "Accomplished [X], as measured by [Y], by doing [Z]".
- production_roadmap: 3-phase 12-week roadmap addressing the identified missing skills, complete with capstone project specs.

Sort the job_evaluations descending by agent_match_score. Strictly adhere to the JSON schema.
"""


class CareerAdvisorAgent:
    """Multi-Provider Agentic LLM Career Advisor (Gemini Pro/Flash, OpenAI GPT-4o/o3, Ollama)."""

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.provider = (provider or os.getenv("AI_PROVIDER", "gemini")).lower().strip()
        self.api_key = api_key
        self.model = model
        self.client = None
        self._init_provider()

    def _init_provider(self):
        """Initializes the client based on selected frontier provider."""
        if self.provider == "gemini":
            self.api_key = self.api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            # Default to the most powerful Pro model available
            self.model = self.model or os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
            if self.api_key and GOOGLE_GENAI_AVAILABLE:
                try:
                    self.client = genai.Client(api_key=self.api_key)
                except Exception as e:
                    print(f"⚠️ [Agent Gemini Init Warning]: {e}")
        elif self.provider == "openai":
            self.api_key = self.api_key or os.getenv("OPENAI_API_KEY")
            self.model = self.model or os.getenv("OPENAI_MODEL", "gpt-4o")
        elif self.provider in ("ollama", "local"):
            self.model = self.model or os.getenv("OLLAMA_MODEL", "llama3.3")

    def evaluate_and_advise(
        self,
        profile: ResumeProfile,
        candidate_jobs: List[CandidateJobSummary],
        top_n: int = 5
    ) -> CareerAgentReport:
        """
        Deeply evaluates candidate against candidate jobs, calculating match scores and gaps.
        """
        if self.provider == "gemini" and self.client and self.api_key:
            try:
                return self._call_gemini_evaluator(profile, candidate_jobs, top_n=top_n)
            except Exception as e:
                print(f"⚠️ [Agent Gemini API Notice]: {e}. Switching to Precision Heuristic Evaluator.")
                return self._generate_heuristic_evaluation(profile, candidate_jobs, top_n=top_n)
        elif self.provider == "openai" and self.api_key:
            try:
                return self._call_openai_evaluator(profile, candidate_jobs, top_n=top_n)
            except Exception as e:
                print(f"⚠️ [Agent OpenAI API Notice]: {e}. Switching to Precision Heuristic Evaluator.")
                return self._generate_heuristic_evaluation(profile, candidate_jobs, top_n=top_n)
        else:
            return self._generate_heuristic_evaluation(profile, candidate_jobs, top_n=top_n)

    def _call_openai_evaluator(
        self,
        profile: ResumeProfile,
        candidate_jobs: List[CandidateJobSummary],
        top_n: int = 5
    ) -> CareerAgentReport:
        """Invokes OpenAI (GPT-4o, o3-mini) with structured JSON Schema."""
        import requests
        jobs_payload = []
        for idx, j in enumerate(candidate_jobs[:top_n], 1):
            jobs_payload.append({
                "job_id": j.job_id,
                "title": j.job_title,
                "company": j.company,
                "location": j.location,
                "source_url": j.source_url,
                "experience_level": j.experience_level,
                "required_skills": j.required_skills,
                "description_snippet": j.description_snippet
            })

        user_content = (
            f"=== CANDIDATE PROFILE ===\n"
            f"Name: {profile.personal_info.full_name}\n"
            f"Domain: {profile.primary_domain}\n"
            f"Seniority: {profile.seniority_level} ({profile.total_years_experience} years exp)\n"
            f"Skills: {', '.join(profile.normalized_skills_flat[:30])}\n"
            f"Summary: {profile.professional_summary}\n\n"
            f"=== TARGET JOBS TO EVALUATE & SCORE ===\n"
            f"{json.dumps(jobs_payload, indent=2, ensure_ascii=False)}\n\n"
            f"Calculate the agent_match_score, skills_score, seniority_score, gap_points_to_100, "
            f"and scoring_rationale for each job, and return the complete CareerAgentReport."
        )

        schema_json = CareerAgentReport.model_json_schema()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "career_agent_report",
                    "strict": False,
                    "schema": schema_json
                }
            },
            "temperature": 0.2 if "o" not in self.model else 1.0,
            "messages": [
                {"role": "system", "content": CAREER_AGENT_SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ]
        }

        resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        raw_text = data["choices"][0]["message"]["content"]
        report = CareerAgentReport.model_validate_json(raw_text)

        report.job_evaluations.sort(key=lambda x: x.agent_match_score, reverse=True)
        for idx, ev in enumerate(report.job_evaluations, 1):
            ev.job_rank = idx
            ev.agent_gap_points_to_100 = round(max(100.0 - ev.agent_match_score, 0.0), 1)

        return report

    def _call_gemini_evaluator(
        self,
        profile: ResumeProfile,
        candidate_jobs: List[CandidateJobSummary],
        top_n: int = 5
    ) -> CareerAgentReport:
        """Invokes Gemini 2.0 with structured JSON schema validation to calculate scores."""
        jobs_payload = []
        for idx, j in enumerate(candidate_jobs[:top_n], 1):
            jobs_payload.append({
                "job_id": j.job_id,
                "title": j.job_title,
                "company": j.company,
                "location": j.location,
                "source_url": j.source_url,
                "experience_level": j.experience_level,
                "required_skills": j.required_skills,
                "description_snippet": j.description_snippet
            })

        user_content = (
            f"=== CANDIDATE PROFILE ===\n"
            f"Name: {profile.personal_info.full_name}\n"
            f"Domain: {profile.primary_domain}\n"
            f"Seniority: {profile.seniority_level} ({profile.total_years_experience} years exp)\n"
            f"Skills: {', '.join(profile.normalized_skills_flat[:30])}\n"
            f"Summary: {profile.professional_summary}\n\n"
            f"=== TARGET JOBS TO EVALUATE & SCORE ===\n"
            f"{json.dumps(jobs_payload, indent=2, ensure_ascii=False)}\n\n"
            f"Calculate the agent_match_score, skills_score, seniority_score, gap_points_to_100, "
            f"and scoring_rationale for each job, and return the complete CareerAgentReport."
        )

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=CareerAgentReport,
            temperature=0.2
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=[CAREER_AGENT_SYSTEM_PROMPT, user_content],
            config=config
        )

        report = CareerAgentReport.model_validate_json(response.text)
        # Ensure rankings are sequential based on agent_match_score
        report.job_evaluations.sort(key=lambda x: x.agent_match_score, reverse=True)
        for idx, ev in enumerate(report.job_evaluations, 1):
            ev.job_rank = idx
            ev.agent_gap_points_to_100 = round(max(100.0 - ev.agent_match_score, 0.0), 1)

        return report

    def _generate_heuristic_evaluation(
        self,
        profile: ResumeProfile,
        candidate_jobs: List[CandidateJobSummary],
        top_n: int = 5
    ) -> CareerAgentReport:
        """Deterministic evaluation fallback calculating match scores and gaps."""
        cand_name = profile.personal_info.full_name or "Engineer"
        domain = profile.primary_domain
        seniority = profile.seniority_level
        cand_skills = set(profile.normalized_skills_flat)

        evaluations: List[AgentJobEvaluation] = []
        all_missing = set()

        import re

        for idx, job in enumerate(candidate_jobs[:top_n], 1):
            req_skills = set(s.lower() for s in job.required_skills)
            overlap = cand_skills.intersection(req_skills)
            missing = req_skills - cand_skills
            all_missing.update(missing)

            # Check domain alignment using word boundaries
            title_lower = job.job_title.lower()
            is_ai_cand = "ai" in domain.lower() or "machine learning" in domain.lower()
            is_ai_job = bool(re.search(r'\b(ai|data scientist|data science|machine learning|deep learning|nlp|computer vision|llm|ml engineer)\b', title_lower))

            if is_ai_cand:
                domain_score = 95.0 if is_ai_job else 25.0
            else:
                domain_score = 85.0

            # 1. Technical Stack Overlap Score
            if req_skills:
                skills_overlap_ratio = len(overlap) / max(len(req_skills), 1)
                skills_score = round(min(skills_overlap_ratio * 100.0, 100.0), 1)
            else:
                skills_score = 80.0 if is_ai_job else 55.0

            # 2. Practical Domain Alignment
            if is_ai_cand:
                domain_score = 95.0 if is_ai_job else 35.0
            else:
                domain_score = 85.0

            # 3. Practical Job Execution Capability ("Can this candidate do the job?")
            # We base the score on whether the candidate has the practical skills and domain mastery to deliver
            match_score = round((skills_score * 0.60) + (domain_score * 0.40), 1)

            # Boost if candidate has strong technical overlap with core tools
            if len(overlap) >= 3:
                match_score = max(match_score, 88.0)
            elif len(overlap) >= 2:
                match_score = max(match_score, 78.0)
            elif len(overlap) == 1 and domain_score >= 80:
                match_score = max(match_score, 68.0)

            # Execution capability cap
            match_score = min(match_score, 98.0)
            seniority_score = round(match_score * 0.95, 1)
            gap_points = round(max(100.0 - match_score, 0.0), 1)

            # Practical Execution Verdict: "Can they do the job?"
            if match_score >= 82:
                can_do_verdict = "Yes — High Practical Execution Capability"
            elif match_score >= 68:
                can_do_verdict = "Capable — Ready with Targeted Tooling Preparation"
            else:
                can_do_verdict = "Stretch Role — Requires Substantial Technical Upskilling"

            matched_str = ', '.join(sorted(list(overlap))[:4]) if overlap else 'Core engineering foundations'
            missing_focus = list(missing)[0] if missing else "Cloud Native Production Deployments"

            rationale = (
                f"Can the candidate execute this role? {can_do_verdict}. "
                f"Practical capability is evaluated at {match_score}% based on demonstrated mastery of {matched_str}. "
                f"{f'Remaining technical gap to bridge is {gap_points}%.' if gap_points > 0 else 'Full technical fit.'}"
            )

            # Actionable Roadmap: "What does the candidate need to do right now to apply for this job?"
            matched_focus = list(overlap)[0] if overlap else domain
            action_to_apply = (
                f"To qualify and apply: 1) Acquire hands-on experience with {missing_focus}; "
                f"2) Build a working GitHub demo demonstrating {matched_focus} integration; "
                f"3) Emphasize {matched_str} in your resume tailored for {job.company}."
            )

            # Generate tailored outreach package
            c_letter = self.generate_cover_letter(
                candidate_name=cand_name,
                job_title=job.job_title,
                company=job.company,
                matched_skills=sorted(list(overlap)),
                missing_skills=sorted(list(missing)),
                domain=domain
            )
            li_pitch = self.generate_linkedin_pitch(
                candidate_name=cand_name,
                job_title=job.job_title,
                company=job.company,
                matched_skills=sorted(list(overlap))
            )

            evaluations.append(AgentJobEvaluation(
                job_rank=idx,
                job_id=job.job_id,
                job_title=job.job_title,
                company=job.company,
                location=job.location,
                source_url=job.source_url,
                agent_match_score=match_score,
                agent_skills_score=skills_score,
                agent_seniority_score=seniority_score,
                agent_gap_points_to_100=gap_points,
                matched_skills=sorted(list(overlap)),
                missing_skills=sorted(list(missing)),
                why_matched=f"Practical readiness: candidate possesses {len(overlap)} matching competencies ({matched_str}) required to deliver on {job.job_title}.",
                scoring_rationale=rationale,
                exact_action_to_100=action_to_apply,
                likely_interview_question=f"How would you design a resilient architecture using {', '.join(list(overlap)[:2]) if overlap else 'modern cloud patterns'}?",
                model_interview_answer_tip="Discuss idempotency, cache invalidation, connection pooling, and circuit breaker patterns.",
                cover_letter=c_letter,
                linkedin_pitch=li_pitch
            ))

        evaluations.sort(key=lambda x: x.agent_match_score, reverse=True)
        for i, ev in enumerate(evaluations, 1):
            ev.job_rank = i

        missing_list = list(all_missing)[:5] or ["System Design", "Cloud Architecture"]

        # ==============================================================
        # DOMAIN-SPECIFIC ATS RESUME MAKEOVERS & ACCEPTANCE RATE BOOSTERS
        # ==============================================================
        if is_ai_cand:
            makeovers = [
                ResumeMakeover(
                    section="Work Experience / Machine Learning Projects",
                    before_bullet="Built machine learning models and analyzed datasets using Python.",
                    after_bullet="Engineered end-to-end predictive deep learning pipelines with PyTorch and Scikit-Learn, optimizing inference latency by 38% and achieving 94.6% ROC-AUC on 1.5M+ production records.",
                    rationale="Transforms a generic duty into quantifiable business impact with concrete SOTA frameworks (PyTorch, latency reduction, ROC-AUC metric)."
                ),
                ResumeMakeover(
                    section="AI Architecture & MLOps",
                    before_bullet="Familiar with computer vision, deep learning, and Docker containers.",
                    after_bullet="Containerized real-time computer vision inference services with Docker & FastAPI, deploying YOLOv8 edge models maintaining 60 FPS under sub-18ms latency.",
                    rationale="Proves production engineering ability and latency discipline rather than just academic model training."
                )
            ]
            roadmap = [
                RoadmapPhase(
                    phase_number=1,
                    phase_title="Core Architecture & Model Deployment",
                    duration_weeks="Weeks 1-4",
                    core_technologies=missing_list[:3] or ["PyTorch", "FastAPI", "Docker"],
                    weekly_milestones=[
                        "Package custom deep learning models as production REST / gRPC microservices.",
                        "Implement batching, quantization (FP16/INT8), and GPU memory optimization.",
                        "Set up automated unit and validation test suites with PyTest."
                    ],
                    capstone_project_title="Real-Time Scalable Model Inference Engine",
                    capstone_project_description="Production containerized API serving deep learning predictions with Redis caching and sub-20ms SLA."
                ),
                RoadmapPhase(
                    phase_number=2,
                    phase_title="MLOps, Observability & Data Pipelines",
                    duration_weeks="Weeks 5-8",
                    core_technologies=["MLflow", "Docker Compose", "Prometheus", "CI/CD"],
                    weekly_milestones=[
                        "Implement automated model tracking, dataset versioning, and artifact logging.",
                        "Set up model drift detection, telemetry alerts, and automated rollback triggers.",
                        "Build CI/CD pipelines testing code and validating data schemas on push."
                    ],
                    capstone_project_title="Autonomous Continuous Training & MLOps Pipeline",
                    capstone_project_description="Complete ML pipeline that automatically validates incoming data, triggers retraining, and deploys verified model artifacts."
                ),
                RoadmapPhase(
                    phase_number=3,
                    phase_title="System Design, Portfolio & Direct Recruiter Outreach",
                    duration_weeks="Weeks 9-12",
                    core_technologies=["ML System Design", "GitHub Portfolio", "Hiring Outreach"],
                    weekly_milestones=[
                        "Master machine learning system design (recommendation systems, vector search, search ranking).",
                        "Publish clean GitHub repositories with benchmark charts, architecture diagrams, and live demo URLs.",
                        "Execute direct outreach to engineering managers at target companies presenting tailored portfolio demos."
                    ],
                    capstone_project_title="Production-Grade AI Engineering Showcase",
                    capstone_project_description="Public showcase portfolio featuring end-to-end documentation, performance benchmarks, and live deployed endpoints."
                )
            ]
        elif "frontend" in domain.lower() or "web" in domain.lower():
            makeovers = [
                ResumeMakeover(
                    section="Work Experience",
                    before_bullet="Created web pages and UI components using React.",
                    after_bullet="Architected high-performance modular UI micro-frontends with React 18, TypeScript, and Next.js, cutting First Contentful Paint by 42% and raising Lighthouse score from 64 to 98.",
                    rationale="Quantifies UI performance impact with standard industry benchmarks (Core Web Vitals, Lighthouse)."
                ),
                ResumeMakeover(
                    section="State Management & Testing",
                    before_bullet="Used Redux and wrote tests for front-end code.",
                    after_bullet="Engineered predictable state architecture using Redux Toolkit & React Query, implementing 85%+ code coverage via Vitest and Cypress E2E testing.",
                    rationale="Demonstrates enterprise-level code quality and test discipline that recruiters filter for."
                )
            ]
            roadmap = [
                RoadmapPhase(
                    phase_number=1,
                    phase_title="Next-Gen Frontend Architecture & Performance",
                    duration_weeks="Weeks 1-4",
                    core_technologies=missing_list[:3] or ["TypeScript", "Next.js", "Tailwind CSS"],
                    weekly_milestones=[
                        "Master server-side rendering, streaming SSR, and edge API routes.",
                        "Implement strict TypeScript types, custom hooks, and memoization patterns.",
                        "Achieve 95+ Core Web Vitals across mobile and desktop viewports."
                    ],
                    capstone_project_title="High-Throughput Collaborative Workspace UI",
                    capstone_project_description="Responsive web application with real-time optimistic updates, offline sync, and accessible design systems."
                ),
                RoadmapPhase(
                    phase_number=2,
                    phase_title="State Architecture, Real-Time & Micro-Frontends",
                    duration_weeks="Weeks 5-8",
                    core_technologies=["React Query", "WebSockets", "Docker", "CI/CD"],
                    weekly_milestones=[
                        "Build resilient data-fetching layers with intelligent caching and automated invalidation.",
                        "Integrate live WebSocket channels with reconnection fallbacks.",
                        "Containerize development environments and build automated GitHub Actions pipelines."
                    ],
                    capstone_project_title="Enterprise Real-Time Analytics Dashboard",
                    capstone_project_description="Interactive data visualization dashboard streaming live metrics with sub-second render times."
                ),
                RoadmapPhase(
                    phase_number=3,
                    phase_title="Interview Architecture, Portfolio & Recruiter Conversions",
                    duration_weeks="Weeks 9-12",
                    core_technologies=["Frontend System Design", "Live Demos", "Recruiter Outreach"],
                    weekly_milestones=[
                        "Practice frontend system design (designing Figma, rich text editors, scalable feed architectures).",
                        "Deploy high-polish portfolio on Vercel with clean GitHub source links.",
                        "Direct outreach to frontend leads with personalized video walk-throughs of target company solutions."
                    ],
                    capstone_project_title="Production-Ready Web Engineering Showcase",
                    capstone_project_description="Open-source design system and live component library documented with Storybook and automated regression tests."
                )
            ]
        else:
            makeovers = [
                ResumeMakeover(
                    section="Work Experience",
                    before_bullet="Developed backend APIs and integrated databases.",
                    after_bullet="Architected high-throughput RESTful microservices using Python and PostgreSQL, reducing query latency by 38% and supporting 100k+ daily active users.",
                    rationale="Replaces passive duty statement with quantified business impact and concrete technology stack using Google XYZ structure."
                ),
                ResumeMakeover(
                    section="Skills & Architecture",
                    before_bullet="Familiar with Docker and deployment pipelines.",
                    after_bullet="Containerized multi-tier cloud applications with Docker & Kubernetes, automating CI/CD pipelines to cut release deployment cycles from 2 hours to 8 minutes.",
                    rationale="Showcases DevOps maturity and measurable operational speedup that ATS parsers rank highly."
                )
            ]
            roadmap = [
                RoadmapPhase(
                    phase_number=1,
                    phase_title="Foundation & Critical Skill Gaps",
                    duration_weeks="Weeks 1-4",
                    core_technologies=missing_list[:3] or ["Docker", "Redis", "Cloud"],
                    weekly_milestones=[
                        "Master core paradigms and syntax of targeted technologies.",
                        "Build hands-on prototypes solving real-world integration challenges.",
                        "Refactor previous projects to incorporate automated unit and integration testing."
                    ],
                    capstone_project_title="Distributed Asynchronous Task Engine",
                    capstone_project_description="High-availability worker queue handling heavy background jobs with distributed caching and failover."
                ),
                RoadmapPhase(
                    phase_number=2,
                    phase_title="Production Scale & Observability",
                    duration_weeks="Weeks 5-8",
                    core_technologies=["Prometheus", "Grafana", "Docker Compose", "CI/CD"],
                    weekly_milestones=[
                        "Implement end-to-end telemetry, structured logging, and health dashboards.",
                        "Optimize database schemas with indexing and query plan analysis.",
                        "Simulate load testing and identify performance bottlenecks."
                    ],
                    capstone_project_title="Cloud-Native Microservices Ecosystem",
                    capstone_project_description="Multi-service architecture featuring rate-limiting, JWT authentication, and structured telemetry."
                ),
                RoadmapPhase(
                    phase_number=3,
                    phase_title="Interview Readiness & Final Polish",
                    duration_weeks="Weeks 9-12",
                    core_technologies=["System Design", "Behavioral Frameworks", "Live Coding"],
                    weekly_milestones=[
                        "Conduct mock technical architectural reviews and system design rounds.",
                        "Finalize production GitHub repository with comprehensive README and live demo links.",
                        "Execute targeted outreach and direct applications to top matched companies."
                    ],
                    capstone_project_title="Production-Ready Engineering Portfolio",
                    capstone_project_description="Open-source portfolio repository with full documentation, architectural diagrams, and test suites."
                )
            ]

        arabic_summary = (
            f"قام الـ AI Agent بتقييم القدرة التنفيذية المباشرة لملف المرشح {cand_name} (الإجابة العملية على: هل يقدر يشتغل الوظيفة؟). "
            f"أظهر التقييم أن المرشح في مجال {domain} يمتلك الكفاءة البرمجية الأساسية للتنفيذ الفوري. "
            f"ولمضاعفة نسبة القبول، تم تحديد خطة عمل إجرائية لكل وظيفة وسد الفجوات المتمثلة في: {', '.join(missing_list)}. "
            f"تطبيق صيغ الـ ATS المرفقة (Google XYZ) وخارطة طريق الـ 12 أسبوعاً سيرفع نسبة قبولك من أول مقابلة."
        )

        english_summary = (
            f"The AI Agent evaluated candidate {cand_name} based on practical execution capability ('Can the candidate do this job?'). "
            f"The candidate demonstrates strong technical delivery competence in {domain}. "
            f"To maximize hiring and acceptance rates, specific actionable steps to apply are outlined for every target opportunity, "
            f"accompanied by Google XYZ ATS resume rewrites and a 12-week production engineering roadmap addressing {', '.join(missing_list[:3])}."
        )

        return CareerAgentReport(
            candidate_name=cand_name,
            target_domain=domain,
            seniority_assessment=f"{seniority} (Ready for accelerated progression)",
            executive_arabic_summary=arabic_summary,
            executive_english_summary=english_summary,
            job_evaluations=evaluations,
            ats_resume_makeovers=makeovers,
            production_roadmap=roadmap
        )

    @staticmethod
    def generate_cover_letter(
        candidate_name: str,
        job_title: str,
        company: str,
        matched_skills: List[str],
        missing_skills: List[str],
        domain: str
    ) -> str:
        """Generates a high-conversion, professional cover letter tailored to the specific role and company."""
        top_skills_str = ", ".join(matched_skills[:4]) if matched_skills else "modern software engineering and AI architectures"
        target_company = company if company and company.strip().lower() not in ["", "unknown", "n/a"] else "your engineering team"

        return (
            f"Dear Hiring Team at {target_company},\n\n"
            f"I am writing to express my strong enthusiasm for the {job_title} position. "
            f"With hands-on technical experience and practical execution depth across {top_skills_str}, "
            f"I have focused my engineering work on building scalable, production-ready solutions that deliver measurable results.\n\n"
            f"In reviewing the requirements for {job_title}, I was particularly drawn to your team's technical vision. "
            f"My technical background directly aligns with your requirements:\n"
            f"• Hands-on proficiency in {top_skills_str}, with a strong emphasis on clean architecture, performance, and code quality.\n"
            f"• Pragmatic execution capability: transforming system requirements into dependable, maintainable software.\n"
            f"• Continuous engineering growth: rapidly mastering adjacent frameworks to solve real-world problems.\n\n"
            f"I am eager to bring this practical execution mindset to {target_company} and contribute directly to your team's success.\n\n"
            f"Thank you for your time and consideration. I welcome the opportunity to discuss how my background aligns with your engineering goals.\n\n"
            f"Sincerely,\n"
            f"{candidate_name}"
        )

    @staticmethod
    def generate_linkedin_pitch(
        candidate_name: str,
        job_title: str,
        company: str,
        matched_skills: List[str]
    ) -> str:
        """Generates a high-conversion, punchy LinkedIn / InMail recruiter outreach message."""
        target_company = company if company and company.strip().lower() not in ["", "unknown", "n/a"] else "your team"
        top_skills_str = ", ".join(matched_skills[:3]) if matched_skills else "software engineering"

        return (
            f"Hi there,\n\n"
            f"I noticed the {job_title} role at {target_company} and wanted to reach out directly. "
            f"With proven hands-on experience across {top_skills_str}, I build reliable, high-performance systems "
            f"and would love to bring this practical execution to your team.\n\n"
            f"I've reviewed your engineering priorities and believe I can make an immediate contribution. "
            f"Would you be open to a brief 10-minute chat this week to connect?\n\n"
            f"Best regards,\n"
            f"{candidate_name}"
        )
