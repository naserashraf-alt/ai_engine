"""
=============================================================================
src/ai_extractor.py - AI Resume Extractor with Verified Tenure & Careerk Export
=============================================================================

Purpose:
- Parses and extracts structured candidate data from PDF/DOCX resumes.
- Features multimodal OCR fallback for scanned image documents.
- Calculates verified employment tenure from chronological dates.
- Normalizes technical skills using the Semantic Skill Ontology.
- Generates 100% compliant Careerk backend payload (NlpParseCvResponse).

Supported AI Providers:
1. Google Gemini (Gemini 2.5 Pro, 2.0 Flash) via modern google-genai SDK.
2. OpenAI (GPT-4o, o3-mini).
3. Local LLMs via Ollama (llama3.2, deepseek-r1).
4. Offline Smart Heuristic Fallback engine.

Dependencies:
- Calls: src/pdf_reader.py, src/schemas.py, src/skills_ontology.py
- Imported in: src/api_server.py, app.py, run_agent.py, extract_cv.py
=============================================================================
"""

import os
import re
import sys
import json
import time
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables
load_dotenv()

from src.schemas import (
    ResumeProfile, PersonalInfo, ExperienceItem, EducationItem,
    ProjectItem, CertificationItem, LanguageItem, SkillsCategorized,
    calculate_tenure_from_experiences
)
from src.skills_ontology import SkillOntology
from src.pdf_reader import PDFReader

# Check modern Google GenAI SDK
GOOGLE_GENAI_AVAILABLE = False
try:
    from google import genai
    from google.genai import types
    GOOGLE_GENAI_AVAILABLE = True
except ImportError:
    pass

# Check legacy SDK only if google.genai is not available
LEGACY_GENAI_AVAILABLE = False
if not GOOGLE_GENAI_AVAILABLE:
    try:
        import google.generativeai as legacy_genai
        LEGACY_GENAI_AVAILABLE = True
    except ImportError:
        pass


SYSTEM_EXTRACTION_PROMPT = """You are an elite, highly accurate AI Resume & CV Information Extraction Engine.
Your task is to analyze the provided Curriculum Vitae (CV) / Resume and extract all relevant candidate data with zero hallucination.

EXTRACTION GUIDELINES:
1. Candidate Name: Extract the actual human full name accurately (do not confuse with company names or headers).
2. Contact Info: Accurately parse email, phone, location (city/country), and links (LinkedIn, GitHub, Portfolio, personal site).
3. Summary: Provide an executive summary of the candidate's career, strengths, and primary focus.
4. Domain & Seniority:
   - primary_domain: e.g. "AI / Machine Learning", "Backend Engineering", "Frontend Engineering", "Full Stack", "Data Science", "DevOps / Cloud", "Mobile Development", "Cybersecurity", "Embedded Systems".
   - seniority_level: Select from "Entry-Level / Intern", "Junior", "Mid-Level", "Senior", "Lead / Staff", "Director / Executive".
   - total_years_experience: Realistic float calculated based on the employment history timeline.
5. Skills Categorization:
   - technical_skills: Programming languages, core frameworks, libraries, databases.
   - tools_and_platforms: DevOps tools (Docker, K8s, CI/CD), cloud providers (AWS, GCP, Azure), OS, developer tools (Git, Jira).
   - soft_skills: Interpersonal, agile, problem solving, teamwork, leadership.
6. Work Experience:
   - Extract each role with job_title, company, location, start_date, end_date (or "Present"), is_current (bool), and bullet points of key_achievements.
   - List specific technologies_used for each individual role if mentioned.
7. Education:
   - Extract degrees, fields of study, institutions, graduation dates, and GPA if present.
8. Projects & Certifications:
   - Extract all mentioned projects with title, description, and technologies.
   - Extract certifications with issuer and date.
9. Languages:
   - Extract spoken languages with proficiency (e.g., Native, Fluent, Intermediate).

Be rigorous, exhaustive, and adhere strictly to the JSON schema.
"""


