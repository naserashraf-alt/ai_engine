"""
=============================================================================
scripts/clean_arbeitnow_strict.py - Strict Tech & Active Link Filter for Arbeitnow
=============================================================================

PURPOSE:
- Filter all Arbeitnow jobs in `jobs.db` and `jobs_dataset.json`:
  1. Purge non-tech / non-engineering / German business roles.
  2. Verify all remaining tech job URLs concurrently (25 threads).
  3. Purge all dead links (HTTP 404, 410, expired pages, redirects).
  4. Update `jobs.db` and `jobs_dataset.json`.
  5. Re-partition by country and sync to `final project/ai_engine`.
=============================================================================
"""

import os
import sys
import json
import re
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# Force unbuffered UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.database import JobsDatabase
from scripts.partition_jobs import partition_and_save_jobs


TECH_POSITIVE_REGEX = re.compile(
    r'\b(software|developer|engineer|engineering|data scientist|data engineer|'
    r'data science|machine learning|deep learning|ai engineer|ai developer|'
    r'computer vision|nlp|devops|cloud|sre|site reliability|full stack|fullstack|'
    r'frontend|backend|web developer|python|react|node|golang|java developer|'
    r'c\+\+|embedded|qa engineer|test automation|security engineer|cybersecurity|'
    r'infrastructure|database administrator|architect|tech lead|mobile developer|'
    r'android|ios|flutter|systems engineer)\b',
    re.IGNORECASE
)

NON_TECH_NEGATIVE_REGEX = re.compile(
    r'\b(ausbildung|buchhalter|accountant|accounting|supply chain|pflege|'
    r'krankenschwester|nurse|hotel|sales manager|key account|vertrieb|'
    r'recruiter|talent acquisition|personalreferent|hr manager|marketing manager|'
    r'content manager|social media|kaufmann|kauffrau|lagerist|einkauf|'
    r'jurist|legal counsel|steuerberater|tax|office manager|empfang|'
    r'kundenservice|customer support executive|call center|real estate|'
    r'immobilien|verwalter|propulsion|tiefbau|mechaniker|mechanic)\b',
    re.IGNORECASE
)


def is_arbeitnow_job_active(url: str, headers: dict) -> tuple[bool, str]:
    """
    Checks if an Arbeitnow URL is genuinely active and not expired.
    Returns: (is_active: bool, reason: str)
    """
    if not url:
        return False, "Missing URL"
    try:
        res = requests.get(url, headers=headers, timeout=5, allow_redirects=True)
        if res.status_code in (404, 410):
            return False, f"HTTP {res.status_code}"
        if res.status_code != 200:
            return False, f"HTTP {res.status_code}"
            
        # Check redirects to home/search
        if res.url.rstrip("/") in ("https://www.arbeitnow.com", "https://www.arbeitnow.com/jobs"):
            return False, "Redirected to general jobs listing (expired)"
            
        text_lower = res.text.lower()[:3000]
        # Check expired banners in Arbeitnow
        if any(phrase in text_lower for phrase in [
            "this job is closed",
            "this job post is no longer available",
            "job has expired",
            "this position has been filled",
            "diese stelle ist nicht mehr verfgbar",
            "diese anzeige ist abgelaufen",
            "job is closed"
        ]):
            return False, "Page contains expired/closed notice"
            
        return True, "Active"
    except Exception as e:
        # On connection error or timeout, consider dead to prevent bad user experience
        return False, f"Error: {e}"


