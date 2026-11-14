"""
=============================================================================
src/matcher.py - Advanced Hybrid Job Matcher & SOTA Precision Reranker
=============================================================================

Purpose:
- Ranks and filters active job vacancies with high precision by combining:
  1. Domain Isolation Gating (strict boundary protection against cross-domain noise).
  2. Semantic Skill Graph Ontology with foundational must-have weighting.
  3. Dense Vector Similarity (TF-IDF Cosine Semantic Space).
  4. Reciprocal Rank Fusion (RRF, k=60) for optimal hybrid recall.
  5. Multi-Factor SOTA Precision Reranker to prioritize practical role execution.

Inputs / Outputs:
- Input: `ResumeProfile` object, optional geographic country filter, remote flag.
- Output: Ranked list of `CandidateJobSummary` objects reflecting true execution fit.

Dependencies:
- Calls: src/database.py, src/schemas.py, src/skills_ontology.py
- Imported in: src/api_server.py, app.py, run_agent.py
=============================================================================
"""

import os
import re
import sys
import json
from typing import List, Dict, Any, Optional, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.schemas import ResumeProfile, CandidateJobSummary
from src.skills_ontology import SkillOntology


class JobMatcher:
    """Enterprise-grade Hybrid Job Matcher combining Domain Isolation, Skill Ontology, and Dense Vector Similarity."""

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
            r'\b(data engineer|etl|elt|big data|spark|hadoop|airflow|kafka|data pipeline|snowflake|dbt|data warehouse|data modeling|sql developer|analytics engineer)\b',
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

    # Negative patterns to avoid cross-domain false positives
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
        Executes Advanced Hybrid Retrieval:
        1. Domain Isolation Gating (Regex Word Boundaries).
        2. Skill Graph Ontology Matching (Synergy & Partial Credit).
        3. Semantic Vector Similarity (TF-IDF Cosine Similarity).
        4. Reciprocal Rank Fusion (RRF) to merge Sparse & Dense rankings.
        """
        jobs = self.load_jobs(country=country, remote_only=remote_only)
        if not jobs:
            return []

        cand_domain = profile.primary_domain.lower()
        cand_skills = list(profile.normalized_skills_flat)
        cand_years = float(profile.total_years_experience or 0.0)

        pos_pattern = self.DOMAIN_POSITIVE_PATTERNS.get(
            cand_domain,
            re.compile(r'\b(software engineer|developer|engineer)\b', re.IGNORECASE)
        )
        neg_pattern = self.DOMAIN_NEGATIVE_PATTERNS.get(cand_domain)

        # -------------------------------------------------------------
        # Step 1: Pre-Filter Candidates through Domain Gating
        # -------------------------------------------------------------
        gated_jobs: List[Tuple[int, Dict[str, Any], str, str, List[str], str]] = []

        for idx, job in enumerate(jobs):
            raw_title = job.get("title") or job.get("job_title") or "Software Engineer"
            clean_title = self.clean_title_for_matching(raw_title)
            desc = job.get("cleaned_description") or job.get("description") or ""
            req_skills = job.get("required_skills") or job.get("skills") or []

            # Check positive pattern in clean title or initial description
            is_title_match = bool(pos_pattern.search(clean_title))
            is_desc_match = bool(pos_pattern.search(desc[:500]))

            # Check negative pattern
            has_negative = bool(neg_pattern.search(clean_title)) if neg_pattern else False
            if has_negative and not is_title_match:
                continue

            # Must exhibit basic domain relevance
            if not is_title_match and not is_desc_match:
                continue

            gated_jobs.append((idx, job, raw_title, clean_title, req_skills, desc))

        # Fallback if gating yielded very few jobs
        if len(gated_jobs) < top_k and jobs:
            for idx, job in enumerate(jobs[:top_k * 2]):
                raw_title = job.get("title") or "Software Engineer"
                clean_title = self.clean_title_for_matching(raw_title)
                desc = job.get("cleaned_description") or ""
                req_skills = job.get("required_skills") or []
                gated_jobs.append((idx, job, raw_title, clean_title, req_skills, desc))

        # -------------------------------------------------------------
        # Step 2: Skill Ontology Synergy & Practical Capability Scoring
        # -------------------------------------------------------------
        skill_ranked_list: List[Tuple[float, int, CandidateJobSummary]] = []
        doc_texts: List[str] = []

        for original_idx, job, raw_title, clean_title, req_skills, desc in gated_jobs:
            # If job has no extracted skills in DB, dynamically extract canonical skills from job description
            if not req_skills and desc:
                desc_lower = desc.lower()
                found_req = []
                for alias in SkillOntology.CANONICAL_ALIASES.keys():
                    if len(alias) >= 2 and re.search(r'\b' + re.escape(alias) + r'\b', desc_lower):
                        found_req.append(SkillOntology.canonicalize(alias))
                req_skills = list(dict.fromkeys(found_req))[:12]

            title_lower = clean_title.lower()
            is_title_match = bool(pos_pattern.search(clean_title))

            # Domain relevance score
            domain_score = 120.0 if is_title_match else 60.0

            # Seniority alignment adjustment in candidate retrieval
            is_job_lead = bool(re.search(r'\b(vp|vice president|chief|director|head of|lead|principal|architect|staff)\b', title_lower))
            is_job_senior = bool(re.search(r'\b(senior|sr\.?)\b', title_lower))
            is_job_junior = bool(re.search(r'\b(junior|jr\.?|entry|intern|fresh|associate)\b', title_lower))

            seniority_adj = 0.0
            is_cand_junior = (cand_years <= 2.5) or ("junior" in (profile.seniority_level or "").lower())

            if is_job_lead:
                if is_cand_junior:
                    seniority_adj = -120.0  # Heavy penalty: Juniors should never be matched to Lead/Architect
                elif cand_years < 5.0:
                    seniority_adj = -60.0
            elif is_job_senior:
                if is_cand_junior:
                    seniority_adj = -90.0  # Heavy penalty: Juniors should not match Senior roles
                elif cand_years >= 5.0:
                    seniority_adj = +25.0
            elif is_job_junior:
                if is_cand_junior:
                    seniority_adj = +80.0  # Major boost: prioritize Junior/Entry-Level roles for Junior candidates
                elif cand_years > 5.0:
                    seniority_adj = -30.0

            # Skill Ontology Evaluation (with Core Foundational Skills weighting)
            synergy_res = SkillOntology.evaluate_skill_synergy(cand_skills, req_skills)
            synergy_score = synergy_res["synergy_score"]
            matched_skills = synergy_res["matched_skills"]

            # Practical capability composite score (with richness bonus for comprehensive job postings)
            richness_adj = 25.0 if len(desc) > 300 else -40.0
            capability_score = domain_score + seniority_adj + (synergy_score * 1.5) + richness_adj

            # Build CandidateJobSummary with true job required skills
            company = job.get("company") or "Technology Co."
            location = job.get("location") or "Remote"
            url = job.get("source_url") or job.get("apply_url") or job.get("url") or "https://www.linkedin.com/jobs"

            # Use actual required skills for clarity, fallback to matched or top stack
            display_skills = [str(s) for s in req_skills[:10]] if req_skills else (matched_skills if matched_skills else cand_skills[:5])

            job_summary = CandidateJobSummary(
                job_id=str(job.get("job_id") or job.get("id") or original_idx + 1),
                job_title=raw_title,
                company=company,
                location=location,
                source_url=url,
                experience_level=job.get("experience_level", "Mid-Level"),
                required_skills=display_skills,
                description_snippet=desc[:500].strip()
            )

            # Keep tracking data for stage 2 reranker
            meta_tuple = {
                "synergy_score": synergy_score,
                "domain_match": is_title_match,
                "seniority_adj": seniority_adj,
                "matched_skills": matched_skills
            }
            skill_ranked_list.append((capability_score, len(doc_texts), job_summary, meta_tuple))
            # Text for vector similarity
            doc_texts.append(f"{raw_title} {' '.join(display_skills)} {desc[:600]}")

        # -------------------------------------------------------------
        # Step 3: Semantic Dense Vector Similarity (TF-IDF Cosine Sim)
        # -------------------------------------------------------------
        dense_ranked_indices: List[Tuple[float, int]] = []
        similarity_map: Dict[int, float] = {}
        if doc_texts:
            try:
                candidate_text = f"{profile.primary_domain} {' '.join(cand_skills)} {profile.professional_summary or ''}"
                corpus = [candidate_text] + doc_texts
                vectorizer = TfidfVectorizer(max_features=4000, stop_words="english", ngram_range=(1, 2))
                tfidf_matrix = vectorizer.fit_transform(corpus)

                query_vec = tfidf_matrix[0:1]
                docs_vec = tfidf_matrix[1:]
                similarities = cosine_similarity(query_vec, docs_vec)[0]

                for doc_idx, sim in enumerate(similarities):
                    dense_ranked_indices.append((float(sim), doc_idx))
                    similarity_map[doc_idx] = float(sim)
            except Exception as e:
                # If vectorizer fails gracefully fallback to index order
                for i in range(len(doc_texts)):
                    val = 1.0 - (i * 0.01)
                    dense_ranked_indices.append((val, i))
                    similarity_map[i] = val
        else:
            dense_ranked_indices = []

        # -------------------------------------------------------------
        # Step 4: Reciprocal Rank Fusion (RRF) - Recall Stage
        # -------------------------------------------------------------
        # Rank by skill synergy
        skill_ranked_list.sort(key=lambda x: x[0], reverse=True)
        # Rank by dense similarity
        dense_ranked_indices.sort(key=lambda x: x[0], reverse=True)

        k_rrf = 60.0
        rrf_scores: Dict[int, float] = {}

        for rank_1, (_, doc_idx, _, _) in enumerate(skill_ranked_list):
            rrf_scores[doc_idx] = rrf_scores.get(doc_idx, 0.0) + (1.0 / (k_rrf + rank_1 + 1))

        for rank_2, (_, doc_idx) in enumerate(dense_ranked_indices):
            rrf_scores[doc_idx] = rrf_scores.get(doc_idx, 0.0) + (1.0 / (k_rrf + rank_2 + 1))

        doc_to_item = {doc_idx: (summary, meta) for _, doc_idx, summary, meta in skill_ranked_list}
        sorted_rrf = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        # -------------------------------------------------------------
        # Step 5: Multi-Factor Semantic Reranker - Precision Stage
        # -------------------------------------------------------------
        pool_size = max(top_k * 3, 20)
        top_pool_indices = [doc_idx for doc_idx, _ in sorted_rrf[:pool_size] if doc_idx in doc_to_item]

        reranked_candidates = []
        for doc_idx in top_pool_indices:
            summary, meta = doc_to_item[doc_idx]
            synergy = meta["synergy_score"] / 100.0  # 0.0 to 1.0
            domain_bonus = 1.0 if meta["domain_match"] else 0.5
            vector_sim = similarity_map.get(doc_idx, 0.0)

            # Seniority penalty/bonus normalized (-0.5 to +0.3)
            raw_adj = meta["seniority_adj"]
            seniority_factor = 0.30 if raw_adj > 30 else (-0.60 if raw_adj < -50 else 0.0)
            desc_rich = 0.15 if len(summary.description_snippet) > 200 else -0.30

            # Final Rerank Precision Formula (SOTA Multi-Factor)
            precision_score = (
                0.40 * synergy +
                0.30 * domain_bonus +
                0.15 * min(1.0, max(0.0, vector_sim)) +
                seniority_factor +
                desc_rich
            )
            reranked_candidates.append((precision_score, summary))

        reranked_candidates.sort(key=lambda x: x[0], reverse=True)
        return [summary for _, summary in reranked_candidates[:top_k]]
