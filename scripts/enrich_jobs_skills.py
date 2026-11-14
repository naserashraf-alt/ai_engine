"""
=============================================================================
scripts/enrich_jobs_skills.py - Relational Job Skills Extraction & Database Enrichment
=============================================================================

Purpose:
- Scans job titles and descriptions across the database using technical patterns.
- Normalizes extracted skills through the Semantic Skill Ontology.
- Populates relational `skills` and `job_skills` tables in `jobs.db`.
=============================================================================
"""

import os
import sys
import re
import sqlite3
import time
from typing import Set, List, Dict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.skills_ontology import SkillOntology
from config import DB_PATH

# 1. Comprehensive Tech Skills Taxonomy with Word Boundary Regexes
TECH_SKILLS_PATTERNS: Dict[str, re.Pattern] = {
    # Core Languages
    "python": re.compile(r'\b(python|py3|python3)\b', re.IGNORECASE),
    "javascript": re.compile(r'\b(javascript|js|ecmascript)\b', re.IGNORECASE),
    "typescript": re.compile(r'\b(typescript|ts)\b', re.IGNORECASE),
    "java": re.compile(r'\bjava\b(?!script)', re.IGNORECASE),
    "cpp": re.compile(r'\b(c\+\+|cpp)\b', re.IGNORECASE),
    "csharp": re.compile(r'\b(c#|csharp|\.net core|\.net)\b', re.IGNORECASE),
    "go": re.compile(r'\b(golang|go language)\b|\bgo\b(?=\s+(?:developer|backend|engineer))', re.IGNORECASE),
    "rust": re.compile(r'\brust\b', re.IGNORECASE),
    "php": re.compile(r'\bphp\b', re.IGNORECASE),
    "ruby": re.compile(r'\bruby\b', re.IGNORECASE),
    "swift": re.compile(r'\bswift\b', re.IGNORECASE),
    "kotlin": re.compile(r'\bkotlin\b', re.IGNORECASE),
    "dart": re.compile(r'\bdart\b', re.IGNORECASE),
    "sql": re.compile(r'\bsql\b', re.IGNORECASE),
    "r": re.compile(r'\br\s+(?:programming|scripting|studio)\b|\b(?:in|using)\s+r\b', re.IGNORECASE),
    "scala": re.compile(r'\bscala\b', re.IGNORECASE),
    "shell": re.compile(r'\b(bash|shell scripting|sh)\b', re.IGNORECASE),

    # Frontend Frameworks & Libraries
    "react": re.compile(r'\b(react|react\.?js|reactjs)\b', re.IGNORECASE),
    "next.js": re.compile(r'\b(next\.?js|nextjs)\b', re.IGNORECASE),
    "vue.js": re.compile(r'\b(vue|vue\.?js|vuejs)\b', re.IGNORECASE),
    "angular": re.compile(r'\b(angular|angular\.?js|angularjs)\b', re.IGNORECASE),
    "html": re.compile(r'\bhtml5?\b', re.IGNORECASE),
    "css": re.compile(r'\bcss3?\b', re.IGNORECASE),
    "tailwind css": re.compile(r'\b(tailwind|tailwindcss)\b', re.IGNORECASE),
    "redux": re.compile(r'\bredux\b', re.IGNORECASE),

    # Backend Frameworks
    "node.js": re.compile(r'\b(node|node\.?js|nodejs)\b', re.IGNORECASE),
    "express.js": re.compile(r'\b(express|express\.?js|expressjs)\b', re.IGNORECASE),
    "nestjs": re.compile(r'\b(nest|nest\.?js|nestjs)\b', re.IGNORECASE),
    "fastapi": re.compile(r'\bfastapi\b', re.IGNORECASE),
    "django": re.compile(r'\bdjango\b', re.IGNORECASE),
    "flask": re.compile(r'\bflask\b', re.IGNORECASE),
    "spring boot": re.compile(r'\b(spring boot|spring framework|spring)\b', re.IGNORECASE),
    "laravel": re.compile(r'\blaravel\b', re.IGNORECASE),
    "ruby on rails": re.compile(r'\b(rails|ruby on rails)\b', re.IGNORECASE),
    "rest api": re.compile(r'\b(rest|restful|rest api|rest apis)\b', re.IGNORECASE),
    "graphql": re.compile(r'\bgraphql\b', re.IGNORECASE),
    "grpc": re.compile(r'\bgrpc\b', re.IGNORECASE),

    # AI, ML, Data Science & GenAI
    "pytorch": re.compile(r'\b(pytorch|torch)\b', re.IGNORECASE),
    "tensorflow": re.compile(r'\b(tensorflow|tf)\b', re.IGNORECASE),
    "scikit-learn": re.compile(r'\b(scikit-learn|sklearn)\b', re.IGNORECASE),
    "pandas": re.compile(r'\bpandas\b', re.IGNORECASE),
    "numpy": re.compile(r'\bnumpy\b', re.IGNORECASE),
    "machine learning": re.compile(r'\b(machine learning|ml)\b', re.IGNORECASE),
    "deep learning": re.compile(r'\b(deep learning|neural networks|cnn|rnn|lstm)\b', re.IGNORECASE),
    "nlp": re.compile(r'\b(nlp|natural language processing)\b', re.IGNORECASE),
    "computer vision": re.compile(r'\b(computer vision|cv|opencv)\b', re.IGNORECASE),
    "generative ai": re.compile(r'\b(generative ai|genai|llm|llms|large language models|gpt|claude|gemini)\b', re.IGNORECASE),
    "rag": re.compile(r'\b(rag|retrieval augmented generation)\b', re.IGNORECASE),
    "langchain": re.compile(r'\blangchain\b', re.IGNORECASE),
    "llamaindex": re.compile(r'\b(llamaindex|llama-index)\b', re.IGNORECASE),
    "transformers": re.compile(r'\b(transformers|hugging face|huggingface)\b', re.IGNORECASE),
    "mlops": re.compile(r'\b(mlops|kubeflow|mlflow)\b', re.IGNORECASE),

    # Data Engineering & Analytics
    "data engineering": re.compile(r'\bdata engineering\b', re.IGNORECASE),
    "data warehouse": re.compile(r'\b(data warehouse|data warehousing|dwh|data mart)\b', re.IGNORECASE),
    "data modeling": re.compile(r'\b(data model|data modeling|star schema|snowflake schema|dimensional modeling)\b', re.IGNORECASE),
    "dbt": re.compile(r'\b(dbt|data build tool)\b', re.IGNORECASE),
    "elt": re.compile(r'\b(elt|extract transform load|extract load transform)\b', re.IGNORECASE),
    "spark": re.compile(r'\b(spark|pyspark|apache spark)\b', re.IGNORECASE),
    "hadoop": re.compile(r'\bhadoop\b', re.IGNORECASE),
    "airflow": re.compile(r'\b(airflow|apache airflow)\b', re.IGNORECASE),
    "kafka": re.compile(r'\b(kafka|apache kafka)\b', re.IGNORECASE),
    "snowflake": re.compile(r'\bsnowflake\b', re.IGNORECASE),
    "teradata": re.compile(r'\bteradata\b', re.IGNORECASE),
    "databricks": re.compile(r'\bdatabricks\b', re.IGNORECASE),
    "bigquery": re.compile(r'\bbigquery\b', re.IGNORECASE),
    "tableau": re.compile(r'\btableau\b', re.IGNORECASE),
    "power bi": re.compile(r'\b(power bi|powerbi)\b', re.IGNORECASE),
    "etl": re.compile(r'\b(etl|data pipelines?)\b', re.IGNORECASE),

    # Databases & Caching
    "postgresql": re.compile(r'\b(postgresql|postgres|psql)\b', re.IGNORECASE),
    "mysql": re.compile(r'\bmysql\b', re.IGNORECASE),
    "mongodb": re.compile(r'\bmongodb|mongo\b', re.IGNORECASE),
    "redis": re.compile(r'\bredis\b', re.IGNORECASE),
    "elasticsearch": re.compile(r'\b(elasticsearch|elastic search|opensearch)\b', re.IGNORECASE),
    "sqlite": re.compile(r'\bsqlite\b', re.IGNORECASE),
    "cassandra": re.compile(r'\bcassandra\b', re.IGNORECASE),
    "dynamodb": re.compile(r'\bdynamodb\b', re.IGNORECASE),
    "oracle": re.compile(r'\boracle db|oracle database\b', re.IGNORECASE),

    # DevOps, Cloud & Architecture
    "docker": re.compile(r'\bdocker\b', re.IGNORECASE),
    "kubernetes": re.compile(r'\b(kubernetes|k8s)\b', re.IGNORECASE),
    "aws": re.compile(r'\b(aws|amazon web services)\b', re.IGNORECASE),
    "gcp": re.compile(r'\b(gcp|google cloud|google cloud platform)\b', re.IGNORECASE),
    "azure": re.compile(r'\b(azure|microsoft azure)\b', re.IGNORECASE),
    "linux": re.compile(r'\b(linux|ubuntu|debian|centos)\b', re.IGNORECASE),
    "git": re.compile(r'\bgit\b', re.IGNORECASE),
    "github": re.compile(r'\bgithub\b', re.IGNORECASE),
    "gitlab": re.compile(r'\bgitlab\b', re.IGNORECASE),
    "ci/cd": re.compile(r'\b(ci/cd|cicd|continuous integration|github actions|jenkins)\b', re.IGNORECASE),
    "terraform": re.compile(r'\bterraform\b', re.IGNORECASE),
    "ansible": re.compile(r'\bansible\b', re.IGNORECASE),
    "microservices": re.compile(r'\bmicroservices?\b', re.IGNORECASE),
    "agile": re.compile(r'\b(agile|scrum)\b', re.IGNORECASE)
}


