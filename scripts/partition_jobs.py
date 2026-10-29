import json
import os
import sys

# Ensure UTF-8 output encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Ensure project root is in sys.path
scripts_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(scripts_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def detect_country_and_mode(job: dict):
    """
    Analyzes job metadata (location, title, country, description) to extract:
    1. Normalized Country ('Egypt', 'Saudi_Arabia', 'UAE', 'Germany', 'United_Kingdom', 'France', 'USA', 'Netherlands', 'Switzerland', 'International')
    2. is_remote boolean (True if remote/worldwide/work-from-home)
    3. work_mode ('Remote', 'On-site', 'Hybrid')
    """
    loc = (job.get('location', '') + ' ' + job.get('country', '')).lower()
    title = job.get('title', '').lower()
    desc = job.get('cleaned_description', '')[:400].lower()
    full = f"{loc} {title} {desc}"

    # 1. Remote Detection
    is_remote = False
    work_mode = "On-site"
    
    if any(k in loc for k in ['remote', 'worldwide', 'global remote', 'anywhere', 'work from home', 'telecommute']):
        is_remote = True
        work_mode = "Remote"
    elif 'remote' in title or '100% remote' in full or 'fully remote' in full:
        is_remote = True
        work_mode = "Remote"
    elif 'hybrid' in loc or 'hybrid' in full:
        work_mode = "Hybrid"
        is_remote = True  # Can be worked remotely part of the time

    # 2. Country Detection
    if any(k in loc for k in ['egypt', 'cairo', 'giza', 'alexandria', 'maadi', 'nasr city', 'mansoura', 'smart village', '6th of october', 'new cairo', 'مصر', 'القاهرة', 'الجيزة', 'الإسكندرية']):
        country = 'Egypt'
    elif any(k in loc for k in ['saudi', 'ksa', 'riyadh', 'jeddah', 'dammam', 'khobar', 'mecca', 'medina', 'السعودية', 'الرياض', 'جدة', 'الدمام', 'الخبر']):
        country = 'Saudi_Arabia'
    elif any(k in loc for k in ['emirates', 'uae', 'dubai', 'abu dhabi', 'sharjah', 'ajman', 'الإمارات', 'دبي', 'أبوظبي', 'الشارقة']):
        country = 'UAE'
    elif any(k in loc for k in ['germany', 'berlin', 'munich', 'münchen', 'hamburg', 'köln', 'cologne', 'frankfurt', 'stuttgart', 'deutschland', 'düsseldorf', 'leipzig']):
        country = 'Germany'
    elif any(k in loc for k in ['united kingdom', ' uk', 'london', 'england', 'scotland', 'manchester', 'birmingham', 'bristol', 'edinburgh', 'cambridge', 'oxford']) or loc.startswith('uk'):
        country = 'United_Kingdom'
    elif any(k in loc for k in ['france', 'paris', 'lyon', 'marseille', 'toulouse', 'nantes', 'bordeaux', 'lille']):
        country = 'France'
    elif any(k in loc for k in ['netherland', 'amsterdam', 'utrecht', 'rotterdam', 'holland', 'eindhoven', 'hague']):
        country = 'Netherlands'
    elif any(k in loc for k in ['switzerland', 'zurich', 'zürich', 'geneva', 'lausanne', 'basel', 'bern']):
        country = 'Switzerland'
    elif any(k in loc for k in ['united states', 'usa', 'new york', 'california', 'san francisco', 'austin', 'seattle', 'boston', 'chicago']) or 'us' in loc.split():
        country = 'USA'
    elif is_remote:
        country = 'Global_Remote'
    else:
        country = 'Other_International'

    return country, is_remote, work_mode

def partition_and_save_jobs(dataset_path: str = None):
    """
    Loads unified jobs_dataset.json and partitions it into structured files:
    - by_country/jobs_egypt.json
    - by_country/jobs_saudi_arabia.json
    - by_country/jobs_uae.json
    - by_country/jobs_gulf_region.json
    - by_country/jobs_all_remote.json
    - by_country/jobs_germany.json
    - by_country/jobs_united_kingdom.json
    - by_country/jobs_france.json
    - by_country/jobs_switzerland.json
    - by_country/jobs_netherlands.json
    - by_country/jobs_usa.json
    - by_country/jobs_global_remote.json
    - by_country/jobs_other_international.json
    """
    if dataset_path is None:
        dataset_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "processed", "jobs_dataset.json")

    if not os.path.exists(dataset_path):
        print(f"❌ Error: Dataset file not found at {dataset_path}")
        return

    with open(dataset_path, "r", encoding="utf-8") as f:
        jobs = json.load(f)

    target_dir = os.path.join(os.path.dirname(dataset_path), "by_country")
    os.makedirs(target_dir, exist_ok=True)

    # Initialize buckets
    country_files = {
        "Egypt": "jobs_egypt.json",
        "Saudi_Arabia": "jobs_saudi_arabia.json",
        "UAE": "jobs_uae.json",
        "Germany": "jobs_germany.json",
        "United_Kingdom": "jobs_united_kingdom.json",
        "France": "jobs_france.json",
        "Switzerland": "jobs_switzerland.json",
        "Netherlands": "jobs_netherlands.json",
        "USA": "jobs_usa.json",
        "Global_Remote": "jobs_global_remote.json",
        "Other_International": "jobs_other_international.json"
    }

    partitioned_data = {k: [] for k in country_files}
    all_remote_jobs = []

    for job in jobs:
        cntry, is_rem, mode = detect_country_and_mode(job)
        job['normalized_country'] = cntry
        job['is_remote'] = is_rem
        job['work_mode'] = mode

        # Add to specific country bucket
        bucket = cntry if cntry in partitioned_data else "Other_International"
        partitioned_data[bucket].append(job)

        # If remote or hybrid, add to dedicated all-remote bucket
        if is_rem:
            all_remote_jobs.append(job)

    # 1. Save country specific files
    for cntry, filename in country_files.items():
        filepath = os.path.join(target_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(partitioned_data[cntry], f, ensure_ascii=False, indent=2)

    # 2. Save all remote jobs file
    remote_filepath = os.path.join(target_dir, "jobs_all_remote.json")
    with open(remote_filepath, "w", encoding="utf-8") as f:
        json.dump(all_remote_jobs, f, ensure_ascii=False, indent=2)

    # 3. Save Gulf Region aggregated file (Saudi Arabia + UAE)
    gulf_jobs = partitioned_data["Saudi_Arabia"] + partitioned_data["UAE"]
    gulf_filepath = os.path.join(target_dir, "jobs_gulf_region.json")
    with open(gulf_filepath, "w", encoding="utf-8") as f:
        json.dump(gulf_jobs, f, ensure_ascii=False, indent=2)

    # 4. Save Summary index file
    summary_filepath = os.path.join(target_dir, "summary_index.json")
    summary = {
        "total_jobs": len(jobs),
        "total_remote_jobs": len(all_remote_jobs),
        "total_egypt_jobs": len(partitioned_data["Egypt"]),
        "total_saudi_jobs": len(partitioned_data["Saudi_Arabia"]),
        "total_uae_jobs": len(partitioned_data["UAE"]),
        "total_gulf_jobs": len(gulf_jobs),
        "files_breakdown": {
            "jobs_all_remote.json": len(all_remote_jobs),
            "jobs_gulf_region.json": len(gulf_jobs),
            **{fname: len(partitioned_data[c]) for c, fname in country_files.items()}
        }
    }
    with open(summary_filepath, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # 5. Save master dataset with normalized fields back to disk
    with open(dataset_path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)

    # 6. Synchronize enriched jobs to SQLite database
    db_path = os.path.join(os.path.dirname(dataset_path), "jobs.db")
    if os.path.exists(db_path):
        try:
            from src.database import JobsDatabase
            db = JobsDatabase(db_path)
            new_cnt, upd_cnt = db.bulk_import_jobs(jobs, show_progress=False)
            print(f"🗄️ [DB UPDATE] SQLite database synced with country & remote partitions: {upd_cnt} updated ({db_path})")
        except Exception as e:
            print(f"⚠️ [DB NOTE] Could not sync database: {e}")

    # 7. Automatically synchronize partitions and jobs.db to final project/ai_engine
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    final_proj_dir = os.path.abspath(os.path.join(project_root, "..", "final project", "ai_engine"))
    if os.path.exists(final_proj_dir):
        try:
            import shutil
            dest_dataset = os.path.join(final_proj_dir, "data", "processed", "jobs_dataset.json")
            dest_db = os.path.join(final_proj_dir, "data", "processed", "jobs.db")
            dest_by_country = os.path.join(final_proj_dir, "data", "processed", "by_country")
            os.makedirs(dest_by_country, exist_ok=True)
            shutil.copy2(dataset_path, dest_dataset)
            if os.path.exists(db_path):
                shutil.copy2(db_path, dest_db)
            if os.path.exists(target_dir):
                for f in os.listdir(target_dir):
                    shutil.copy2(os.path.join(target_dir, f), os.path.join(dest_by_country, f))
            print("✅ Synchronized partitioned data & database to final project/ai_engine!")
        except Exception as e:
            print(f"⚠️ Note: Final project sync skipped: {e}")

    print("\n" + "=" * 70)
    print("📁 JOBS DATASET PARTITIONED BY COUNTRY & REMOTE STATUS SUCCESSFULLY!")
    print("=" * 70)
    print(f"Target Directory: {target_dir}\n")
    print(f"  • {'jobs_all_remote.json':<32} : {len(all_remote_jobs):>4} jobs (All Remote 🌐)")
    print(f"  • {'jobs_gulf_region.json':<32} : {len(gulf_jobs):>4} jobs (Gulf Region 🇸🇦 🇦🇪)")
    for c, fname in sorted(country_files.items(), key=lambda x: -len(partitioned_data[x[0]])):
        print(f"  • {fname:<32} : {len(partitioned_data[c]):>4} jobs ({c})")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    partition_and_save_jobs()
