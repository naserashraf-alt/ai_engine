"""
=============================================================================
scripts/check_stats.py - Central Database & Jobs Analytics Inspector
=============================================================================

PURPOSE:
- Displays comprehensive real-time statistics on SQLite database (jobs.db).
- Visualizes distributions by country, source platforms, work modes, and seniority.

EXECUTION:
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
    print("📊 Central Database & Active Opportunities Analytics Report")
    print("=" * 75)

    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at: {DB_PATH}")
        return

    db = JobsDatabase(DB_PATH)
    stats = db.get_stats()

    print(f"  ├ Database Path: {DB_PATH}")
    print(f"  ├ Total Active Jobs: {stats['total_jobs']:,} jobs")
    print(f"  ├ Remote Opportunities: {stats['total_remote']:,} jobs")
    print(f"  ├ On-site Opportunities: {stats['total_onsite']:,} jobs")
    print(f"  ├ Unique Companies: {stats['unique_companies']:,} companies")
    print(f"  ├ Database File Size: {stats['db_size_mb']} MB")

    print("\n🌍 Geographic Distribution (By Country):")
    for country, count in sorted(stats["by_country"].items(), key=lambda x: -x[1]):
        pct = (count / stats["total_jobs"] * 100) if stats["total_jobs"] else 0
        print(f"  • {country:<28} : {count:>4} jobs ({pct:.1f}%)")

    print("\n🎯 Seniority Level Distribution:")
    for lvl, count in sorted(stats["by_experience_level"].items(), key=lambda x: -x[1]):
        pct = (count / stats["total_jobs"] * 100) if stats["total_jobs"] else 0
        print(f"  • {lvl:<28} : {count:>4} jobs ({pct:.1f}%)")

    print("\n🔗 Sourcing Platform Breakdown:")
    for src, count in sorted(stats["by_source"].items(), key=lambda x: -x[1]):
        print(f"  • {src:<32} : {count:>4} jobs")

    candidates = db.get_all_candidates()
    reports = db.get_all_reports()
    print(f"\n👤 Total Registered Candidates (candidates table) : {len(candidates)}")
    print(f"📁 Total Advisory Reports (reports table)          : {len(reports)}")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    main()