def run_clean_arbeitnow():
    print("=" * 80)
    print("🧹 STRICT ARBEITNOW TECH FILTER & DEAD LINK PURGE")
    print("=" * 80)

    dataset_path = os.path.join(project_root, "data", "processed", "jobs_dataset.json")
    db_path = os.path.join(project_root, "data", "processed", "jobs.db")

    if not os.path.exists(dataset_path):
        print("❌ Dataset not found.")
        return

    with open(dataset_path, "r", encoding="utf-8") as f:
        all_jobs = json.load(f)

    print(f"Total jobs currently in dataset: {len(all_jobs)}")

    non_arbeitnow_jobs = []
    arbeitnow_jobs = []

    for j in all_jobs:
        if j.get("source_api") == "Arbeitnow" or "arbeitnow" in j.get("job_id", "") or "arbeitnow.com" in j.get("source_url", ""):
            arbeitnow_jobs.append(j)
        else:
            non_arbeitnow_jobs.append(j)

    print(f"  ├ Non-Arbeitnow jobs (Preserved 100%): {len(non_arbeitnow_jobs)}")
    print(f"  └ Arbeitnow jobs to audit           : {len(arbeitnow_jobs)}")

    # 1. Title Filter: Keep only pure Tech & eliminate non-tech German roles
    tech_arbeitnow = []
    purged_non_tech = []

    for j in arbeitnow_jobs:
        title = j.get("title", "")
        # Must match positive tech regex AND NOT match non-tech negative regex
        if TECH_POSITIVE_REGEX.search(title) and not NON_TECH_NEGATIVE_REGEX.search(title):
            tech_arbeitnow.append(j)
        else:
            purged_non_tech.append(j)

    print(f"\n[Step 1] Pure Tech Title Screening:")
    print(f"  ├ Purged non-tech / German generic business jobs: {len(purged_non_tech)}")
    print(f"  └ Verified tech titles remaining for URL check  : {len(tech_arbeitnow)}")

    # 2. Concurrent HTTP Link Verification (25 threads)
    print(f"\n[Step 2] Verifying URLs of {len(tech_arbeitnow)} tech jobs (25 concurrent threads)...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }

    verified_active_arbeitnow = []
    purged_dead_links = []
    checked = 0
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=25) as executor:
        future_to_job = {
            executor.submit(is_arbeitnow_job_active, j.get("source_url", ""), headers): j
            for j in tech_arbeitnow
        }

        for future in as_completed(future_to_job):
            j = future_to_job[future]
            checked += 1
            is_active, reason = future.result()

            if is_active:
                verified_active_arbeitnow.append(j)
            else:
                purged_dead_links.append((j, reason))

            if checked % 100 == 0 or checked == len(tech_arbeitnow):
                print(f"  ⏳ Verified {checked}/{len(tech_arbeitnow)}... ({len(verified_active_arbeitnow)} active, {len(purged_dead_links)} dead)")

    elapsed = round(time.time() - start_time, 2)
    print(f"\nURL Verification completed in {elapsed}s:")
    print(f"  ├ Active, working Arbeitnow tech jobs : {len(verified_active_arbeitnow)}")
    print(f"  └ Dead/expired links purged          : {len(purged_dead_links)}")

    # 3. Combine non-Arbeitnow + verified active Arbeitnow
    final_clean_jobs = non_arbeitnow_jobs + verified_active_arbeitnow
    print(f"\n[Step 3] New Master Clean Dataset Size: {len(final_clean_jobs)} jobs")

    # Save to jobs_dataset.json
    with open(dataset_path, "w", encoding="utf-8") as f:
        json.dump(final_clean_jobs, f, ensure_ascii=False, indent=2)
    print(f"💾 Updated {dataset_path}")

    # 4. Update SQLite database: delete all purged jobs
    all_purged_ids = [j.get("job_id") for j in purged_non_tech if j.get("job_id")] + \
                     [j.get("job_id") for j, _ in purged_dead_links if j.get("job_id")]

    if os.path.exists(db_path) and all_purged_ids:
        db = JobsDatabase(db_path)
        print(f"\n[Step 4] Deleting {len(all_purged_ids)} purged jobs from SQLite database...")
        deleted = db.delete_jobs_batch(all_purged_ids)
        print(f"🗄️ SQLite database cleaned: {deleted} jobs permanently deleted ({db_path})")

    # 5. Re-partition dataset
    print("\n[Step 5] Re-partitioning by_country/ files...")
    partition_and_save_jobs(dataset_path)

    # 6. Synchronize to final project/ai_engine
    final_proj_dir = os.path.abspath(os.path.join(project_root, "..", "final project", "ai_engine"))
    if os.path.exists(final_proj_dir):
        print("\n[Step 6] Synchronizing clean database to final project/ai_engine...")
        import shutil
        shutil.copy2(dataset_path, os.path.join(final_proj_dir, "data", "processed", "jobs_dataset.json"))
        shutil.copy2(db_path, os.path.join(final_proj_dir, "data", "processed", "jobs.db"))
        
        src_by_country = os.path.join(project_root, "data", "processed", "by_country")
        dst_by_country = os.path.join(final_proj_dir, "data", "processed", "by_country")
        if os.path.exists(src_by_country):
            for f in os.listdir(src_by_country):
                shutil.copy2(os.path.join(src_by_country, f), os.path.join(dst_by_country, f))
        print("✅ 100% Synchronization with final project/ai_engine completed!")

    print("\n" + "=" * 80)
    print(f"🎉 ARBEITNOW STRICT CLEANUP COMPLETE!")
    print(f"  ├ Remaining Active, Working Tech Jobs: {len(final_clean_jobs)}")
    print(f"  └ Every remaining Arbeitnow job link is VERIFIED 200 OK & TECH!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_clean_arbeitnow()
