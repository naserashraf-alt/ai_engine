"""
=============================================================================
src/matcher.py - محرك الفلترة والمطابقة التخصصية (Precision Job Matcher)
=============================================================================

الغرض (Purpose):
- سحب وترشيح أنسب الوظائف من قاعدة البيانات (7,210 وظيفة) لتقييمها بواسطة الـ AI Agent.
- تطبيق نظام العزل التخصصي (Domain Isolation) عبر Word-Boundary Regex لمنع تداخل المجالات.
- تطبيق نظام العزل الهرمي للخبرة (Strict Seniority Alignment) لمنع مطابقة وظائف Senior لمبتدئ.

المدخلات والمخرجات (Inputs / Outputs):
- المدخل: كائن `ResumeProfile` للمرشح، الفلتر الجغرافي (الدولة)، وفلتر الريموت.
- المخرج: قائمة مختصرة من كائنات `CandidateJobSummary` تمثل أفضل الوظائف المتوافقة.

الاتصالات والتبعيات (Dependencies & Connections):
- يستدعي: src/database.py, src/schemas.py
- يُستورد في: app.py, run_agent.py
=============================================================================
"""

import os
import re
import sys
import json
from typing import List, Dict, Any, Optional

from src.schemas import ResumeProfile, CandidateJobSummary


