import requests
import json
import re
import os
import sys
import time
from bs4 import BeautifulSoup

# Ensure UTF-8 output encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Include project root and scripts in path
scripts_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(scripts_dir, ".."))
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.classifier import SeniorityClassifier

def clean_html(text: str) -> str:
    """Removes HTML tags and normalizes whitespace."""
    if not text:
        return ""
    clean = re.sub(r'<[^>]+>', ' ', text)
    clean = re.sub(r'&[a-zA-Z0-9#]+;', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

# ======================================================================
# 1. WUZZUF EGYPT (wuzzuf.net) - Egypt's #1 Direct Tech Job Board
# ======================================================================
def fetch_wuzzuf_jobs(limit_per_keyword: int = 15) -> list:
    """
    Scrapes live jobs directly from Wuzzuf (Egypt), extracting exact titles,
    companies, locations, seniority levels, years of experience, and skill tags.
    """
    keywords = [
        "Software Engineer", "Full Stack", "Backend Developer", "Frontend Developer",
        "Data Scientist", "Data Engineer", "Machine Learning", "AI Engineer",
        "Mobile Developer", "Flutter", "Android", "iOS",
        "DevOps Engineer", "Cloud Engineer", "Cybersecurity", ".NET Developer", "Python", "Node.js"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
        "Referer": "https://www.google.com/"
    }
    
    all_jobs = []
    seen_ids = set()
    print("[1/8] Fetching live tech jobs from Wuzzuf (Egypt 🇪🇬)...")
    
    for kw in keywords:
        search_url = f"https://wuzzuf.net/search/jobs/?q={requests.utils.quote(kw)}&a=hpb"
        try:
            res = requests.get(search_url, headers=headers, timeout=12)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                cards = soup.find_all("div", class_=lambda c: c and ('css-pkv5jc' in c or 'css-1gatmva' in c) if c else False)
                
                added = 0
                for card in cards:
                    h2 = card.find("h2")
                    if not h2:
                        continue
                    a_tag = h2.find("a")
                    if not a_tag:
                        continue
                        
                    title = h2.text.strip()
                    job_url = "https://wuzzuf.net" + a_tag.get("href", "") if a_tag.get("href", "").startswith("/") else a_tag.get("href", "")
                    
                    # Generate deterministic job ID
                    slug_match = re.search(r'/jobs/p/([a-zA-Z0-9_-]+)', job_url)
                    job_id = f"wuzzuf_{slug_match.group(1)}" if slug_match else f"wuzzuf_{hash(job_url)}"
                    
                    if job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)
                    
                    # Company
                    comp_elem = card.find("a", class_=lambda x: x and ('css-ipsyv7' in x or 'css-17s97q8' in x) if x else False) or card.find("a", href=lambda x: x and '/jobs/careers/' in x if x else False)
                    company = comp_elem.text.replace("-", "").strip() if comp_elem else "Tech Company"
                    
                    # Location
                    loc_span = card.find("span", class_=lambda x: x and ('css-16x61xq' in x or 'css-5wys0k' in x) if x else False)
                    location = loc_span.text.strip() if loc_span else "Cairo, Egypt"
                    
                    # Skill tags
                    tag_elems = card.find_all("a", class_="css-5x9pm1")
                    skill_tags = [t.text.replace("·", "").strip() for t in tag_elems if t.text.strip()]
                    tags_str = ", ".join(skill_tags)
                    
                    # Career level hint from card text
                    card_text = card.text
                    level_hint = ""
                    for lvl_word in ["Entry Level", "Experienced", "Manager", "Senior", "Junior"]:
                        if lvl_word.lower() in card_text.lower():
                            level_hint = lvl_word
                            break
                            
                    full_desc = f"{title} at {company} located in {location}. Skills and tools: {tags_str}. Details: {card_text[:300]}"
                    cleaned_desc = clean_html(full_desc)
                    exp_level = SeniorityClassifier.classify_job_level(title, cleaned_desc, level_hint)
                    
                    all_jobs.append({
                        "job_id": job_id,
                        "title": title,
                        "company": company,
                        "location": location,
                        "category": kw,
                        "experience_level": exp_level,
                        "original_description": full_desc,
                        "cleaned_description": cleaned_desc,
                        "job_type": "Full-time",
                        "source_url": job_url,
                        "source_api": "Wuzzuf",
                        "country": "Egypt"
                    })
                    added += 1
                    if added >= limit_per_keyword:
                        break
                        
                print(f"  ├ Wuzzuf ['{kw}']: fetched {added} jobs.")
            time.sleep(0.3)
        except Exception as e:
            print(f"  ├ [WARNING] Wuzzuf error for '{kw}': {e}")
            
    print(f"✅ Total Wuzzuf Egypt jobs fetched: {len(all_jobs)}")
    return all_jobs


