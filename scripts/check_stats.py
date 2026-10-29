"""
=============================================================================
scripts/check_stats.py - فحص شامل لإحصائيات قاعدة البيانات والوظائف
=============================================================================

الغرض (Purpose):
- يعرض إحصائيات سريعة وشاملة عن قاعدة البيانات المركزية SQLite (jobs.db).
- يوضح توزيع الوظائف حسب الدول، مصادر السحب، ونسب العمل عن بُعد.

كيفية التشغيل (Execution):
python scripts/check_stats.py
=============================================================================
"""

import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from config import DB_PATH
from src.database import JobsDatabase


def main():
    print("=" * 75)
    print("📊 إحصائيات قاعدة البيانات والوظائف النشطة (Database Analytics Report)")
    print("=" * 75)

    if not os.path.exists(DB_PATH):
        print(f"❌ لم يتم العثور على قاعدة البيانات في: {DB_PATH}")
        return

    db = JobsDatabase(DB_PATH)
    stats = db.get_stats()

    print(f"  ├ مسار قاعدة البيانات: {DB_PATH}")
    print(f"  ├ إجمالي الوظائف النشطة: {stats['total_jobs']:,} وظيفة")
    print(f"  ├ الوظائف المتاحة عن بُعد (Remote): {stats['total_remote']:,} وظيفة")
    print(f"  ├ الوظائف الميدانية (On-site): {stats['total_onsite']:,} وظيفة")
    print(f"  ├ عدد الشركات المسجلة: {stats['unique_companies']:,} شركة")
    print(f"  ├ حجم ملف قاعدة البيانات: {stats['db_size_mb']} MB")

    print("\n🌍 توزيع الوظائف حسب الدولة (Geographic Distribution):")
    for country, count in sorted(stats["by_country"].items(), key=lambda x: -x[1]):
        pct = (count / stats["total_jobs"] * 100) if stats["total_jobs"] else 0
        print(f"  • {country:<28} : {count:>4} وظيفة ({pct:.1f}%)")

    print("\n🎯 توزيع الوظائف حسب مستوى الخبرة (Seniority Breakdown):")
    for lvl, count in sorted(stats["by_experience_level"].items(), key=lambda x: -x[1]):
        pct = (count / stats["total_jobs"] * 100) if stats["total_jobs"] else 0
        print(f"  • {lvl:<28} : {count:>4} وظيفة ({pct:.1f}%)")

    print("\n🔗 مصادر جمع البيانات (Scraping Sources Breakdown):")
    for src, count in sorted(stats["by_source"].items(), key=lambda x: -x[1]):
        print(f"  • {src:<32} : {count:>4} وظيفة")

    candidates = db.get_all_candidates()
    reports = db.get_all_reports()
    print(f"\n👤 إجمالي المرشحين في جدول candidates : {len(candidates)}")
    print(f"📁 إجمالي التقارير في جدول reports        : {len(reports)}")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    main()