def extract_skills_from_text(title: str, description: str) -> List[str]:
    """Extracts deduplicated canonical skills from title and description text."""
    combined = f"{title}\n{description}"
    found_skills: Set[str] = set()

    for canonical_name, pattern in TECH_SKILLS_PATTERNS.items():
        if pattern.search(combined):
            can = SkillOntology.canonicalize(canonical_name)
            found_skills.add(can)

    return sorted(list(found_skills))


def run_enrichment():
    print("=" * 80)
    print("🚀 Starting Skills Extraction & Relational Database Enrichment (jobs.db)")
    print(f"📁 Database Path: {DB_PATH}")
    print("=" * 80)

    start_time = time.time()
    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.execute("PRAGMA journal_mode=WAL")
    cur = conn.cursor()

    # 1. Fetch all jobs
    cur.execute("SELECT id, title, cleaned_description FROM jobs")
    all_jobs = cur.fetchall()
    total_jobs = len(all_jobs)
    print(f"  ├ Total jobs to process: {total_jobs}")

    # Clear existing skills and job_skills
    cur.execute("DELETE FROM job_skills")
    cur.execute("DELETE FROM skills")
    conn.commit()

    # Track skills cache {name_lower: skill_id}
    skill_cache: Dict[str, int] = {}
    job_skills_records = []

    jobs_with_skills_count = 0
    total_skills_assigned = 0

    print("  ├ Scanning texts and extracting canonical technical skills...")
    for idx, (job_id, title, desc) in enumerate(all_jobs):
        extracted_skills = extract_skills_from_text(title or "", desc or "")
        if extracted_skills:
            jobs_with_skills_count += 1
            for sk in extracted_skills:
                sk_lower = sk.lower()
                if sk_lower not in skill_cache:
                    cur.execute("INSERT INTO skills (name, name_lower) VALUES (?, ?)", (sk, sk_lower))
                    skill_id = cur.lastrowid
                    skill_cache[sk_lower] = skill_id
                else:
                    skill_id = skill_cache[sk_lower]

                job_skills_records.append((job_id, skill_id))
                total_skills_assigned += 1

        if (idx + 1) % 500 == 0:
            print(f"  ⏳ Processed {idx + 1}/{total_jobs} jobs...")

    # Bulk insert job_skills
    print(f"  ├ Inserting {len(job_skills_records)} skill relationships into job_skills table...")
    cur.executemany("INSERT OR IGNORE INTO job_skills (job_id, skill_id) VALUES (?, ?)", job_skills_records)
    conn.commit()

    elapsed = round(time.time() - start_time, 2)
    print("\n" + "=" * 80)
    print("✅ Skills Enrichment Complete!")
    print(f"  • Execution Time: {elapsed} seconds")
    print(f"  • Jobs with Extracted Skills: {jobs_with_skills_count} of {total_jobs} ({(jobs_with_skills_count/total_jobs)*100:.1f}%)")
    print(f"  • Unique Technical Skills: {len(skill_cache)}")
    print(f"  • Total Job-Skill Links: {total_skills_assigned}")
    print(f"  • Average Skills Per Job: {total_skills_assigned / max(1, jobs_with_skills_count):.1f} skills")
    print("=" * 80)

    # Show Top 15 in-demand skills in the database
    cur.execute("""
        SELECT s.name, COUNT(js.job_id) as cnt
        FROM skills s
        JOIN job_skills js ON s.id = js.skill_id
        GROUP BY s.name
        ORDER BY cnt DESC
        LIMIT 15
    """)
    top_skills = cur.fetchall()
    print("\n📊 Top 15 In-Demand Skills in Database:")
    for rank, (name, count) in enumerate(top_skills, 1):
        print(f"   {rank:2d}. {name:<20} : {count:4d} jobs")

    conn.close()


if __name__ == "__main__":
    run_enrichment()