# ======================================================================
# 2. TANQEEB EGYPT (egypt.tanqeeb.com) - Egypt's #1 Job Aggregator
# ======================================================================
def fetch_tanqeeb_egypt_jobs(limit_per_keyword: int = 15) -> list:
    """
    Scrapes live jobs from Tanqeeb Egypt, which aggregates jobs from Bayt,
    LinkedIn, and Egyptian tech companies.
    """
    keywords = [
        "Software Engineer", "Frontend", "Backend", "Full Stack",
        "Data Scientist", "Data Engineer", "Machine Learning",
        "DevOps", "Mobile Developer", "Flutter", ".NET Developer", "Python"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
        "Referer": "https://www.google.com/"
    }
    
    all_jobs = []
    seen_ids = set()
    print("\n[2/8] Fetching live tech jobs from Tanqeeb (Egypt Aggregator 🇪🇬)...")
    
    for kw in keywords:
        search_url = f"https://egypt.tanqeeb.com/jobs/search?keywords={requests.utils.quote(kw)}"
        try:
            res = requests.get(search_url, headers=headers, timeout=12)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                cards = soup.find_all("div", class_=lambda c: c and 'card-body' in c.lower() and 'search-job-card' in c.lower() if c else False)
                
                added = 0
                for card in cards:
                    title_elem = card.find("h2", class_="search-job-title") or card.find("a", class_="search-job-title-link")
                    if not title_elem:
                        continue
                    a_tag = title_elem.find("a") if title_elem.name != "a" else title_elem
                    if not a_tag:
                        continue
                        
                    title = a_tag.text.strip()
                    rel_url = a_tag.get("href", "")
                    job_url = "https://egypt.tanqeeb.com" + rel_url if rel_url.startswith("/") else rel_url
                    
                    id_match = re.search(r'/jobs/([0-9a-zA-Z_-]+)\.html', job_url)
                    job_id = f"tanqeeb_{id_match.group(1)}" if id_match else f"tanqeeb_{hash(job_url)}"
                    
                    if job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)
                    
                    # Company & Location
                    comp_elem = card.find("div", class_="search-job-company-block") or card.find("div", class_="search-job-company-info")
                    company = comp_elem.text.strip() if comp_elem else "Egyptian Tech Employer"
                    # clean company name from extra whitespace
                    company = re.sub(r'\s+', ' ', company).strip()
                    if not company:
                        company = "Tech Company (Egypt)"
                        
                    loc_elem = card.find("span", class_="search-job-workplace-location")
                    location = loc_elem.text.replace("On-site -", "").replace("Remote -", "").strip() if loc_elem else "Cairo, Egypt"
                    
                    full_desc = f"{title} at {company} in {location}. Aggregated via Tanqeeb Egypt. Details available at source."
                    cleaned_desc = clean_html(full_desc)
                    exp_level = SeniorityClassifier.classify_job_level(title, cleaned_desc)
                    
                    all_jobs.append({
                        "job_id": job_id,
                        "title": title,
                        "company": company,
                        "location": location,
                        "category": kw,
                        "experience_level": exp_level,
                        "original_description": full_desc,
                        "cleaned_description": cleaned_desc,
                        "job_type": "Full-time",
                        "source_url": job_url,
                        "source_api": "Tanqeeb (Egypt Aggregator)",
                        "country": "Egypt"
                    })
                    added += 1
                    if added >= limit_per_keyword:
                        break
                        
                print(f"  ├ Tanqeeb ['{kw}']: fetched {added} jobs.")
            time.sleep(0.3)
        except Exception as e:
            print(f"  ├ [WARNING] Tanqeeb error for '{kw}': {e}")
            
    print(f"✅ Total Tanqeeb Egypt jobs fetched: {len(all_jobs)}")
    return all_jobs


# ======================================================================
# 3. HIMALAYAS API (himalayas.app/jobs/api) - Modern Tech & AI Jobs API
# ======================================================================
def fetch_himalayas_jobs(limit: int = 50) -> list:
    """
    Fetches live developer & AI jobs from Himalayas official API with built-in seniority.
    """
    all_jobs = []
    seen_ids = set()
    print("\n[3/8] Fetching live tech jobs from Himalayas API (Global Tech & AI 🌐)...")
    
    url = f"https://himalayas.app/jobs/api?limit={limit}"
    headers = {"User-Agent": "CareerMatchingEngine/3.0 (academic graduation project)"}
    
    try:
        res = requests.get(url, headers=headers, timeout=12)
        if res.status_code == 200:
            data = res.json()
            jobs = data.get("jobs", [])
            for job in jobs:
                job_id = f"himalayas_{job.get('guid', hash(job.get('title', '')))}"
                if job_id not in seen_ids:
                    seen_ids.add(job_id)
                    title = job.get("title", "").strip()
                    company = job.get("companyName", "").strip() or "Tech Company"
                    raw_desc = job.get("description", "") or job.get("excerpt", "")
                    cleaned_desc = clean_html(raw_desc)
                    
                    # Seniority level hint
                    sen_list = job.get("seniority", [])
                    hint = sen_list[0] if isinstance(sen_list, list) and sen_list else ""
                    exp_level = SeniorityClassifier.classify_job_level(title, cleaned_desc, hint)
                    
                    all_jobs.append({
                        "job_id": job_id,
                        "title": title,
                        "company": company,
                        "location": job.get("locationRestrictions", ["Remote"])[0] if job.get("locationRestrictions") else "Remote",
                        "category": "Tech & Engineering",
                        "experience_level": exp_level,
                        "original_description": raw_desc,
                        "cleaned_description": cleaned_desc,
                        "job_type": job.get("employmentType", "Full-time"),
                        "source_url": job.get("applicationLink") or f"https://himalayas.app/jobs/{job.get('guid', '')}",
                        "source_api": "Himalayas",
                        "country": "Global Remote"
                    })
            print(f"  ├ Himalayas API fetched {len(all_jobs)} jobs.")
    except Exception as e:
        print(f"  ├ [WARNING] Himalayas error: {e}")
        
    print(f"✅ Total jobs fetched from Himalayas: {len(all_jobs)}")
    return all_jobs


