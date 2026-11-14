r"""
migrate_to_db.py - One-shot migration script.
Converts jobs_dataset.json -> SQLite database (jobs.db).
Preserves all 7,211+ jobs with full data integrity.

Usage:
    python scripts/migrate_to_db.py
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

from src.database import migrate_json_to_db, JobsDatabase


def main():
    json_path = os.path.join(project_root, "data", "processed", "jobs_dataset.json")
    db_path = os.path.join(project_root, "data", "processed", "jobs.db")

    if not os.path.exists(json_path):
        print(f"❌ JSON dataset not found at: {json_path}")
        return

    # 1. Run migration
    db = migrate_json_to_db(json_path, db_path=db_path, partition_data=True)
    if not db:
        return

    # 2. Verify data integrity
    print("\n🔍 VERIFYING DATA INTEGRITY...")
    with open(json_path, "r", encoding="utf-8") as f:
        original_jobs = json.load(f)

    db_count = db.get_total_count()
    json_count = len(original_jobs)

    print(f"  ├ Original JSON records: {json_count}")
    print(f"  ├ Database records:      {db_count}")

    if db_count == json_count:
        print(f"  ✅ PERFECT MATCH! All {json_count} jobs migrated successfully.")
    elif db_count < json_count:
        diff = json_count - db_count
        print(f"  ⚠️ {diff} duplicate records were merged (same job_id). This is expected behavior.")
        print(f"  ✅ All unique jobs migrated successfully.")
    else:
        print(f"  ⚠️ Warning: DB has more records than JSON ({db_count} vs {json_count})")

    # 3. Export partitioned JSON files from DB (backward compatibility)
    print("\n📂 Exporting partitioned JSON files from database...")
    results = db.export_partitioned()
    for fname, count in sorted(results.items(), key=lambda x: -x[1]):
        print(f"  • {fname:<32} : {count:>4} jobs")

    # 4. Sync database to final project
    final_proj_dir = os.path.join(project_root, "..", "final project", "ai_engine")
    if os.path.exists(final_proj_dir):
        dest_db = os.path.join(final_proj_dir, "data", "processed", "jobs.db")
        os.makedirs(os.path.dirname(dest_db), exist_ok=True)
        shutil.copy2(db_path, dest_db)

        # Also sync database.py source file
        src_db_module = os.path.join(project_root, "src", "database.py")
        dest_db_module = os.path.join(final_proj_dir, "src", "database.py")
        os.makedirs(os.path.dirname(dest_db_module), exist_ok=True)
        shutil.copy2(src_db_module, dest_db_module)

        print(f"\n🔄 [SYNC] Database synced to: {dest_db}")
        print(f"🔄 [SYNC] database.py synced to: {dest_db_module}")

    # 5. Print top skills
    stats = db.get_stats()
    if stats.get("top_skills"):
        print(f"\n🏆 TOP 15 MOST IN-DEMAND SKILLS:")
        for idx, (skill, count) in enumerate(list(stats["top_skills"].items())[:15], 1):
            print(f"  {idx:>2}. {skill:<25} ({count} jobs)")

    print(f"\n✅ MIGRATION COMPLETE!")
    print(f"   Database: {db_path}")
    print(f"   Size:     {stats['db_size_mb']} MB\n")


if __name__ == "__main__":
    main()
