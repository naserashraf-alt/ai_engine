r"""
migrate_all_jsons.py - Master script to import ALL project JSON files into SQLite database.
Imports:
  1. Extracted CV Profiles (data/extracted_cvs/*.json) -> candidates table
  2. AI Career Agent Reports (data/agent_reports/*.json) -> reports & report_evaluations tables
  3. Partition Summaries (data/processed/by_country/summary_index.json) -> partition_summaries table
  4. Any additional JSONs from final project -> database
"""

import os
import sys
import json
import shutil

# Ensure UTF-8 output encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Include project root in sys.path
scripts_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(scripts_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

from src.database import JobsDatabase


def main():
    print("=" * 75)
    print("🚀 IMPORTING ALL JSON FILES INTO SQLite DATABASE (jobs.db)")
    print("=" * 75)

    db_path = os.path.join(project_root, "data", "processed", "jobs.db")
    db = JobsDatabase(db_path)

    # 1. Import from ai_project
    print(f"\n📂 [1/2] Scanning '{project_root}' for JSON files...")
    counts = db.import_all_existing_jsons(project_root=project_root)
    print(f"  ├ Candidates imported into 'candidates' table : {counts['candidates_imported']}")
    print(f"  ├ Reports imported into 'reports' table       : {counts['reports_imported']}")
    print(f"  └ Summary imported into 'partition_summaries'  : {counts['summaries_imported']}")

    # 2. Check and import from final project if extra files exist
    final_proj_dir = os.path.abspath(os.path.join(project_root, "..", "final project", "ai_engine"))
    if os.path.exists(final_proj_dir):
        print(f"\n📂 [2/2] Checking '{final_proj_dir}' for extra JSON files...")
        final_counts = db.import_all_existing_jsons(project_root=final_proj_dir)
        print(f"  ├ Candidates imported : {final_counts['candidates_imported']}")
        print(f"  └ Reports imported    : {final_counts['reports_imported']}")

    # 3. Print Database Stats
    print("\n" + "=" * 75)
    print("📊 CURRENT DATABASE TOTALS (All Data in One Place):")
    stats = db.get_stats()
    print(f"  ├ Total Active Jobs        : {stats['total_jobs']:,} jobs")
    print(f"  ├ Total Remote Jobs        : {stats['total_remote']:,} jobs")
    
    candidates = db.get_all_candidates()
    print(f"  ├ Total Candidate Profiles : {len(candidates)} candidates")
    for c in candidates:
        print(f"      • #{c['id']} | {c['full_name']} ({c['primary_domain']} - {c['seniority_level']})")

    reports = db.get_all_reports()
    print(f"  ├ Total Agent Reports      : {len(reports)} reports")
    for r in reports:
        print(f"      • #{r['id']} | Candidate: {r['candidate_name']} | Target: {r['target_domain']} | Evals: {r['evaluations_count']} jobs | Top Score: {r['top_match_score']}%")

    print(f"  └ Database File Size       : {stats['db_size_mb']} MB")
    print("=" * 75)

    # 4. Sync updated jobs.db to final project
    if os.path.exists(final_proj_dir):
        dest_db = os.path.join(final_proj_dir, "data", "processed", "jobs.db")
        os.makedirs(os.path.dirname(dest_db), exist_ok=True)
        shutil.copy2(db_path, dest_db)
        print(f"\n🔄 [SYNC] Synchronized updated jobs.db to '{dest_db}'")

    print("\n✅ ALL JSON FILES ARE NOW FULLY STORED AND QUERYABLE IN THE DATABASE!\n")


if __name__ == "__main__":
    main()