# ======================================================================
# 4. WE WORK REMOTELY (weworkremotely.com) - Top Remote Programming Jobs
# ======================================================================
def fetch_weworkremotely_jobs() -> list:
    """
    Fetches live remote software engineering & DevOps jobs from We Work Remotely RSS.
    """
    categories = [
        ("remote-programming-jobs", "Software Development"),
        ("remote-devops-sysadmin-jobs", "DevOps & Cloud")
    ]
    all_jobs = []
    seen_ids = set()
    print("\n[4/8] Fetching live jobs from We Work Remotely (WWR 🌐)...")
    
    headers = {"User-Agent": "Mozilla/5.0"}
    for cat_slug, cat_name in categories:
        url = f"https://weworkremotely.com/categories/{cat_slug}.rss"
        try:
            res = requests.get(url, headers=headers, timeout=12)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "xml")
                items = soup.find_all("item")
                added = 0
                for item in items:
                    title_elem = item.find("title")
                    link_elem = item.find("link")
                    desc_elem = item.find("description")
                    
                    if not title_elem or not link_elem:
                        continue
                        
                    raw_title = title_elem.text.strip()
                    job_url = link_elem.text.strip()
                    job_id = f"wwr_{hash(job_url)}"
                    
                    if job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)
                    
                    # Split title if format is "Company: Title"
                    company = "Remote Tech Company"
                    title = raw_title
                    if ":" in raw_title:
                        parts = raw_title.split(":", 1)
                        company = parts[0].strip()
                        title = parts[1].strip()
                        
                    raw_desc = desc_elem.text.strip() if desc_elem else f"{title} at {company}"
                    cleaned_desc = clean_html(raw_desc)
                    exp_level = SeniorityClassifier.classify_job_level(title, cleaned_desc)
                    
                    all_jobs.append({
                        "job_id": job_id,
                        "title": title,
                        "company": company,
                        "location": "Global Remote",
                        "category": cat_name,
                        "experience_level": exp_level,
                        "original_description": raw_desc,
                        "cleaned_description": cleaned_desc,
                        "job_type": "Full-time",
                        "source_url": job_url,
                        "source_api": "WeWorkRemotely",
                        "country": "Global Remote"
                    })
                    added += 1
                print(f"  ├ WWR ['{cat_slug}']: fetched {added} jobs.")
            time.sleep(0.3)
        except Exception as e:
            print(f"  ├ [WARNING] WWR error for '{cat_slug}': {e}")
            
    print(f"✅ Total jobs fetched from WeWorkRemotely: {len(all_jobs)}")
    return all_jobs


# ======================================================================
# 5. LINKEDIN EGYPT (Guest API)
# ======================================================================
def fetch_linkedin_egypt_jobs(limit_per_keyword: int = 15) -> list:
    """Fetches live LinkedIn jobs across tech fields in Egypt."""
    keywords = [
        "Junior Software Engineer", "Software Engineer Intern", "Software Engineer",
        "Full Stack Developer", "Backend Developer", "Frontend Developer",
        "Data Engineer", "Data Scientist", "Machine Learning Engineer",
        "Mobile Developer", "Flutter Developer", "DevOps Engineer", "Cloud Engineer",
        "Cybersecurity Specialist", "QA Automation Engineer", ".NET Developer", "Python Developer",
        "Senior Software Engineer", "Technical Lead"
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8"
    }
    all_jobs = []
    seen_ids = set()
    print("\n[5/8] Fetching live LinkedIn jobs in Egypt (LinkedIn Guest API 🇪🇬)...")
    
    for kw in keywords:
        search_url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={requests.utils.quote(kw)}&location=Egypt&start=0"
        try:
            res = requests.get(search_url, headers=headers, timeout=12)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                job_cards = soup.find_all("li")
                added = 0
                for card in job_cards:
                    link_elem = card.find("a", class_="base-card__full-link")
                    title_elem = card.find("h3", class_="base-search-card__title")
                    company_elem = card.find("h4", class_="base-search-card__subtitle")
                    location_elem = card.find("span", class_="job-search-card__location")
                    
                    if link_elem and title_elem:
                        job_url = link_elem.get("href", "").split("?")[0]
                        job_id_match = re.search(r'-(\d+)$', job_url) or re.search(r'/view/(\d+)', job_url)
                        num_id = job_id_match.group(1) if job_id_match else None
                        job_id = f"linkedin_eg_{num_id}" if num_id else f"linkedin_eg_{hash(job_url)}"
                        canonical_url = f"https://www.linkedin.com/jobs/view/{num_id}/" if num_id else job_url
                        
                        if job_id not in seen_ids:
                            seen_ids.add(job_id)
                            title = title_elem.text.strip()
                            company = company_elem.text.strip() if company_elem else "N/A"
                            location = location_elem.text.strip() if location_elem else "Egypt"
                            
                            raw_desc = f"{title} role at {company} in {location}. Full description available at source URL."
                            cleaned_desc = clean_html(raw_desc)
                            exp_level = SeniorityClassifier.classify_job_level(title, cleaned_desc)
                            
                            all_jobs.append({
                                "job_id": job_id,
                                "title": title,
                                "company": company,
                                "location": location,
                                "category": kw,
                                "experience_level": exp_level,
                                "original_description": raw_desc,
                                "cleaned_description": cleaned_desc,
                                "job_type": "Full-time",
                                "source_url": canonical_url,
                                "source_api": "LinkedIn (Egypt)",
                                "country": "Egypt"
                            })
                            added += 1
                            if added >= limit_per_keyword:
                                break
                print(f"  ├ LinkedIn Egypt ['{kw}']: {added} jobs.")
            time.sleep(0.2)
        except Exception as e:
            print(f"  ├ [WARNING] LinkedIn error for '{kw}': {e}")
            
    print(f"✅ Total LinkedIn Egypt jobs fetched: {len(all_jobs)}")
    return all_jobs


