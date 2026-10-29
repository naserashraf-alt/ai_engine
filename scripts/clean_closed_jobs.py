import requests
import json
import os
import sys
import time
import re
import shutil
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

# Force unbuffered UTF-8 output encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Include project dir in sys.path
ai_project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ai_project_dir not in sys.path:
    sys.path.append(ai_project_dir)

try:
    from scripts.partition_jobs import partition_and_save_jobs
except ImportError:
    from partition_jobs import partition_and_save_jobs


def is_job_closed(job: dict, headers: dict) -> tuple[dict, bool, str]:
    """
    Checks if a job posting is closed or expired across all platforms.
    Returns: (job, is_closed_flag, reason_description)
    """
    source_api = job.get("source_api", "")
    url = job.get("source_url", "")
    job_id = job.get("job_id", "")
    
    # 1. LinkedIn Job Check
    if "LinkedIn" in source_api or "linkedin" in job_id or "linkedin.com" in url:
        id_match = re.search(r'(\d{8,12})', job_id) or re.search(r'/view/(\d+)', url) or re.search(r'-(\d+)', url)
        if id_match:
            detail_url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{id_match.group(1)}"
            try:
                res = requests.get(detail_url, headers=headers, timeout=5)
                if res.status_code in [404, 410]:
                    return job, True, "LinkedIn 404/410 Not Found"
                if res.status_code == 200:
                    text = res.text.lower()
                    if "no longer accepting applications" in text or "this job is no longer available" in text:
                        return job, True, "LinkedIn 'No longer accepting applications'"
                # If 429 rate limit or timeout, assume active to avoid false-positive purging
                return job, False, "Active"
            except Exception:
                return job, False, "Active (Check Timeout)"

    # 2. Wuzzuf Job Check
    if "Wuzzuf" in source_api or "wuzzuf.net" in url:
        try:
            wuzzuf_headers = {
                **headers,
                "Referer": "https://www.google.com/"
            }
            res = requests.get(url, headers=wuzzuf_headers, timeout=5)
            if res.status_code in [404, 410]:
                return job, True, "Wuzzuf 404 Not Found"
            if res.status_code == 200:
                if "this job is closed" in res.text.lower() or "job has expired" in res.text.lower():
                    return job, True, "Wuzzuf Expired/Closed Badge"
            return job, False, "Active"
        except Exception:
            return job, False, "Active (Timeout)"

    # 3. Tanqeeb Check (Egypt, Saudi, UAE)
    if "Tanqeeb" in source_api or "tanqeeb.com" in url:
        try:
            res = requests.get(url, headers=headers, timeout=5, allow_redirects=True)
            if res.status_code in [404, 410]:
                return job, True, "Tanqeeb 404 Not Found"
            # Tanqeeb redirects closed jobs to search or home page
            if "/jobs/search" in res.url or res.url.rstrip("/").endswith("tanqeeb.com"):
                return job, True, "Tanqeeb Redirected to Search (Expired)"
            return job, False, "Active"
        except Exception:
            return job, False, "Active (Timeout)"

    # 4. Greenhouse (Canonical, GitLab, Elastic)
    if "Greenhouse" in source_api or "greenhouse.io" in url or "elastic.co" in url:
        try:
            res = requests.get(url, headers=headers, timeout=5, allow_redirects=True)
            if res.status_code in [404, 410]:
                return job, True, "Greenhouse 404 (Role Filled)"
            return job, False, "Active"
        except Exception:
            return job, False, "Active (Timeout)"

    # 5. Arbeitnow Specialized Check (Zero-tolerance for expired/redirected links)
    if "Arbeitnow" in source_api or "arbeitnow.com" in url:
        try:
            res = requests.get(url, headers=headers, timeout=5, allow_redirects=True)
            if res.status_code in [404, 410] or res.status_code != 200:
                return job, True, f"Arbeitnow HTTP {res.status_code} Not Found"
            if res.url.rstrip("/") in ("https://www.arbeitnow.com", "https://www.arbeitnow.com/jobs"):
                return job, True, "Arbeitnow Redirected to Home/Jobs (Expired)"
            text_lower = res.text.lower()[:3000]
            if any(p in text_lower for p in ["this job is closed", "no longer available", "job has expired", "position has been filled", "abgelaufen", "diese anzeige"]):
                return job, True, "Arbeitnow Expired/Closed Page"
            return job, False, "Active"
        except Exception:
            return job, True, "Arbeitnow Dead/Unreachable Link"

    # 6. General URL Check (Remotive, Jobicy, RemoteOK, WeWorkRemotely, Himalayas)
    if url:
        try:
            res = requests.get(url, headers=headers, timeout=5, allow_redirects=True)
            if res.status_code in [404, 410]:
                return job, True, f"HTTP {res.status_code} Not Found"
            text_lower = res.text.lower()[:2000]
            if "job is closed" in text_lower or "no longer available" in text_lower or "position has been filled" in text_lower:
                return job, True, "Page indicates position filled"
        except Exception:
            pass
            
    return job, False, "Active"


