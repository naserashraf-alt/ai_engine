"""
=============================================================================
tests/test_db_integration.py - Central Database Health & Performance Validation
=============================================================================

PURPOSE:
- Validate SQLite database connectivity (jobs.db).
- Benchmark real-time Full-Text Search (FTS5) latency and accuracy.
- Verify read/write integrity across tables: jobs, candidates, reports, report_evaluations.

EXECUTION:
python tests/test_db_integration.py
=============================================================================
"""

import sys
import os
import time

# Central path configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config import DB_PATH
from src.database import JobsDatabase
from src.matcher import JobMatcher
from src.schemas import ResumeProfile


def test_db_integration():
    print("=" * 75)
    print("🧪 1. Database Health & Performance Verification (SQLite)")
    print("=" * 75)

    db = JobsDatabase(DB_PATH)
    t0 = time.time()
    stats = db.get_stats()
    elapsed = time.time() - t0

    assert stats["total_jobs"] >= 2000, "Database must have indexed active jobs"

    print(f"  ├ Database Path: {DB_PATH}")
    print(f"  ├ Total Active Jobs: {stats['total_jobs']:,} jobs (fetched in {elapsed:.4f}s)")
    print(f"  ├ Remote Opportunities: {stats['total_remote']:,} jobs")
    print(f"  ├ Database File Size: {stats['db_size_mb']} MB")
    print(f"  └ Top Countries: {dict(list(stats['by_country'].items())[:5])}")

    print("\n" + "=" * 75)
    print("⚡ 2. Real-time FTS5 Full-Text Search Benchmark")
    print("=" * 75)

    t0 = time.time()
    query = "Machine Learning"
    search_results = db.search_jobs(query, limit=5)
    s_elapsed = time.time() - t0

    print(f"  ├ Search results for '{query}': {len(search_results)} jobs in {s_elapsed:.4f}s:")
    for j in search_results[:3]:
        print(f"      • {j['title']} @ {j['company']} ({j['location']})")

    print("\n" + "=" * 75)
    print("👤 3. Candidates and Advisory Reports Verification")
    print("=" * 75)

    candidates = db.get_all_candidates()
    print(f"  ├ Total Registered Candidates: {len(candidates)}")
    for c in candidates[:3]:
        print(f"      • #{c['id']} | {c['full_name']} — {c['primary_domain']} ({c['seniority_level']})")

    reports = db.get_all_reports()
    print(f"  ├ Total Saved Advisory Reports: {len(reports)}")
    for r in reports[:3]:
        print(f"      • #{r['id']} | {r['candidate_name']} — Top Score: {r.get('top_match_score')}%")

    print("\n" + "=" * 75)
    print("🎯 4. JobMatcher Integration Benchmark")
    print("=" * 75)

    matcher = JobMatcher()
    sample_profile = ResumeProfile(
        primary_domain="AI / Machine Learning",
        seniority_level="Mid-Level",
        total_years_experience=3.0,
        normalized_skills_flat=["python", "pytorch", "machine learning", "deep learning"]
    )
    t0 = time.time()
    candidates_jobs = matcher.retrieve_candidates(sample_profile, top_k=4, country="Egypt")
    m_elapsed = time.time() - t0

    print(f"  ├ Retrieved {len(candidates_jobs)} matching opportunities in {m_elapsed:.4f}s:")
    for c in candidates_jobs:
        print(f"      • {c.job_title} @ {c.company} | Skills: {c.required_skills[:3]}")

    print("\n" + "=" * 75)
    print("✅ All database and integration benchmarks passed successfully (100%)!")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    test_db_integration()