# ======================================================================
# 6. JOBICY API (jobicy.com)
# ======================================================================
def fetch_jobicy_jobs(count: int = 40) -> list:
    """Fetch live remote jobs with seniority from Jobicy API."""
    all_jobs = []
    seen_ids = set()
    print("\n[6/8] Fetching live tech jobs from Jobicy API...")
    industries = ["engineering", "data-science", "devops", "design-multimedia", "qa", "product"]
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for ind in industries:
        url = f"https://jobicy.com/api/v2/remote-jobs?count={count}&industry={ind}"
        try:
            res = requests.get(url, headers=headers, timeout=12)
            if res.status_code == 200:
                data = res.json()
                jobs = data.get("jobs", [])
                added = 0
                for job in jobs:
                    job_id = f"jobicy_{job.get('id')}"
                    if job_id not in seen_ids:
                        seen_ids.add(job_id)
                        title = job.get("jobTitle", "").strip()
                        raw_desc = job.get("jobDescription", "") or job.get("jobExcerpt", "")
                        level_hint = job.get("jobLevel", "")
                        cleaned_desc = clean_html(raw_desc)
                        exp_level = SeniorityClassifier.classify_job_level(title, cleaned_desc, level_hint)
                        
                        all_jobs.append({
                            "job_id": job_id,
                            "title": title,
                            "company": job.get("companyName", "Tech Company").strip(),
                            "location": job.get("jobGeo", "Remote"),
                            "category": ind,
                            "experience_level": exp_level,
                            "original_description": raw_desc,
                            "cleaned_description": cleaned_desc,
                            "job_type": job.get("jobType", "Full-time"),
                            "source_url": job.get("url", ""),
                            "source_api": "Jobicy",
                            "country": "Global Remote"
                        })
                        added += 1
                print(f"  ├ Jobicy ['{ind}']: {added} jobs.")
            time.sleep(0.2)
        except Exception as e:
            print(f"  ├ [WARNING] Jobicy error for '{ind}': {e}")
            
    print(f"✅ Total jobs fetched from Jobicy: {len(all_jobs)}")
    return all_jobs


# ======================================================================
# 7. REMOTEOK API (remoteok.com)
# ======================================================================
def fetch_remoteok_jobs() -> list:
    """Fetch live remote developer, data, devops jobs from RemoteOK API."""
    all_jobs = []
    seen_ids = set()
    print("\n[7/8] Fetching live tech jobs from RemoteOK API...")
    url = "https://remoteok.com/api"
    headers = {"User-Agent": "CareerMatchingEngine/3.0"}
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            items = res.json()
            for job in items[1:]:
                job_id = f"remoteok_{job.get('id') or job.get('slug')}"
                if job_id not in seen_ids:
                    seen_ids.add(job_id)
                    title = job.get("position", "").strip()
                    if not title:
                        continue
                    raw_desc = job.get("description", "")
                    tags = ", ".join(job.get("tags", []))
                    cleaned_desc = clean_html(f"{raw_desc} Key Skills: {tags}")
                    exp_level = SeniorityClassifier.classify_job_level(title, cleaned_desc)
                    
                    all_jobs.append({
                        "job_id": job_id,
                        "title": title,
                        "company": job.get("company", "Remote Tech").strip(),
                        "location": job.get("location", "Remote"),
                        "category": "Tech & Engineering",
                        "experience_level": exp_level,
                        "original_description": raw_desc,
                        "cleaned_description": cleaned_desc,
                        "job_type": "Full-time",
                        "source_url": job.get("url", f"https://remoteok.com/remote-jobs/{job.get('slug', '')}"),
                        "source_api": "RemoteOK",
                        "country": "Global Remote"
                    })
            print(f"  ├ RemoteOK fetched {len(all_jobs)} jobs.")
    except Exception as e:
        print(f"  ├ [WARNING] RemoteOK error: {e}")
        
    print(f"✅ Total jobs fetched from RemoteOK: {len(all_jobs)}")
    return all_jobs