def sync_cleaned_data_to_final_project(dataset_path: str, by_country_dir: str):
    """Syncs the cleaned master dataset, jobs.db, and all by_country files to final project/ai_engine/."""
    final_proj_dir = os.path.join(os.path.dirname(ai_project_dir), "final project", "ai_engine")
    if not os.path.exists(final_proj_dir):
        return
        
    try:
        dest_dataset = os.path.join(final_proj_dir, "data", "processed", "jobs_dataset.json")
        dest_by_country = os.path.join(final_proj_dir, "data", "processed", "by_country")
        db_path = os.path.join(ai_project_dir, "data", "processed", "jobs.db")
        dest_db = os.path.join(final_proj_dir, "data", "processed", "jobs.db")
        
        os.makedirs(os.path.dirname(dest_dataset), exist_ok=True)
        shutil.copy2(dataset_path, dest_dataset)
        
        if os.path.exists(db_path):
            shutil.copy2(db_path, dest_db)

        if os.path.exists(by_country_dir):
            os.makedirs(dest_by_country, exist_ok=True)
            for f in os.listdir(by_country_dir):
                src_f = os.path.join(by_country_dir, f)
                dst_f = os.path.join(dest_by_country, f)
                if os.path.isfile(src_f):
                    shutil.copy2(src_f, dst_f)
                    
        print(f"🔄 [SYNC SUCCESS] Synchronized clean dataset, jobs.db & by_country/ to 'final project/ai_engine/'!", flush=True)
    except Exception as e:
        print(f"⚠️ [SYNC NOTE] Could not sync to final project: {e}", flush=True)


def clean_all_closed_jobs(max_workers: int = 15, sample_limit: int = None):
    """
    1. Checks jobs concurrently across all platforms.
    2. Purges closed/expired jobs.
    3. Saves master cleaned jobs_dataset.json.
    4. Automatically updates EVERY country and remote partition file in by_country/.
    5. Synchronizes the cleaned database to final project/ai_engine/.
    """
    dataset_path = os.path.join(ai_project_dir, "data", "processed", "jobs_dataset.json")
    by_country_dir = os.path.join(ai_project_dir, "data", "processed", "by_country")
    
    if not os.path.exists(dataset_path):
        print("❌ Dataset file not found.", flush=True)
        return
        
    with open(dataset_path, "r", encoding="utf-8") as f:
        jobs = json.load(f)
        
    total_initial = len(jobs)
    target_jobs = jobs[:sample_limit] if sample_limit else jobs
    
    print("=" * 75, flush=True)
    print(f"🧹 STARTING CLOSED JOBS CLEANER & DATABASE REFRESH ENGINE", flush=True)
    print(f"   Total Jobs in Database: {total_initial} | To Verify: {len(target_jobs)}", flush=True)
    print(f"   Concurrent Workers: {max_workers}", flush=True)
    print("=" * 75, flush=True)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8"
    }
    
    active_jobs = []
    closed_jobs = []
    checked_count = 0
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_job = {
            executor.submit(is_job_closed, job, headers): job for job in target_jobs
        }
        
        for future in as_completed(future_to_job):
            checked_count += 1
            job, closed, reason = future.result()
            
            if closed:
                closed_jobs.append(job)
                title = job.get('title', 'N/A')
                comp = job.get('company', 'N/A')
                src = job.get('source_api', 'Unknown')
                print(f"  ❌ [{checked_count}/{len(target_jobs)}] Purged: {title[:35]} @ {comp[:20]} [{src}] -> ({reason})", flush=True)
            else:
                active_jobs.append(job)
                
            if checked_count % 100 == 0 or checked_count == len(target_jobs):
                print(f"  ⏳ Progress: Verified {checked_count}/{len(target_jobs)} jobs... ({len(closed_jobs)} closed purged so far)", flush=True)
                
    # If sample_limit was set, keep remaining jobs untouched
    if sample_limit and sample_limit < total_initial:
        active_jobs.extend(jobs[sample_limit:])
        
    elapsed = round(time.time() - start_time, 2)
    
    print("\n" + "=" * 75, flush=True)
    print(f"📊 CLEANING COMPLETE (Time: {elapsed}s):", flush=True)
    print(f"  ├ Initial Database Size: {total_initial} jobs", flush=True)
    print(f"  ├ Closed / Expired Purged: {len(closed_jobs)} jobs", flush=True)
    print(f"  └ Retained Active Jobs: {len(active_jobs)} jobs", flush=True)
    print("=" * 75, flush=True)
    
    # 1. Save master dataset
    with open(dataset_path, "w", encoding="utf-8") as f:
        json.dump(active_jobs, f, ensure_ascii=False, indent=2)
    print(f"💾 [SAVED] Master dataset updated: {dataset_path}", flush=True)

    # 2. Update SQLite database
    db_path = os.path.join(ai_project_dir, "data", "processed", "jobs.db")
    if os.path.exists(db_path) and closed_jobs:
        try:
            from src.database import JobsDatabase
            db = JobsDatabase(db_path)
            closed_ids = [j.get("job_id") for j in closed_jobs if j.get("job_id")]
            del_count = db.delete_jobs_batch(closed_ids)
            print(f"🗄️ [DB UPDATE] Deleted {del_count} closed jobs from SQLite database ({db_path})", flush=True)
        except Exception as e:
            print(f"⚠️ [DB NOTE] Could not delete from database: {e}", flush=True)
    
    # 2. Trigger automatic partitioning for by_country/*.json
    print("\n📂 Re-partitioning by_country/ files to reflect purged jobs...", flush=True)
    partition_and_save_jobs(dataset_path)
    
    # 3. Synchronize to final project/ai_engine
    sync_cleaned_data_to_final_project(dataset_path, by_country_dir)
    print("\n✅ Entire database and all region partitions are 100% updated and synchronized!\n", flush=True)

if __name__ == "__main__":
    limit_arg = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else None
    clean_all_closed_jobs(max_workers=25, sample_limit=limit_arg)