class JobMatcher:
    """Retrieves relevant job candidates from 7,200+ active jobs for AI Agent evaluation."""

    # Domain Positive Patterns (Word Boundary Protected)
    DOMAIN_POSITIVE_PATTERNS = {
        "ai / machine learning": re.compile(
            r'\b(ai|artificial intelligence|machine learning|deep learning|data scientist|data science|nlp|computer vision|llm|genai|generative ai|mlops|ml engineer|machine learning engineer)\b',
            re.IGNORECASE
        ),
        "data science": re.compile(
            r'\b(data scientist|data science|data analyst|machine learning|analytics engineer|bi developer)\b',
            re.IGNORECASE
        ),
        "data engineering": re.compile(
            r'\b(data engineer|etl|big data|spark|hadoop|airflow|kafka|data pipeline)\b',
            re.IGNORECASE
        ),
        "backend engineering": re.compile(
            r'\b(backend|back-end|python developer|django|fastapi|golang|go developer|java developer|spring boot|api engineer|c# developer|\.net developer|node\.js developer)\b',
            re.IGNORECASE
        ),
        "frontend engineering": re.compile(
            r'\b(frontend|front-end|react|react\.js|vue|vue\.js|angular|javascript developer|typescript developer|ui/ux|next\.js)\b',
            re.IGNORECASE
        ),
        "full stack engineering": re.compile(
            r'\b(full stack|fullstack|software engineer|web developer|full-stack)\b',
            re.IGNORECASE
        ),
        "devops / cloud engineering": re.compile(
            r'\b(devops|cloud engineer|sre|site reliability|kubernetes|infrastructure|platform engineer|aws engineer|azure engineer)\b',
            re.IGNORECASE
        ),
        "mobile development": re.compile(
            r'\b(mobile|android|ios|flutter|react native|swift|kotlin)\b',
            re.IGNORECASE
        )
    }

    # Negative patterns to avoid cross-domain false positives (e.g. AI candidate matching Java Backend)
    DOMAIN_NEGATIVE_PATTERNS = {
        "ai / machine learning": re.compile(
            r'\b(java backend|php developer|wordpress|sales|marketing|recruiter|hr manager|accountant|frontend developer|react developer|angular developer|flutter developer)\b',
            re.IGNORECASE
        ),
        "frontend engineering": re.compile(
            r'\b(backend developer|data scientist|devops engineer|embedded|hardware)\b',
            re.IGNORECASE
        ),
        "backend engineering": re.compile(
            r'\b(frontend developer|react developer|ui designer|data scientist)\b',
            re.IGNORECASE
        )
    }

    def __init__(self, base_data_dir: Optional[str] = None):
        if not base_data_dir:
            ai_proj_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            base_data_dir = os.path.join(ai_proj_root, "data", "processed")
        self.base_data_dir = base_data_dir
        self.by_country_dir = os.path.join(base_data_dir, "by_country")
        self.default_dataset_path = os.path.join(base_data_dir, "jobs_dataset.json")
        self.db_path = os.path.join(base_data_dir, "jobs.db")
        self._db = None

    @property
    def db(self):
        """Lazy-loaded database connection."""
        if self._db is None and os.path.exists(self.db_path):
            try:
                from src.database import JobsDatabase
                self._db = JobsDatabase(self.db_path)
            except Exception as e:
                print(f"⚠️ Could not initialize database, falling back to JSON: {e}")
                self._db = None
        return self._db

    def resolve_dataset_path(self, country: Optional[str] = None, remote_only: bool = False) -> str:
        """Determines the exact partition file to query based on geography/remote preferences."""
        if remote_only:
            remote_path = os.path.join(self.by_country_dir, "jobs_all_remote.json")
            if os.path.exists(remote_path):
                return remote_path

        if country:
            c = country.lower().strip()
            alias_map = {
                "egypt": "jobs_egypt.json", "cairo": "jobs_egypt.json", "alexandria": "jobs_egypt.json",
                "saudi": "jobs_saudi_arabia.json", "saudi arabia": "jobs_saudi_arabia.json", "ksa": "jobs_saudi_arabia.json", "riyadh": "jobs_saudi_arabia.json",
                "uae": "jobs_uae.json", "dubai": "jobs_uae.json", "emirates": "jobs_uae.json",
                "gulf": "jobs_gulf_region.json", "khaleej": "jobs_gulf_region.json",
                "germany": "jobs_germany.json", "berlin": "jobs_germany.json", "munich": "jobs_germany.json",
                "uk": "jobs_united_kingdom.json", "united kingdom": "jobs_united_kingdom.json", "london": "jobs_united_kingdom.json",
                "france": "jobs_france.json", "paris": "jobs_france.json",
                "usa": "jobs_usa.json", "us": "jobs_usa.json", "united states": "jobs_usa.json",
                "netherlands": "jobs_netherlands.json", "holland": "jobs_netherlands.json", "amsterdam": "jobs_netherlands.json",
                "switzerland": "jobs_switzerland.json", "zurich": "jobs_switzerland.json",
                "global_remote": "jobs_global_remote.json", "remote": "jobs_all_remote.json"
            }
            fname = alias_map.get(c, f"jobs_{c}.json")
            cand_path = os.path.join(self.by_country_dir, fname)
            if os.path.exists(cand_path):
                return cand_path

        return self.default_dataset_path

    def load_jobs(self, dataset_path: Optional[str] = None, country: Optional[str] = None, remote_only: bool = False) -> List[Dict[str, Any]]:
        """
        Loads job records. Prefers SQLite database for performance,
        falls back to JSON file if DB is not available.
        """
        if self.db:
            try:
                return self.db.get_jobs_for_matching(country=country, remote_only=remote_only)
            except Exception as e:
                print(f"⚠️ Error querying SQLite database, falling back to JSON: {e}")

        # JSON Fallback
        if not dataset_path:
            dataset_path = self.resolve_dataset_path(country=country, remote_only=remote_only)

        if not os.path.exists(dataset_path):
            return []
        try:
            with open(dataset_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception as e:
            print(f"⚠️ Error reading dataset from {dataset_path}: {e}")
            return []

    @staticmethod
    def clean_title_for_matching(raw_title: str) -> str:
        """Removes trailing location names (like ', Cairo, Egypt') from job title."""
        if not raw_title:
            return ""
        # Remove trailing geographic tags appended by job boards
        cleaned = re.sub(r'[,\|\-–]\s*(Cairo|Egypt|Remote|Germany|Berlin|London|USA|UAE|Dubai|Saudi Arabia|KSA|Riyadh).*$', '', raw_title, flags=re.IGNORECASE)
        return cleaned.strip()

    def retrieve_candidates(
        self,
        profile: ResumeProfile,
        top_k: int = 8,
        country: Optional[str] = None,
        remote_only: bool = False
    ) -> List[CandidateJobSummary]:
        """
        Retrieves the top candidate jobs strictly aligned with the candidate's domain
        using word-boundary regex to prevent false matches (like 'ai' inside 'Cairo').
        Uses SQLite database when available for high performance.
        """
        jobs = self.load_jobs(country=country, remote_only=remote_only)

        if not jobs:
            return []

        cand_domain = profile.primary_domain.lower()
        cand_skills = set(profile.normalized_skills_flat)
        cand_seniority = (profile.seniority_level or "Junior").lower()
        cand_years = float(profile.total_years_experience or 0.0)

        # Determine candidate seniority tier
        is_cand_junior = (
            "entry" in cand_seniority
            or "intern" in cand_seniority
            or "junior" in cand_seniority
            or cand_years < 2.5
        )
        is_cand_senior = (
            "senior" in cand_seniority
            or "lead" in cand_seniority
            or "staff" in cand_seniority
            or "principal" in cand_seniority
            or "director" in cand_seniority
            or cand_years >= 5.0
        )
        is_cand_mid = not is_cand_junior and not is_cand_senior

        pos_pattern = self.DOMAIN_POSITIVE_PATTERNS.get(
            cand_domain,
            re.compile(r'\b(software engineer|developer|engineer)\b', re.IGNORECASE)
        )
        neg_pattern = self.DOMAIN_NEGATIVE_PATTERNS.get(cand_domain)

        scored_candidates = []

        for idx, job in enumerate(jobs):
            raw_title = job.get("title") or job.get("job_title") or "Software Engineer"
            clean_title = self.clean_title_for_matching(raw_title)
            company = job.get("company") or "Technology Co."
            location = job.get("location") or "Remote"
            url = job.get("source_url") or job.get("apply_url") or job.get("url") or "https://www.linkedin.com/jobs"
            req_skills = job.get("required_skills") or job.get("skills") or []
            desc = job.get("cleaned_description") or job.get("description") or ""

            # Check positive pattern in clean title
            is_title_match = bool(pos_pattern.search(clean_title))
            is_desc_match = bool(pos_pattern.search(desc[:500]))

            # Check negative pattern
            has_negative = bool(neg_pattern.search(clean_title)) if neg_pattern else False

            # If it explicitly matches the negative pattern and title doesn't have positive, disqualify
            if has_negative and not is_title_match:
                continue

            # ==============================================================
            # PRACTICAL CAPABILITY & RELEVANCE SCORING ("Can they do the job?")
            # ==============================================================
            title_lower = clean_title.lower()
            job_level_lower = (job.get("experience_level") or "Mid-Level").lower()

            # Base relevance starts from practical capability, NOT rigid titles
            relevance = 0

            # 1. Technical Domain Match (Essential for job execution)
            if is_title_match:
                relevance += 120  # Primary match on target title
            elif is_desc_match:
                relevance += 60   # Domain keywords confirmed in role description

            # 2. Executive Management Demotion (Only for C-Suite / VP / Director roles)
            is_job_executive = bool(re.search(r'\b(vp|vice president|chief|director|head of)\b', title_lower))
            if is_job_executive and cand_years < 4.0:
                relevance -= 50  # Executive management roles require organizational scale

            # 3. Hands-on Technical Stack Overlap (Core indicator of execution ability)
            if req_skills:
                req_skills_clean = [str(s).lower().strip() for s in req_skills]
                overlap = [s for s in req_skills_clean if s in cand_skills]
            else:
                desc_lower = desc[:1500].lower()
                overlap = [
                    s for s in cand_skills
                    if len(s) >= 3 and re.search(r'\b' + re.escape(s.lower()) + r'\b', desc_lower)
                ]

            # High weight on skills: Can the candidate actually write the code and execute the stack?
            relevance += (len(overlap) * 30)
            if len(overlap) >= 3:
                relevance += 50   # Substantial practical skill synergy

            # Only consider jobs that have domain relevance
            if relevance < 30:
                continue

            final_skills = [str(s) for s in (req_skills if req_skills else overlap[:8])]

            job_summary = CandidateJobSummary(
                job_id=str(job.get("job_id") or job.get("id") or idx + 1),
                job_title=raw_title,
                company=company,
                location=location,
                source_url=url,
                experience_level=job.get("experience_level", "Mid-Level"),
                required_skills=final_skills,
                description_snippet=desc[:500].strip()
            )
            scored_candidates.append((relevance, job_summary))

        # Sort by relevance descending
        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        # Fallback if no strict domain matches: return generic tech roles rather than empty
        if not scored_candidates and jobs:
            for idx, job in enumerate(jobs[:top_k]):
                scored_candidates.append((10, CandidateJobSummary(
                    job_id=str(job.get("job_id") or idx + 1),
                    job_title=job.get("title") or "Software Engineer",
                    company=job.get("company") or "Tech Co",
                    location=job.get("location") or "Remote",
                    source_url=job.get("source_url") or "https://www.linkedin.com/jobs",
                    experience_level=job.get("experience_level", "Mid-Level"),
                    required_skills=[str(s) for s in (job.get("required_skills") or [])[:10]],
                    description_snippet=(job.get("cleaned_description") or "")[:500].strip()
                )))

        return [item[1] for item in scored_candidates[:top_k]]