# ======================================================================
# 8. ARBEITNOW API (arbeitnow.com)
# ======================================================================
def fetch_arbeitnow_jobs(pages: int = 5) -> list:
    """Fetch live tech jobs from Arbeitnow Global API."""
    all_jobs = []
    seen_ids = set()
    print(f"\n[8/8] Fetching live tech jobs from Arbeitnow API ({pages} pages)...")
    
    for page in range(1, pages + 1):
        url = f"https://www.arbeitnow.com/api/job-board-api?page={page}"
        try:
            response = requests.get(url, timeout=12)
            if response.status_code == 200:
                data = response.json()
                jobs = data.get("data", [])
                if not jobs:
                    break
                added = 0
                for job in jobs:
                    job_slug = job.get("slug", "")
                    job_id = f"arbeitnow_{job_slug}"
                    if job_id not in seen_ids and job_slug:
                        seen_ids.add(job_id)
                        title = job.get("title", "").strip()
                    
                    # Strict Tech Filter: Only accept genuine tech & engineering roles from Arbeitnow
                    if not re.search(r'\b(software|developer|engineer|engineering|data scientist|data engineer|data science|machine learning|ai engineer|ai developer|deep learning|devops|cloud|sre|frontend|backend|full stack|fullstack|python|react|golang|java|mobile|ios|android|qa|security|architect|tech lead)\b', title, re.IGNORECASE):
                        continue
                    if re.search(r'\b(ausbildung|buchhalter|accountant|pflege|nurse|hotel|sales|vertrieb|recruiter|hr|marketing|kaufmann|einkauf|office|jurist|kundenservice)\b', title, re.IGNORECASE):
                        continue
                        raw_desc = job.get("description", "")
                        tags = ", ".join(job.get("tags", []))
                        cleaned_desc = clean_html(f"{raw_desc} Key Skills & Tags: {tags}" if tags else raw_desc)
                        exp_level = SeniorityClassifier.classify_job_level(title, cleaned_desc)
                        
                        all_jobs.append({
                            "job_id": job_id,
                            "title": title,
                            "company": job.get("company_name", "").strip(),
                            "location": "Remote" if job.get("remote") else job.get("location", "Global"),
                            "category": "Tech & Engineering",
                            "experience_level": exp_level,
                            "original_description": raw_desc,
                            "cleaned_description": cleaned_desc,
                            "job_type": ", ".join(job.get("job_types", [])) or "Full-time",
                            "source_url": job.get("url", ""),
                            "source_api": "Arbeitnow",
                            "country": "Global / Remote"
                        })
                        added += 1
                print(f"  ├ Arbeitnow [Page {page}/{pages}]: {added} jobs.")
            time.sleep(0.2)
        except Exception as e:
            print(f"  ├ [WARNING] Arbeitnow page {page}: {e}")
            
    print(f"✅ Total jobs fetched from Arbeitnow: {len(all_jobs)}")
    return all_jobs


# ======================================================================
# 9. TANQEEB SAUDI ARABIA (sa.tanqeeb.com) - Gulf Tech Jobs (🇸🇦)
# ======================================================================
def fetch_tanqeeb_saudi_jobs(limit_per_keyword: int = 15) -> list:
    """Fetches live tech and developer jobs from Tanqeeb Saudi Arabia (🇸🇦)."""
    keywords = [
        "Software Engineer", "Full Stack Developer", "Backend Developer", ".NET Developer",
        "Python", "Data Engineer", "Machine Learning", "DevOps Engineer",
        "Frontend Developer", "Flutter Developer"
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8"
    }
    all_jobs = []
    seen_ids = set()
    print("\n[9/12] Fetching live tech jobs from Tanqeeb (Saudi Arabia 🇸🇦)...")
    
    for kw in keywords:
        search_url = f"https://saudi.tanqeeb.com/jobs/search?keywords={requests.utils.quote(kw)}"
        try:
            res = requests.get(search_url, headers=headers, timeout=8)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                cards = soup.find_all("div", class_=lambda c: c and 'card-body' in c.lower() and 'search-job-card' in c.lower() if c else False)
                
                added = 0
                for card in cards:
                    title_elem = card.find("h2", class_="search-job-title") or card.find("a", class_="search-job-title-link")
                    if not title_elem:
                        continue
                    a_tag = title_elem.find("a") if title_elem.name != "a" else title_elem
                    if not a_tag:
                        continue
                        
                    title = a_tag.text.strip()
                    rel_url = a_tag.get("href", "")
                    job_url = "https://saudi.tanqeeb.com" + rel_url if rel_url.startswith("/") else rel_url
                    
                    id_match = re.search(r'/jobs/([0-9a-zA-Z_-]+)\.html', job_url)
                    job_id = f"tanqeeb_sa_{id_match.group(1)}" if id_match else f"tanqeeb_sa_{hash(job_url)}"
                    
                    if job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)
                    
                    comp_elem = card.find("div", class_="search-job-company-block") or card.find("div", class_="search-job-company-info")
                    company = comp_elem.text.strip() if comp_elem else "Saudi Tech Employer"
                    company = re.sub(r'\s+', ' ', company).strip()
                    if not company:
                        company = "Tech Company (Saudi Arabia)"
                        
                    loc_elem = card.find("span", class_="search-job-workplace-location")
                    location = loc_elem.text.replace("On-site -", "").replace("Remote -", "").strip() if loc_elem else "Riyadh, Saudi Arabia"
                    
                    full_desc = f"{title} at {company} in {location}. Aggregated via Tanqeeb Saudi Arabia. Direct corporate posting."
                    cleaned_desc = clean_html(full_desc)
                    exp_level = SeniorityClassifier.classify_job_level(title, cleaned_desc)
                    
                    all_jobs.append({
                        "job_id": job_id,
                        "title": title,
                        "company": company,
                        "location": location,
                        "category": kw,
                        "experience_level": exp_level,
                        "original_description": full_desc,
                        "cleaned_description": cleaned_desc,
                        "job_type": "Full-time",
                        "source_url": job_url,
                        "source_api": "Tanqeeb (Saudi Arabia)",
                        "country": "Saudi Arabia"
                    })
                    added += 1
                    if added >= limit_per_keyword:
                        break
                print(f"  ├ Tanqeeb SA ['{kw}']: fetched {added} jobs.")
            time.sleep(0.3)
        except Exception as e:
            print(f"  ├ [WARNING] Tanqeeb SA error for '{kw}': {e}")
            
    print(f"✅ Total Tanqeeb Saudi jobs fetched: {len(all_jobs)}")
    return all_jobs


