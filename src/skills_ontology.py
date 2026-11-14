"""
=============================================================================
src/skills_ontology.py - Semantic Skill Graph Ontology & Relationship Matrix
=============================================================================

Purpose:
- Comprehensive semantic taxonomy and ontology graph for software engineering,
  data science, and artificial intelligence skills.
- Canonical alias normalization (e.g. 'js' -> 'javascript', 'ts' -> 'typescript').
- Hierarchical skill implication (e.g. PyTorch implies Python & Deep Learning).
- Sibling / substitute skill transferability scoring (e.g. PostgreSQL <-> MySQL).
- Foundational must-have weighting for core programming languages and frameworks.

Outputs:
- Cumulative Skill Synergy Score (0.0 to 100.0).
- Exact, implied, and transferable skill matches.
- Actionable missing skill gaps.
=============================================================================
"""

import re
from typing import List, Dict, Set, Tuple, Any, Optional


class SkillOntology:
    """Enterprise-grade Technical Skill Ontology and Semantic Graph."""

    # 1. Canonical Aliases (Synonyms -> Standard Canonical Name)
    CANONICAL_ALIASES: Dict[str, str] = {
        # Programming Languages
        "js": "javascript",
        "ecmascript": "javascript",
        "ts": "typescript",
        "py": "python",
        "python3": "python",
        "golang": "go",
        "c++": "cpp",
        "c#": "csharp",
        ".net": "dotnet",
        "dotnet core": "dotnet",
        "asp.net": "dotnet",

        # Frontend
        "react": "react",
        "react.js": "react",
        "reactjs": "react",
        "next": "next.js",
        "next.js": "next.js",
        "nextjs": "next.js",
        "vue": "vue.js",
        "vue.js": "vue.js",
        "vuejs": "vue.js",
        "angular": "angular",
        "angular.js": "angular",
        "angularjs": "angular",
        "tailwind": "tailwind css",
        "tailwindcss": "tailwind css",

        # Backend
        "node": "node.js",
        "node.js": "node.js",
        "nodejs": "node.js",
        "express": "express.js",
        "express.js": "express.js",
        "expressjs": "express.js",
        "fastapi": "fastapi",
        "fast api": "fastapi",
        "django": "django",
        "drf": "django rest framework",
        "flask": "flask",
        "spring": "spring boot",
        "springboot": "spring boot",
        "spring boot": "spring boot",

        # AI / ML / Data Science
        "ml": "machine learning",
        "machine learning": "machine learning",
        "dl": "deep learning",
        "deep learning": "deep learning",
        "ai": "artificial intelligence",
        "artificial intelligence": "artificial intelligence",
        "nlp": "nlp",
        "natural language processing": "nlp",
        "cv": "computer vision",
        "computer vision": "computer vision",
        "llm": "generative ai",
        "llms": "generative ai",
        "genai": "generative ai",
        "generative ai": "generative ai",
        "large language models": "generative ai",
        "rag": "rag",
        "retrieval augmented generation": "rag",
        "tf": "tensorflow",
        "tensorflow": "tensorflow",
        "torch": "pytorch",
        "pytorch": "pytorch",
        "sklearn": "scikit-learn",
        "scikit-learn": "scikit-learn",
        "xgboost": "xgboost",
        "lightgbm": "lightgbm",
        "pandas": "pandas",
        "numpy": "numpy",
        "opencv": "opencv",
        "huggingface": "hugging face",
        "hugging face": "hugging face",
        "transformers": "transformers",

        # DevOps / Cloud
        "k8s": "kubernetes",
        "kubernetes": "kubernetes",
        "docker": "docker",
        "docker-compose": "docker",
        "aws": "aws",
        "amazon web services": "aws",
        "gcp": "gcp",
        "google cloud": "gcp",
        "google cloud platform": "gcp",
        "azure": "azure",
        "microsoft azure": "azure",
        "ci/cd": "ci/cd",
        "cicd": "ci/cd",
        "github actions": "github actions",
        "terraform": "terraform",

        # Databases
        "postgres": "postgresql",
        "postgresql": "postgresql",
        "mysql": "mysql",
        "mongo": "mongodb",
        "mongodb": "mongodb",
        "redis": "redis",
        "elasticsearch": "elasticsearch",
        "elastic search": "elasticsearch",

        # Data Engineering & Analytics
        "snowflake": "snowflake",
        "teradata": "teradata",
        "dbt": "dbt",
        "etl": "etl",
        "elt": "elt",
        "data warehousing": "data warehouse",
        "data warehouse": "data warehouse",
        "data modeling": "data modeling",
        "data model": "data modeling",
        "powerbi": "power bi",
        "power bi": "power bi",
        "spark": "apache spark",
        "apache spark": "apache spark",
        "pyspark": "apache spark",
        "airflow": "apache airflow",
        "apache airflow": "apache airflow",
        "kafka": "apache kafka",
        "apache kafka": "apache kafka",
        "bigquery": "bigquery",
        "google bigquery": "bigquery",
        "redshift": "amazon redshift",
        "aws redshift": "amazon redshift",
        "s3": "aws s3",
        "aws s3": "aws s3"
    }

    # 2. Hierarchical Implications (Child Skill -> Parent/Foundational Skills Implied)
    IMPLIED_SKILLS: Dict[str, List[str]] = {
        "dbt": ["sql", "data warehouse", "elt"],
        "snowflake": ["sql", "data warehouse", "cloud data"],
        "elt": ["sql", "data engineering"],
        "etl": ["sql", "data engineering"],
        "apache spark": ["python", "data engineering", "big data"],
        "apache airflow": ["python", "data engineering", "orchestration"],
        "power bi": ["data analysis", "sql", "business intelligence"],
        "pytorch": ["python", "deep learning", "machine learning"],
        "tensorflow": ["python", "deep learning", "machine learning"],
        "keras": ["python", "deep learning"],
        "scikit-learn": ["python", "machine learning", "data science"],
        "xgboost": ["python", "machine learning"],
        "opencv": ["computer vision", "python"],
        "transformers": ["generative ai", "nlp", "deep learning", "python"],
        "rag": ["generative ai", "nlp", "vector databases", "python"],
        "fastapi": ["python", "rest api", "backend"],
        "django": ["python", "backend", "web development"],
        "flask": ["python", "backend", "rest api"],
        "express.js": ["node.js", "javascript", "backend"],
        "nest.js": ["node.js", "typescript", "backend"],
        "spring boot": ["java", "backend", "rest api"],
        "next.js": ["react", "javascript", "typescript", "frontend"],
        "vue.js": ["javascript", "frontend"],
        "angular": ["typescript", "javascript", "frontend"],
        "kubernetes": ["docker", "devops", "cloud computing"],
        "terraform": ["devops", "cloud computing", "infrastructure as code"],
        "airflow": ["python", "etl", "data engineering"],
        "spark": ["big data", "data engineering", "python"],
        "dbt": ["sql", "data engineering", "analytics engineering"],
        "snowflake": ["sql", "data warehouse", "cloud computing"]
    }

    # 3. Sibling Skills with Substitution / Similarity Factor (0.0 to 1.0)
    SIBLING_RELATIONS: Dict[str, Dict[str, float]] = {
        "pytorch": {"tensorflow": 0.85, "keras": 0.75, "jax": 0.70},
        "tensorflow": {"pytorch": 0.85, "keras": 0.85, "jax": 0.70},
        "fastapi": {"flask": 0.80, "django": 0.70, "express.js": 0.60},
        "flask": {"fastapi": 0.80, "django": 0.75},
        "django": {"fastapi": 0.70, "flask": 0.75},
        "react": {"vue.js": 0.75, "angular": 0.70, "svelte": 0.70},
        "vue.js": {"react": 0.75, "angular": 0.70},
        "angular": {"react": 0.70, "vue.js": 0.70},
        "postgresql": {"mysql": 0.85, "mariadb": 0.90, "sqlite": 0.75, "oracle": 0.65},
        "mysql": {"postgresql": 0.85, "mariadb": 0.95, "sqlite": 0.75},
        "mongodb": {"dynamodb": 0.75, "cassandra": 0.70, "couchdb": 0.80},
        "aws": {"gcp": 0.80, "azure": 0.80},
        "gcp": {"aws": 0.80, "azure": 0.75},
        "azure": {"aws": 0.80, "gcp": 0.75},
        "docker": {"podman": 0.90, "containerd": 0.85},
        "kubernetes": {"docker swarm": 0.70, "nomad": 0.65},
        "snowflake": {"bigquery": 0.85, "amazon redshift": 0.85, "databricks": 0.80},
        "dbt": {"apache airflow": 0.75, "apache spark": 0.70},
        "etl": {"elt": 0.95, "data pipeline": 0.90},
        "elt": {"etl": 0.95, "data pipeline": 0.90},
        "power bi": {"tableau": 0.85, "looker": 0.80}
    }

    # 4. Core Foundational Skills (Must-Have Priority Weight = 2.0x)
    CORE_FOUNDATIONAL_SKILLS: Set[str] = {
        "python", "javascript", "typescript", "java", "cpp", "csharp", "go", "rust",
        "react", "angular", "vue.js", "next.js",
        "fastapi", "django", "node.js", "spring boot", "express.js", "nestjs",
        "sql", "postgresql", "mysql", "mongodb", "snowflake", "dbt", "etl", "elt", "data warehouse",
        "pytorch", "tensorflow", "machine learning", "deep learning", "generative ai",
        "docker", "kubernetes", "aws", "gcp", "azure", "linux"
    }

    @classmethod
    def canonicalize(cls, skill: str) -> str:
        """Normalizes any skill variant into its standard canonical representation."""
        if not skill:
            return ""
        clean = skill.strip().lower()
        # Remove version numbers like python 3.10 -> python, angular 16 -> angular
        clean = re.sub(r'\s+v?\d+(?:\.\d+)*$', '', clean).strip()
        return cls.CANONICAL_ALIASES.get(clean, clean)

    @classmethod
    def expand_candidate_skills(cls, skills: List[str]) -> Dict[str, float]:
        """
        Expands a candidate's skill set with implied capabilities.
        Returns a dictionary mapping {skill: confidence_weight (0.0 to 1.0)}.
        """
        profile: Dict[str, float] = {}

        # 1. Direct skills (Weight 1.0)
        for s in skills:
            can = cls.canonicalize(s)
            if can:
                profile[can] = 1.0

        # 2. Implied skills (Weight 0.85)
        for s in list(profile.keys()):
            implied_list = cls.IMPLIED_SKILLS.get(s, [])
            for imp in implied_list:
                can_imp = cls.canonicalize(imp)
                if can_imp not in profile:
                    profile[can_imp] = 0.85

        return profile

    @classmethod
    def evaluate_skill_synergy(
        cls,
        candidate_skills: List[str],
        required_skills: List[str]
    ) -> Dict[str, Any]:
        """
        Calculates the semantic synergy score between candidate skills and required skills.

        Returns:
            - synergy_score: float (0.0 - 100.0)
            - matched_skills: List[str]
            - missing_skills: List[str]
            - details: List[Dict[str, Any]] (Breakdown of each required skill)
        """
        if not required_skills:
            return {
                "synergy_score": 60.0,
                "matched_skills": candidate_skills[:4],
                "missing_skills": [],
                "details": []
            }

        expanded_profile = cls.expand_candidate_skills(candidate_skills)
        matched = []
        missing = []
        breakdown = []
        total_credit = 0.0
        total_weight = 0.0

        for req in required_skills:
            can_req = cls.canonicalize(req)
            credit = 0.0
            match_type = "missing"
            supporting_skill = None
            # Weight: Core foundational skills (e.g. Python, SQL, React) are weighted 2.0x
            skill_weight = 2.0 if can_req in cls.CORE_FOUNDATIONAL_SKILLS else 1.0

            # 1. Direct Exact Match
            if can_req in expanded_profile and expanded_profile[can_req] == 1.0:
                credit = 1.0
                match_type = "exact"
                supporting_skill = can_req
                matched.append(can_req)

            # 2. Hierarchically Implied Match
            elif can_req in expanded_profile:
                credit = expanded_profile[can_req]  # 0.85
                match_type = "implied"
                supporting_skill = f"derived from advanced stack"
                matched.append(f"{can_req} (implied)")

            # 3. Sibling / Substitute Skill Match
            else:
                siblings = cls.SIBLING_RELATIONS.get(can_req, {})
                best_sub_credit = 0.0
                best_sub_name = None
                for sib_name, sib_sim in siblings.items():
                    if sib_name in expanded_profile:
                        effective_credit = sib_sim * expanded_profile[sib_name]
                        if effective_credit > best_sub_credit:
                            best_sub_credit = effective_credit
                            best_sub_name = sib_name

                if best_sub_credit >= 0.65:
                    credit = best_sub_credit
                    match_type = "sibling_transfer"
                    supporting_skill = f"transferable from {best_sub_name} ({int(best_sub_credit*100)}%)"
                    matched.append(f"{can_req} (~{best_sub_name})")
                else:
                    missing.append(can_req)

            total_credit += (credit * skill_weight)
            total_weight += skill_weight
            breakdown.append({
                "required_skill": can_req,
                "match_type": match_type,
                "credit": round(credit, 2),
                "is_core_skill": skill_weight > 1.0,
                "supporting_skill": supporting_skill
            })

        synergy_score = round((total_credit / max(1.0, total_weight)) * 100.0, 1)

        return {
            "synergy_score": min(100.0, synergy_score),
            "matched_skills": list(dict.fromkeys(matched)),
            "missing_skills": list(dict.fromkeys(missing)),
            "details": breakdown
        }