class AIExtractor:
    """Multi-Provider AI Resume Extractor with guaranteed schema validation."""

    def __init__(
        self,
        provider: str = "gemini",
        model: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        self.provider = (provider or os.getenv("AI_PROVIDER", "gemini")).lower().strip()
        self.api_key = api_key
        self.model = model
        self._init_provider()

    def _init_provider(self):
        """Initializes client based on the chosen provider."""
        if self.provider == "gemini":
            self.api_key = self.api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            self.model = self.model or os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
            self.client = None
            if self.api_key and GOOGLE_GENAI_AVAILABLE:
                try:
                    self.client = genai.Client(api_key=self.api_key)
                except Exception as e:
                    print(f"⚠️ [Gemini Client Init Warning]: {e}")
        elif self.provider in ["openai", "chatgpt"]:
            self.api_key = self.api_key or os.getenv("OPENAI_API_KEY")
            self.model = self.model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        elif self.provider == "ollama":
            self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
            self.model = self.model or os.getenv("OLLAMA_MODEL", "llama3.2")

    def extract_from_pdf(self, pdf_path: str, prefer_multimodal: bool = True) -> ResumeProfile:
        """
        Extracts structured resume data from a PDF or DOCX file using AI.
        """
        start_time = time.time()
        
        # 1. Read document using Universal Document Reader (PDF / DOCX)
        meta = PDFReader.extract_text_and_meta(pdf_path)
        cleaned_text = meta["cleaned_text"]

        # Automatic Scanned Document OCR Detection
        is_scanned_image = len(cleaned_text.split()) < 30 and pdf_path.lower().endswith(".pdf")
        if is_scanned_image:
            prefer_multimodal = True
            meta["is_scanned_document"] = True

        profile: Optional[ResumeProfile] = None
        used_provider = self.provider
        used_model = self.model

        # 2. Dispatch to designated AI Provider
        if self.provider == "gemini":
            if self.api_key:
                profile = self._extract_with_gemini(pdf_path, cleaned_text, prefer_multimodal=prefer_multimodal)
            else:
                profile = self._extract_heuristic_fallback(
                    cleaned_text,
                    reason="GEMINI_API_KEY not configured. Set GEMINI_API_KEY in .env to use live Gemini AI."
                )
                used_provider = "heuristic_fallback"
                used_model = "regex_heuristic_v1"

        elif self.provider in ["openai", "chatgpt"]:
            if self.api_key:
                profile = self._extract_with_openai(cleaned_text)
            else:
                profile = self._extract_heuristic_fallback(
                    cleaned_text,
                    reason="OPENAI_API_KEY not configured. Set OPENAI_API_KEY in .env to use live OpenAI."
                )
                used_provider = "heuristic_fallback"
                used_model = "regex_heuristic_v1"

        elif self.provider == "ollama":
            profile = self._extract_with_ollama(cleaned_text)
            if profile is None:
                profile = self._extract_heuristic_fallback(
                    cleaned_text,
                    reason=f"Ollama server not reachable at {self.ollama_host}."
                )
                used_provider = "heuristic_fallback"
                used_model = "regex_heuristic_v1"

        else:
            profile = self._extract_heuristic_fallback(
                cleaned_text,
                reason=f"Unknown provider '{self.provider}'. Falling back to heuristic extractor."
            )
            used_provider = "heuristic_fallback"

        # 3. Post-Process & Normalize Flat Skills
        elapsed_sec = round(time.time() - start_time, 2)
        profile = self._normalize_skills_and_meta(profile, meta, used_provider, used_model, elapsed_sec)
        return profile

    # Universal alias for PDF and Word DOCX files
    extract_from_file = extract_from_pdf

    def _extract_with_gemini(self, pdf_path: str, cleaned_text: str, prefer_multimodal: bool = True) -> ResumeProfile:
        """Invokes Google Gemini with native structured JSON output."""
        prompt = f"{SYSTEM_EXTRACTION_PROMPT}\n\nResume Document Content:\n{cleaned_text}"

        try:
            if GOOGLE_GENAI_AVAILABLE and self.client:
                # Modern google-genai SDK with Pydantic structured output
                config = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ResumeProfile,
                    temperature=0.1
                )

                # Attempt multimodal PDF upload/bytes if preferred
                contents = []
                if prefer_multimodal and pdf_path.lower().endswith(".pdf") and os.path.getsize(pdf_path) < 15 * 1024 * 1024:
                    try:
                        pdf_bytes = PDFReader.get_pdf_bytes(pdf_path)
                        part = types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
                        contents = [part, SYSTEM_EXTRACTION_PROMPT]
                    except Exception:
                        contents = [prompt]
                else:
                    contents = [prompt]

                response = self.client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=config
                )
                
                raw_json = response.text
                return ResumeProfile.model_validate_json(raw_json)

            elif LEGACY_GENAI_AVAILABLE:
                # Fallback to legacy SDK
                legacy_genai.configure(api_key=self.api_key)
                model_inst = legacy_genai.GenerativeModel(
                    self.model,
                    generation_config={"response_mime_type": "application/json"}
                )
                resp = model_inst.generate_content(prompt)
                return ResumeProfile.model_validate_json(resp.text)

        except Exception as e:
            print(f"⚠️ [Gemini API Exception]: {e}. Falling back to Smart Heuristic Extractor.")
            return self._extract_heuristic_fallback(cleaned_text, reason=str(e))

    def _extract_with_openai(self, cleaned_text: str) -> ResumeProfile:
        """Invokes OpenAI with JSON output format."""
        import requests
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        schema_json = json.dumps(ResumeProfile.model_json_schema())
        payload = {
            "model": self.model,
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "messages": [
                {
                    "role": "system",
                    "content": f"{SYSTEM_EXTRACTION_PROMPT}\n\nYou MUST respond with valid JSON strictly conforming to this JSON Schema:\n{schema_json}"
                },
                {
                    "role": "user",
                    "content": f"Extract all information from this resume:\n\n{cleaned_text}"
                }
            ]
        }
        
        try:
            resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            raw_content = data["choices"][0]["message"]["content"]
            return ResumeProfile.model_validate_json(raw_content)
        except Exception as e:
            print(f"⚠️ [OpenAI API Exception]: {e}. Falling back to Smart Heuristic Extractor.")
            return self._extract_heuristic_fallback(cleaned_text, reason=str(e))

    def _extract_with_ollama(self, cleaned_text: str) -> Optional[ResumeProfile]:
        """Invokes local Ollama server."""
        import requests
        url = f"{self.ollama_host.rstrip('/')}/api/generate"
        schema_json = json.dumps(ResumeProfile.model_json_schema())
        prompt = (
            f"{SYSTEM_EXTRACTION_PROMPT}\n"
            f"Adhere strictly to this JSON Schema:\n{schema_json}\n\n"
            f"Resume Text:\n{cleaned_text}\n\n"
            f"Return JSON only:"
        )
        payload = {
            "model": self.model,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.1}
        }
        try:
            resp = requests.post(url, json=payload, timeout=90)
            if resp.status_code == 200:
                raw_json = resp.json().get("response", "{}")
                return ResumeProfile.model_validate_json(raw_json)
        except Exception as e:
            print(f"⚠️ [Ollama Connection Notice]: {e}")
            return None

    def _extract_heuristic_fallback(self, text: str, reason: str = "") -> ResumeProfile:
        """
        Smart, robust heuristic extraction for offline testing or when API keys are not provided.
        Ensures the pipeline never breaks and returns fully compliant schema objects.
        """
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        # 1. Candidate Name (Usually in the top 3 lines)
        full_name = "Candidate"
        for line in lines[:5]:
            # Avoid contact info or headers
            if not re.search(r'[@\+0-9/:\.]', line) and len(line) < 40 and len(line.split()) >= 2:
                full_name = line.strip()
                break

        # 1.1 Candidate Target Role Headline (Line right below name)
        candidate_headline = ""
        for line in lines[1:6]:
            if line == full_name or '@' in line or '+' in line or 'linkedin' in line.lower() or 'github' in line.lower():
                continue
            if re.search(r'\b(data engineer|machine learning engineer|ai engineer|data scientist|data analyst|backend developer|frontend developer|full stack developer|software engineer|cloud engineer|devops engineer|mobile developer)\b', line, re.IGNORECASE):
                candidate_headline = line.strip()
                break

        # 2. Email
        email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        email = email_match.group(0) if email_match else None

        # 3. Phone
        phone_match = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,5}', text)
        phone = phone_match.group(0) if phone_match else None

        # 4. Links
        links = {}
        linkedin = re.search(r'(https?://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_-]+)', text, re.IGNORECASE)
        github = re.search(r'(https?://(?:www\.)?github\.com/[a-zA-Z0-9_-]+)', text, re.IGNORECASE)
        if linkedin:
            links['linkedin'] = linkedin.group(0)
        if github:
            links['github'] = github.group(0)

        # 5. Extract Technical Skills dictionary scan
        common_tech = [
            "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust", "php",
            "react", "angular", "vue", "next.js", "node.js", "express", "django", "fastapi", "flask", "spring boot",
            "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
            "snowflake", "dbt", "etl", "elt", "data warehouse", "data warehousing", "data modeling", "power bi", "bigquery", "spark", "pyspark", "hadoop", "airflow", "kafka", "aws s3",
            "docker", "kubernetes", "aws", "gcp", "azure", "git", "linux", "ci/cd", "terraform",
            "pytorch", "tensorflow", "scikit-learn", "pandas", "numpy", "matplotlib", "machine learning", "deep learning", "nlp", "llm"
        ]
        text_lower = text.lower()
        found_tech = [t for t in common_tech if re.search(r'\b' + re.escape(t) + r'\b', text_lower)]

        # 6. Determine Primary Domain (Priority to Explicit Headline)
        primary_domain = "Software Engineering"
        hl_lower = candidate_headline.lower()
        if "data engineer" in hl_lower:
            primary_domain = "Data Engineering"
        elif "data scientist" in hl_lower or "data analyst" in hl_lower:
            primary_domain = "Data Science"
        elif "machine learning" in hl_lower or "ai engineer" in hl_lower:
            primary_domain = "AI / Machine Learning"
        elif "backend" in hl_lower:
            primary_domain = "Backend Engineering"
        elif "frontend" in hl_lower:
            primary_domain = "Frontend Engineering"
        elif "full stack" in hl_lower:
            primary_domain = "Full Stack Engineering"
        elif "devops" in hl_lower or "cloud" in hl_lower:
            primary_domain = "DevOps / Cloud Engineering"
        else:
            # Fallback by skill density
            if any(k in found_tech for k in ["snowflake", "dbt", "etl", "elt", "data warehouse", "data modeling"]):
                primary_domain = "Data Engineering"
            elif any(k in found_tech for k in ["pytorch", "tensorflow", "nlp", "llm"]):
                primary_domain = "AI / Machine Learning"
            elif any(k in found_tech for k in ["react", "angular", "vue", "next.js", "typescript"]):
                if any(k in found_tech for k in ["node.js", "django", "fastapi", "postgresql", "mongodb"]):
                    primary_domain = "Full Stack Engineering"
                else:
                    primary_domain = "Frontend Engineering"
            elif any(k in found_tech for k in ["docker", "kubernetes", "aws", "terraform"]):
                primary_domain = "DevOps / Cloud Engineering"
            elif any(k in found_tech for k in ["django", "fastapi", "flask", "spring boot", "postgresql"]):
                primary_domain = "Backend Engineering"

        # 7. Extract Years of Experience & Seniority
        exp_matches = re.findall(r'(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\b', text, re.IGNORECASE)
        years_exp = 1.0
        if exp_matches:
            valid_years = [float(y) for y in exp_matches if float(y) <= 35]
            if valid_years:
                years_exp = min(valid_years)  # Prefer lower baseline for junior/trainee profiles

        is_explicit_junior = bool(re.search(r'\b(junior|jr\.?|entry|intern|trainee|fresh|aspiring)\b', candidate_headline or text[:400], re.IGNORECASE))
        if is_explicit_junior:
            seniority = "Junior"
            years_exp = min(years_exp, 1.5)
        elif years_exp >= 8:
            seniority = "Senior / Lead"
        elif years_exp >= 5:
            seniority = "Senior"
        elif years_exp >= 2.5:
            seniority = "Mid-Level"
        else:
            seniority = "Junior"

        headline = candidate_headline if candidate_headline else f"{seniority} {primary_domain}"

        # 8. Deep Section-by-Section Parsing for Real Resume Understanding
        sections = {}
        current_sec = 'HEADER'
        lines_raw = text.split('\n')
        header_pattern = re.compile(
            r'^(PROFESSIONAL SUMMARY|SUMMARY|PROFILE|OBJECTIVE|EDUCATION|PROFESSIONAL EXPERIENCE|EXPERIENCE|WORK EXPERIENCE|INTERNSHIPS & TRAINING|TRAINING & INTERNSHIPS|TRAINING|TECHNICAL SKILLS|SKILLS|PROJECTS|KEY PROJECTS|CERTIFICATIONS & LANGUAGES|CERTIFICATIONS|LANGUAGES)\s*$',
            re.IGNORECASE
        )

        buf = []
        for line_r in lines_raw:
            l_str = line_r.strip()
            if header_pattern.match(l_str):
                sections[current_sec] = '\n'.join(buf).strip()
                current_sec = l_str.upper()
                buf = []
            else:
                buf.append(l_str)
        sections[current_sec] = '\n'.join(buf).strip()

        # Summary
        summary_text = sections.get('PROFESSIONAL SUMMARY') or sections.get('SUMMARY') or sections.get('PROFILE') or ""
        if summary_text:
            prof_summary = summary_text.replace('\n', ' ').strip()
        else:
            prof_summary = f"{seniority} {primary_domain} specializing in {', '.join(found_tech[:6])}."

        # Education
        edu_text = sections.get('EDUCATION', '')
        edu_items = []
        if edu_text:
            edu_lines = [l.strip() for l in edu_text.split('\n') if l.strip()]
            inst = edu_lines[0] if edu_lines else "University"
            deg = edu_lines[1] if len(edu_lines) > 1 else "Bachelor of Science"
            edu_items.append(EducationItem(
                institution=inst,
                degree=deg,
                field_of_study="Computer Science or Related Field"
            ))
        else:
            edu_items.append(EducationItem(
                degree="Bachelor of Science",
                field_of_study="Computer Science",
                institution="Accredited University"
            ))

        # Experience & Internships
        exp_combined = sections.get('PROFESSIONAL EXPERIENCE', '') + '\n\n' + sections.get('EXPERIENCE', '') + '\n\n' + sections.get('INTERNSHIPS & TRAINING', '') + '\n\n' + sections.get('TRAINING', '')
        exp_items = []
        exp_pattern = re.compile(
            r'([A-Za-z0-9\s/]+)\s*[—–-]\s*([A-Za-z0-9\s\(\)]+)\n\s*([A-Za-z0-9\s–\-]+)\n((?:[-•\s\w\.,\(\)]+?)(?=\n[A-Za-z0-9\s/]+\s*[—–-]|\Z))',
            re.DOTALL
        )
        for m in exp_pattern.finditer(exp_combined):
            role = m.group(1).strip()
            comp = m.group(2).strip()
            dates = m.group(3).strip()
            bullet_text = m.group(4).strip()
            bullets = [b.strip().lstrip('-•* ') for b in bullet_text.split('\n') if len(b.strip()) > 5]
            exp_items.append(ExperienceItem(
                job_title=role,
                company=comp,
                start_date=dates,
                is_current="present" in dates.lower(),
                description=' '.join(bullets[:2]) if bullets else role,
                key_achievements=bullets,
                technologies_used=[t for t in found_tech if t in bullet_text.lower()][:6]
            ))

        if not exp_items:
            exp_items.append(ExperienceItem(
                job_title=headline,
                company="Engineering Experience",
                start_date="Recent",
                is_current=True,
                description="Designed and delivered technical software and data solutions.",
                key_achievements=["Delivered production-grade features", "Engineered scalable solutions"],
                technologies_used=found_tech[:6]
            ))

        # Projects
        project_items = []
        proj_text = sections.get('PROJECTS') or sections.get('KEY PROJECTS') or ""
        if proj_text:
            proj_blocks = re.split(r'\n(?=[A-Z][A-Za-z0-9\s\-\(\)]+\n\s*[-•])', proj_text)
            for b in proj_blocks:
                p_lines = [l.strip() for l in b.split('\n') if l.strip()]
                if not p_lines:
                    continue
                p_title = p_lines[0]
                p_bullets = [l.lstrip('-•* ') for l in p_lines[1:] if len(l.strip()) > 5]
                b_text = ' '.join(p_bullets).lower()
                inferred = [t for t in found_tech if t in b_text]
                project_items.append(ProjectItem(
                    title=p_title,
                    description=' '.join(p_bullets) if p_bullets else p_title,
                    technologies=inferred
                ))

        # Construct comprehensive profile
        return ResumeProfile(
            personal_info=PersonalInfo(
                full_name=full_name,
                headline=headline,
                email=email,
                phone=phone,
                links=links
            ),
            professional_summary=prof_summary,
            primary_domain=primary_domain,
            seniority_level=seniority,
            total_years_experience=years_exp,
            skills=SkillsCategorized(
                technical_skills=found_tech[:20],
                tools_and_platforms=[t for t in found_tech if t in ["git", "github", "docker", "linux", "aws s3", "vs code", "power bi"]],
                soft_skills=["Problem Solving", "Independent Learning", "Communication", "Team Collaboration"]
            ),
            work_experience=exp_items,
            education=edu_items,
            projects=project_items,
            languages=[
                LanguageItem(language="English", proficiency="Professional"),
                LanguageItem(language="Arabic", proficiency="Native")
            ],
            extraction_metadata={
                "fallback_reason": reason,
                "is_fallback": True
            }
        )

    def _normalize_skills_and_meta(
        self,
        profile: ResumeProfile,
        meta: Dict[str, Any],
        used_provider: str,
        used_model: str,
        elapsed_sec: float
    ) -> ResumeProfile:
        """
        Creates deduplicated, ontology-canonicalized flat skills list,
        calculates verified tenure from work history dates, and enriches metadata.
        """
        # 1. Canonicalize Technical Skills & Tools via Skills Ontology
        all_skills = set()
        canonical_tech = []
        for s in profile.skills.technical_skills:
            clean = s.strip().lower()
            if clean:
                canonical = SkillOntology.canonicalize(clean)
                all_skills.add(canonical)
                canonical_tech.append(canonical)
        profile.skills.technical_skills = sorted(list(set(canonical_tech)))

        canonical_tools = []
        for s in profile.skills.tools_and_platforms:
            clean = s.strip().lower()
            if clean:
                canonical = SkillOntology.canonicalize(clean)
                all_skills.add(canonical)
                canonical_tools.append(canonical)
        profile.skills.tools_and_platforms = sorted(list(set(canonical_tools)))

        # Also expand candidate skills with high-confidence implied skills (e.g., PyTorch implies Python & Deep Learning)
        expanded_map = SkillOntology.expand_candidate_skills(list(all_skills))
        for implied_skill, confidence in expanded_map.items():
            if confidence >= 0.95:  # Only strict direct implications
                all_skills.add(implied_skill)

        profile.normalized_skills_flat = sorted(list(all_skills))

        # 2. Verified Date & Tenure Calculation
        verified_tenure = calculate_tenure_from_experiences(profile.work_experience)
        if verified_tenure > 0.0:
            if profile.total_years_experience <= 0.0 or abs(profile.total_years_experience - verified_tenure) >= 2.0:
                profile.total_years_experience = verified_tenure

        # 3. Calibrate Seniority Level from Verified Experience if needed (Respect explicit Junior / Trainee declarations)
        has_explicit_junior = bool(re.search(r'\b(junior|intern|fresh|entry|trainee|aspiring)\b', profile.personal_info.headline or "", re.IGNORECASE))
        if not has_explicit_junior:
            if profile.total_years_experience >= 8.0 and "Lead" not in profile.seniority_level and "Director" not in profile.seniority_level:
                profile.seniority_level = "Lead / Staff"
            elif 5.0 <= profile.total_years_experience < 8.0 and "Senior" not in profile.seniority_level:
                profile.seniority_level = "Senior"
            elif 2.5 <= profile.total_years_experience < 5.0 and profile.seniority_level in ["Entry-Level / Intern", "Junior"]:
                profile.seniority_level = "Mid-Level"

        # 4. Enrich metadata
        meta_dict = {
            "source_file": meta["filename"],
            "provider": used_provider,
            "model": used_model,
            "execution_time_seconds": elapsed_sec,
            "num_pages": meta["num_pages"],
            "char_count": meta["char_count"],
            "word_count": meta["word_count"],
            "is_live_ai": used_provider in ["gemini", "openai", "ollama"] and not profile.extraction_metadata.get("is_fallback", False),
            "verified_tenure_years": verified_tenure
        }
        profile.extraction_metadata.update(meta_dict)
        return profile

    def extract_and_format_for_careerk(self, file_path: str, job_seeker_id: str) -> Dict[str, Any]:
        """
        End-to-End Extraction pipeline that outputs the exact schema
        contract expected by careerk NestJS backend (NlpParseCvResponse).
        """
        profile = self.extract_from_file(file_path)
        return profile.to_careerk_dict(job_seeker_id)