# ======================================================================
# 10. TANQEEB UAE (ae.tanqeeb.com) - Dubai & Abu Dhabi Tech Jobs (🇦🇪)
# ======================================================================
def fetch_tanqeeb_uae_jobs(limit_per_keyword: int = 15) -> list:
    """Fetches live tech and developer jobs from Tanqeeb UAE (🇦🇪)."""
    keywords = [
        "Software Engineer", "Full Stack Developer", "Backend Developer", ".NET Developer",
        "Python", "Data Engineer", "Machine Learning", "DevOps Engineer",
        "Frontend Developer", "Flutter Developer"
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8"
    }
    all_jobs = []
    seen_ids = set()
    print("\n[10/12] Fetching live tech jobs from Tanqeeb (United Arab Emirates 🇦🇪)...")
    
    for kw in keywords:
        search_url = f"https://uae.tanqeeb.com/jobs/search?keywords={requests.utils.quote(kw)}"
        try:
            res = requests.get(search_url, headers=headers, timeout=8)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                cards = soup.find_all("div", class_=lambda c: c and 'card-body' in c.lower() and 'search-job-card' in c.lower() if c else False)
                
                added = 0
                for card in cards:
                    title_elem = card.find("h2", class_="search-job-title") or card.find("a", class_="search-job-title-link")
                    if not title_elem:
                        continue
                    a_tag = title_elem.find("a") if title_elem.name != "a" else title_elem
                    if not a_tag:
                        continue
                        
                    title = a_tag.text.strip()
                    rel_url = a_tag.get("href", "")
                    job_url = "https://uae.tanqeeb.com" + rel_url if rel_url.startswith("/") else rel_url
                    
                    id_match = re.search(r'/jobs/([0-9a-zA-Z_-]+)\.html', job_url)
                    job_id = f"tanqeeb_ae_{id_match.group(1)}" if id_match else f"tanqeeb_ae_{hash(job_url)}"
                    
                    if job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)
                    
                    comp_elem = card.find("div", class_="search-job-company-block") or card.find("div", class_="search-job-company-info")
                    company = comp_elem.text.strip() if comp_elem else "UAE Tech Employer"
                    company = re.sub(r'\s+', ' ', company).strip()
                    if not company:
                        company = "Tech Company (UAE)"
                        
                    loc_elem = card.find("span", class_="search-job-workplace-location")
                    location = loc_elem.text.replace("On-site -", "").replace("Remote -", "").strip() if loc_elem else "Dubai, UAE"
                    
                    full_desc = f"{title} at {company} in {location}. Aggregated via Tanqeeb UAE. Direct corporate posting."
                    cleaned_desc = clean_html(full_desc)
                    exp_level = SeniorityClassifier.classify_job_level(title, cleaned_desc)
                    
                    all_jobs.append({
                        "job_id": job_id,
                        "title": title,
                        "company": company,
                        "location": location,
                        "category": kw,
                        "experience_level": exp_level,
                        "original_description": full_desc,
                        "cleaned_description": cleaned_desc,
                        "job_type": "Full-time",
                        "source_url": job_url,
                        "source_api": "Tanqeeb (UAE)",
                        "country": "United Arab Emirates"
                    })
                    added += 1
                    if added >= limit_per_keyword:
                        break
                print(f"  ├ Tanqeeb UAE ['{kw}']: fetched {added} jobs.")
            time.sleep(0.3)
        except Exception as e:
            print(f"  ├ [WARNING] Tanqeeb UAE error for '{kw}': {e}")
            
    print(f"✅ Total Tanqeeb UAE jobs fetched: {len(all_jobs)}")
    return all_jobs


# ======================================================================
# 11. REMOTIVE API (remotive.com) - Global High-Comp Remote Tech (🌐)
# ======================================================================
def fetch_remotive_jobs(categories: list = None) -> list:
    """Fetches high-paying global remote tech jobs from Remotive official API."""
    if categories is None:
        categories = ["software-dev", "data", "devops"]
        
    all_jobs = []
    seen_ids = set()
    print("\n[11/12] Fetching live tech jobs from Remotive API (Global High-Comp Remote 🌐)...")
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    for cat in categories:
        url = f"https://remotive.com/api/remote-jobs?category={cat}&limit=50"
        try:
            res = requests.get(url, headers=headers, timeout=12)
            if res.status_code == 200:
                data = res.json()
                jobs = data.get("jobs", [])
                added = 0
                for job in jobs:
                    job_id = f"remotive_{job.get('id', hash(job.get('title', '')))}"
                    if job_id not in seen_ids:
                        seen_ids.add(job_id)
                        title = job.get("title", "").strip()
                        comp = job.get("company_name", "Remote Tech Company").strip()
                        loc = job.get("candidate_required_location", "Worldwide Remote").strip() or "Worldwide Remote"
                        salary = job.get("salary", "")
                        raw_desc = job.get("description", "")
                        if salary:
                            raw_desc = f"Compensation: {salary}\n" + raw_desc
                        cleaned_desc = clean_html(raw_desc)
                        exp_level = SeniorityClassifier.classify_job_level(title, cleaned_desc)
                        
                        all_jobs.append({
                            "job_id": job_id,
                            "title": title,
                            "company": comp,
                            "location": loc,
                            "category": job.get("category", cat),
                            "experience_level": exp_level,
                            "original_description": raw_desc[:2500],
                            "cleaned_description": cleaned_desc[:2500],
                            "job_type": job.get("job_type", "Full-time"),
                            "source_url": job.get("url", "https://remotive.com"),
                            "source_api": "Remotive API",
                            "country": "Global Remote"
                        })
                        added += 1
                print(f"  ├ Remotive ['{cat}']: fetched {added} jobs.")
            time.sleep(0.3)
        except Exception as e:
            print(f"  ├ [WARNING] Remotive error for '{cat}': {e}")
            
    print(f"✅ Total Remotive jobs fetched: {len(all_jobs)}")
    return all_jobs


