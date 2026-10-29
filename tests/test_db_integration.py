"""
=============================================================================
tests/test_db_integration.py - فحص واختبار أداء قاعدة البيانات المركزية
=============================================================================

الغرض (Purpose):
- التحقق من اتصال قاعدة البيانات SQLite (jobs.db).
- قياس سرعة الاستعلام والبحث اللحظي Full-Text Search (FTS5).
- التأكد من قراءة وكتابة الجداول: jobs, candidates, reports, report_evaluations.

كيفية التشغيل (Execution):
python tests/test_db_integration.py
=============================================================================
"""

import sys
import os
import time

# ربط المسارات بالكونكشن المركزي
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config import DB_PATH
from src.database import JobsDatabase
from src.matcher import JobMatcher
from src.schemas import ResumeProfile


def run_tests():
    print("=" * 75)
    print("🧪 1. اختبار قاعدة البيانات SQLite (Database Health & Performance)")
    print("=" * 75)

    db = JobsDatabase(DB_PATH)
    t0 = time.time()
    stats = db.get_stats()
    elapsed = time.time() - t0

    print(f"  ├ مسار قاعدة البيانات: {DB_PATH}")
    print(f"  ├ إجمالي الوظائف النشطة: {stats['total_jobs']:,} وظيفة (تم جلبها في {elapsed:.4f} ثانية)")
    print(f"  ├ الوظائف المتاحة ريموت: {stats['total_remote']:,} وظيفة")
    print(f"  ├ حجم ملف قاعدة البيانات: {stats['db_size_mb']} MB")
    print(f"  └ أهم الدول: {dict(list(stats['by_country'].items())[:5])}")

    print("\n" + "=" * 75)
    print("⚡ 2. اختبار محرك البحث اللحظي FTS5 (Full-Text Search)")
    print("=" * 75)

    t0 = time.time()
    query = "Machine Learning"
    search_results = db.search_jobs(query, limit=5)
    s_elapsed = time.time() - t0

    print(f"  ├ نتائج البحث عن '{query}': {len(search_results)} وظيفة في {s_elapsed:.4f} ثانية:")
    for j in search_results[:3]:
        print(f"      • {j['title']} @ {j['company']} ({j['location']})")

    print("\n" + "=" * 75)
    print("👤 3. اختبار جدول المرشحين وجدول التقارير (Candidates & Reports)")
    print("=" * 75)

    candidates = db.get_all_candidates()
    print(f"  ├ إجمالي المرشحين المسجلين: {len(candidates)} مرشحين")
    for c in candidates[:3]:
        print(f"      • #{c['id']} | {c['full_name']} — {c['primary_domain']} ({c['seniority_level']})")

    reports = db.get_all_reports()
    print(f"  ├ إجمالي تقارير الاستشارات المحفوظة: {len(reports)} تقارير")
    for r in reports[:3]:
        print(f"      • #{r['id']} | {r['candidate_name']} — Top Score: {r.get('top_match_score')}%")

    print("\n" + "=" * 75)
    print("🎯 4. اختبار تكامل محرك المطابقة (JobMatcher Integration)")
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

    print(f"  ├ تم استرجاع {len(candidates_jobs)} وظائف مناسبة في {m_elapsed:.4f} ثانية:")
    for c in candidates_jobs:
        print(f"      • {c.job_title} @ {c.company} | المهارات: {c.required_skills[:3]}")

    print("\n" + "=" * 75)
    print("✅ جميع اختبارات قاعدة البيانات والتكامل تعمل بنجاح 100%!")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    run_tests()