# ======================================================================
# 12. GREENHOUSE ATS APIS (Canonical, GitLab, Elastic) - Direct Tech Giants (🏢)
# ======================================================================
def fetch_greenhouse_tech_jobs(companies: list = None) -> list:
    """Fetches direct open roles from top tech giants & open-source leaders via Greenhouse API."""
    if companies is None:
        companies = ["canonical", "gitlab", "elastic"]
        
    all_jobs = []
    seen_ids = set()
    print("\n[12/12] Fetching direct corporate jobs from Tech Giants (Greenhouse ATS APIs 🏢)...")
    
    headers = {"User-Agent": "CareerMatchingEngine/3.0"}
    for comp in companies:
        url = f"https://boards-api.greenhouse.io/v1/boards/{comp}/jobs?content=true"
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 200:
                data = res.json()
                jobs = data.get("jobs", [])
                added = 0
                for job in jobs:
                    title = job.get("title", "").strip()
                    job_id = f"gh_{comp}_{job.get('id')}"
                    if job_id not in seen_ids:
                        seen_ids.add(job_id)
                        loc_obj = job.get("location", {})
                        location = loc_obj.get("name", "Remote / Global") if isinstance(loc_obj, dict) else "Remote"
                        raw_desc = job.get("content", f"{title} at {comp.capitalize()}")
                        cleaned_desc = clean_html(raw_desc)
                        exp_level = SeniorityClassifier.classify_job_level(title, cleaned_desc)
                        
                        all_jobs.append({
                            "job_id": job_id,
                            "title": title,
                            "company": comp.capitalize(),
                            "location": location,
                            "category": "Software Engineering & Cloud",
                            "experience_level": exp_level,
                            "original_description": raw_desc[:3000],
                            "cleaned_description": cleaned_desc[:3000],
                            "job_type": "Full-time",
                            "source_url": job.get("absolute_url", f"https://boards.greenhouse.io/{comp}"),
                            "source_api": f"Greenhouse ({comp.capitalize()})",
                            "country": "Global Remote"
                        })
                        added += 1
                print(f"  ├ Greenhouse [{comp.capitalize()}]: fetched {added} jobs.")
            time.sleep(0.3)
        except Exception as e:
            print(f"  ├ [WARNING] Greenhouse error for '{comp}': {e}")
            
    print(f"✅ Total Greenhouse jobs fetched: {len(all_jobs)}")
    return all_jobs


# ======================================================================
# DATASET MERGE, DEDUPLICATION & CLASSIFICATION
# ======================================================================
def load_and_upgrade_existing_jobs(file_path: str) -> list:
    """Loads existing jobs and ensures each has experience_level classified."""
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            jobs = json.load(f)
        for j in jobs:
            if "experience_level" not in j or not j["experience_level"]:
                j["experience_level"] = SeniorityClassifier.classify_job_level(
                    j.get("title", ""), j.get("cleaned_description", "")
                )
        return jobs
    except Exception:
        return []

def deduplicate_jobs(jobs_list: list) -> list:
    """Deduplicates jobs based on normalized Title + Company."""
    unique_jobs = []
    seen = set()
    
    for job in jobs_list:
        key = f"{job.get('title', '').lower()}|{job.get('company', '').lower()}"
        if key not in seen and job.get('title'):
            seen.add(key)
            if "experience_level" not in job:
                job["experience_level"] = SeniorityClassifier.classify_job_level(
                    job.get("title", ""), job.get("cleaned_description", "")
                )
            unique_jobs.append(job)
            
    return unique_jobs

if __name__ == "__main__":
    print("=" * 75)
    print("🚀 12-SOURCE COMPREHENSIVE MULTI-REGION TECH JOB COLLECTOR")
    print("   [Wuzzuf + Tanqeeb EG + Tanqeeb SA + Tanqeeb UAE + Himalayas + WWR +")
    print("    LinkedIn + Jobicy + RemoteOK + Arbeitnow + Remotive + Greenhouse Tech Giants]")
    print("=" * 75)
    
    output_dir = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "jobs_dataset.json")
    
    # 1. Load existing jobs
    existing_jobs = load_and_upgrade_existing_jobs(output_file)
    print(f"Loaded {len(existing_jobs)} existing jobs.\n")
    
    # 2. Fetch from all 12 sources
    wuzzuf_jobs = fetch_wuzzuf_jobs(limit_per_keyword=15)
    tanqeeb_jobs = fetch_tanqeeb_egypt_jobs(limit_per_keyword=15)
    saudi_jobs = fetch_tanqeeb_saudi_jobs(limit_per_keyword=15)
    uae_jobs = fetch_tanqeeb_uae_jobs(limit_per_keyword=15)
    himalayas_jobs = fetch_himalayas_jobs(limit=50)
    wwr_jobs = fetch_weworkremotely_jobs()
    linkedin_jobs = fetch_linkedin_egypt_jobs(limit_per_keyword=15)
    jobicy_jobs = fetch_jobicy_jobs(count=40)
    remoteok_jobs = fetch_remoteok_jobs()
    arbeitnow_jobs = fetch_arbeitnow_jobs(pages=5)
    remotive_jobs = fetch_remotive_jobs()
    greenhouse_jobs = fetch_greenhouse_tech_jobs()
    
    # 3. Combine & Deduplicate
    all_combined = (
        existing_jobs + wuzzuf_jobs + tanqeeb_jobs + saudi_jobs + uae_jobs +
        himalayas_jobs + wwr_jobs + linkedin_jobs + jobicy_jobs +
        remoteok_jobs + arbeitnow_jobs + remotive_jobs + greenhouse_jobs
    )
    final_jobs = deduplicate_jobs(all_combined)
    
    # 4. Generate Stats
    level_counts = {}
    source_counts = {}
    egypt_count = 0
    saudi_count = 0
    uae_count = 0
    
    for j in final_jobs:
        lvl = j.get("experience_level", "Mid-Level")
        src = j.get("source_api", "Unknown")
        level_counts[lvl] = level_counts.get(lvl, 0) + 1
        source_counts[src] = source_counts.get(src, 0) + 1
        
        loc = (j.get("location", "") + " " + j.get("country", "")).lower()
        if any(k in loc for k in ["egypt", "cairo", "giza", "alexandria", "maadi"]):
            egypt_count += 1
        elif any(k in loc for k in ["saudi", "ksa", "riyadh", "jeddah", "dammam"]):
            saudi_count += 1
        elif any(k in loc for k in ["uae", "emirates", "dubai", "abu dhabi", "sharjah"]):
            uae_count += 1
            
    print("\n" + "=" * 75)
    print(f"📊 DATASET COLLECTION & CLASSIFICATION REPORT:")
    print(f"  ├ Total Unique Active Jobs: {len(final_jobs)}")
    print(f"  ├ Jobs Located in Egypt 🇪🇬: {egypt_count}")
    print(f"  ├ Jobs Located in Saudi Arabia 🇸🇦: {saudi_count}")
    print(f"  ├ Jobs Located in UAE 🇦🇪: {uae_count}")
    print(f"  ├ Gulf Region Total (🇸🇦 + 🇦🇪): {saudi_count + uae_count}")
    print(f"  ├ Global & Remote Tech Jobs 🌐: {len(final_jobs) - (egypt_count + saudi_count + uae_count)}")
    print("  │")
    print("  ├ 🌐 Sources Breakdown:")
    for src, count in sorted(source_counts.items(), key=lambda x: -x[1]):
        print(f"      • {src:<32} : {count:>4} jobs")
    print("  │")
    print("  └ 🎯 Experience Level Breakdown:")
    for lvl, count in sorted(level_counts.items(), key=lambda x: -x[1]):
        pct = (count / len(final_jobs)) * 100
        print(f"      • {lvl:<28} : {count:>4} jobs ({pct:.1f}%)")
    print("=" * 75)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_jobs, f, ensure_ascii=False, indent=4)
        
    print(f"\n[SUCCESS] Dataset saved to: {output_file}\n")

    # 5. Automatically partition dataset by Country and Remote status
    try:
        from partition_jobs import partition_and_save_jobs
        partition_and_save_jobs(output_file)
    except Exception as e:
        print(f"⚠️ Note: Partitioning skipped or encountered: {e}")

    # 6. Upsert to SQLite Database
    db_path = os.path.join(output_dir, "jobs.db")
    try:
        from src.database import JobsDatabase
        db = JobsDatabase(db_path)
        new_cnt, upd_cnt = db.bulk_import_jobs(final_jobs, show_progress=False)
        print(f"🗄️ [DB UPDATE] SQLite database synced: {new_cnt} new, {upd_cnt} updated ({db_path})")
    except Exception as e:
        print(f"⚠️ Note: SQLite sync skipped: {e}")

    # 7. Automatically synchronize to final project/ai_engine
    final_proj_dir = os.path.abspath(os.path.join(project_root, "..", "final project", "ai_engine"))
    if os.path.exists(final_proj_dir):
        try:
            import shutil
            dest_dataset = os.path.join(final_proj_dir, "data", "processed", "jobs_dataset.json")
            dest_db = os.path.join(final_proj_dir, "data", "processed", "jobs.db")
            os.makedirs(os.path.dirname(dest_dataset), exist_ok=True)
            shutil.copy2(output_file, dest_dataset)
            if os.path.exists(db_path):
                shutil.copy2(db_path, dest_db)
            print("✅ Synchronized newly collected jobs to final project/ai_engine!")
        except Exception as e:
            print(f"⚠️ Note: Final project sync skipped: {e}")

