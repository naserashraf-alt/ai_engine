"""
=============================================================================
src/database.py - Central Relational Database Engine (SQLite & FTS5)
=============================================================================

Purpose:
- Manages the central jobs database (jobs.db) with high-speed indexed queries
  and real-time FTS5 full-text search.
- Handles atomic operations, WAL mode concurrency, and relational mapping.

Managed Tables:
1. jobs: Active job records, metadata, country partitions, and remote work modes.
2. skills & job_skills: Relational taxonomy mapping jobs to extracted skills.
3. candidates: Extracted CV profiles and candidate attributes.
4. reports & report_evaluations: Career advisor reports, match scores, and gap milestones.
5. jobs_fts: Real-time Porter-tokenized FTS5 full-text search index.

Dependencies:
- Calls: config.py
- Imported in: src/matcher.py, src/api_server.py, app.py, run_agent.py, scripts/*
=============================================================================
"""

import os
import re
import json
import sqlite3
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager
from datetime import datetime

try:
    from config import DB_PATH
except ImportError:
    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "processed", "jobs.db")


class JobsDatabase:
    """SQLite database manager for the jobs dataset."""

    DEFAULT_DB_PATH = DB_PATH

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or self.DEFAULT_DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_conn(self):
        """Context manager for database connections with WAL mode for concurrency."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        """Creates all tables and indexes if they don't exist."""
        with self._get_conn() as conn:
            conn.executescript("""
                -- ============================================================
                -- Main Jobs Table
                -- ============================================================
                CREATE TABLE IF NOT EXISTS jobs (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id          TEXT UNIQUE NOT NULL,
                    title           TEXT NOT NULL,
                    company         TEXT NOT NULL DEFAULT '',
                    location        TEXT NOT NULL DEFAULT '',
                    country         TEXT NOT NULL DEFAULT '',
                    category        TEXT DEFAULT '',
                    experience_level TEXT DEFAULT 'Mid-Level',
                    job_type        TEXT DEFAULT 'Full-time',
                    source_url      TEXT DEFAULT '',
                    source_api      TEXT DEFAULT '',
                    cleaned_description TEXT DEFAULT '',
                    original_description TEXT DEFAULT '',
                    posted_at       TEXT DEFAULT '',
                    
                    -- Partition metadata (auto-computed)
                    normalized_country TEXT DEFAULT '',
                    is_remote       INTEGER DEFAULT 0,
                    work_mode       TEXT DEFAULT 'On-site',
                    
                    -- Timestamps
                    created_at      TEXT DEFAULT (datetime('now')),
                    updated_at      TEXT DEFAULT (datetime('now'))
                );

                -- ============================================================
                -- Skills Table (Many-to-Many with Jobs)
                -- ============================================================
                CREATE TABLE IF NOT EXISTS skills (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    name            TEXT UNIQUE NOT NULL,
                    name_lower      TEXT UNIQUE NOT NULL
                );

                CREATE TABLE IF NOT EXISTS job_skills (
                    job_id          INTEGER NOT NULL,
                    skill_id        INTEGER NOT NULL,
                    PRIMARY KEY (job_id, skill_id),
                    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
                    FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE
                );

                -- ============================================================
                -- Sources Table (Track scraping sources metadata)
                -- ============================================================
                CREATE TABLE IF NOT EXISTS scrape_runs (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_name     TEXT NOT NULL,
                    jobs_fetched    INTEGER DEFAULT 0,
                    jobs_new        INTEGER DEFAULT 0,
                    jobs_closed     INTEGER DEFAULT 0,
                    run_at          TEXT DEFAULT (datetime('now')),
                    duration_sec    REAL DEFAULT 0,
                    status          TEXT DEFAULT 'completed'
                );

                -- ============================================================
                -- Candidates Table (Extracted CV Profiles)
                -- ============================================================
                CREATE TABLE IF NOT EXISTS candidates (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name       TEXT NOT NULL DEFAULT '',
                    headline        TEXT DEFAULT '',
                    email           TEXT DEFAULT '',
                    phone           TEXT DEFAULT '',
                    location        TEXT DEFAULT '',
                    primary_domain  TEXT DEFAULT '',
                    seniority_level TEXT DEFAULT 'Junior',
                    total_years_experience REAL DEFAULT 0.0,
                    professional_summary TEXT DEFAULT '',
                    skills_flat     TEXT DEFAULT '',
                    profile_json    TEXT NOT NULL,
                    source_filename TEXT DEFAULT '',
                    created_at      TEXT DEFAULT (datetime('now')),
                    updated_at      TEXT DEFAULT (datetime('now'))
                );

                -- ============================================================
                -- Career Agent Reports Table
                -- ============================================================
                CREATE TABLE IF NOT EXISTS reports (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_name  TEXT NOT NULL DEFAULT '',
                    target_domain   TEXT DEFAULT '',
                    seniority_assessment TEXT DEFAULT '',
                    executive_arabic_summary TEXT DEFAULT '',
                    executive_english_summary TEXT DEFAULT '',
                    report_json     TEXT NOT NULL,
                    source_cv       TEXT DEFAULT '',
                    created_at      TEXT DEFAULT (datetime('now'))
                );

                -- ============================================================
                -- Job Evaluations Table (Relational breakdown of report evaluations)
                -- ============================================================
                CREATE TABLE IF NOT EXISTS report_evaluations (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id       INTEGER NOT NULL,
                    job_rank        INTEGER DEFAULT 1,
                    job_id          TEXT NOT NULL,
                    job_title       TEXT NOT NULL,
                    company         TEXT DEFAULT '',
                    location        TEXT DEFAULT '',
                    source_url      TEXT DEFAULT '',
                    agent_match_score REAL DEFAULT 0.0,
                    agent_skills_score REAL DEFAULT 0.0,
                    agent_seniority_score REAL DEFAULT 0.0,
                    agent_gap_points_to_100 REAL DEFAULT 0.0,
                    matched_skills  TEXT DEFAULT '',
                    missing_skills  TEXT DEFAULT '',
                    scoring_rationale TEXT DEFAULT '',
                    exact_action_to_100 TEXT DEFAULT '',
                    cover_letter    TEXT DEFAULT '',
                    linkedin_pitch  TEXT DEFAULT '',
                    FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE
                );

                -- ============================================================
                -- Partitions Metadata Summary Table
                -- ============================================================
                CREATE TABLE IF NOT EXISTS partition_summaries (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    total_jobs      INTEGER DEFAULT 0,
                    total_remote    INTEGER DEFAULT 0,
                    summary_json    TEXT NOT NULL,
                    updated_at      TEXT DEFAULT (datetime('now'))
                );

                -- ============================================================
                -- Indexes for Fast Queries
                -- ============================================================
                CREATE INDEX IF NOT EXISTS idx_jobs_country ON jobs(country);
                CREATE INDEX IF NOT EXISTS idx_jobs_normalized_country ON jobs(normalized_country);
                CREATE INDEX IF NOT EXISTS idx_jobs_is_remote ON jobs(is_remote);
                CREATE INDEX IF NOT EXISTS idx_jobs_experience_level ON jobs(experience_level);
                CREATE INDEX IF NOT EXISTS idx_jobs_source_api ON jobs(source_api);
                CREATE INDEX IF NOT EXISTS idx_jobs_title ON jobs(title);
                CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company);
                CREATE INDEX IF NOT EXISTS idx_skills_name_lower ON skills(name_lower);
                CREATE INDEX IF NOT EXISTS idx_candidates_name ON candidates(full_name);
                CREATE INDEX IF NOT EXISTS idx_candidates_domain ON candidates(primary_domain);
                CREATE INDEX IF NOT EXISTS idx_reports_candidate ON reports(candidate_name);
                CREATE INDEX IF NOT EXISTS idx_evaluations_report ON report_evaluations(report_id);

                -- Full-Text Search index on title + description + company
                CREATE VIRTUAL TABLE IF NOT EXISTS jobs_fts USING fts5(
                    job_id_ref,
                    title,
                    company,
                    cleaned_description,
                    content='jobs',
                    content_rowid='id',
                    tokenize='porter unicode61'
                );

                -- Triggers to keep FTS in sync
                CREATE TRIGGER IF NOT EXISTS jobs_ai AFTER INSERT ON jobs BEGIN
                    INSERT INTO jobs_fts(rowid, job_id_ref, title, company, cleaned_description)
                    VALUES (new.id, new.job_id, new.title, new.company, new.cleaned_description);
                END;

                CREATE TRIGGER IF NOT EXISTS jobs_ad AFTER DELETE ON jobs BEGIN
                    INSERT INTO jobs_fts(jobs_fts, rowid, job_id_ref, title, company, cleaned_description)
                    VALUES ('delete', old.id, old.job_id, old.title, old.company, old.cleaned_description);
                END;

                CREATE TRIGGER IF NOT EXISTS jobs_au AFTER UPDATE ON jobs BEGIN
                    INSERT INTO jobs_fts(jobs_fts, rowid, job_id_ref, title, company, cleaned_description)
                    VALUES ('delete', old.id, old.job_id, old.title, old.company, old.cleaned_description);
                    INSERT INTO jobs_fts(rowid, job_id_ref, title, company, cleaned_description)
                    VALUES (new.id, new.job_id, new.title, new.company, new.cleaned_description);
                END;
            """)
            # Ensure schema migrations for cover_letter & linkedin_pitch
            for col in ["cover_letter", "linkedin_pitch"]:
                try:
                    conn.execute(f"ALTER TABLE report_evaluations ADD COLUMN {col} TEXT DEFAULT ''")
                except Exception:
                    pass

    # ==============================================================
    # CRUD Operations
    # ==============================================================

    @staticmethod
    def _to_str(val: Any, default: str = "") -> str:
        """Safely normalizes any value (list, dict, int, float, None) to string."""
        if val is None:
            return default
        if isinstance(val, list):
            return ", ".join(str(x).strip() for x in val if x)
        if isinstance(val, dict):
            return json.dumps(val, ensure_ascii=False)
        return str(val).strip()

    def upsert_job(self, job: Dict[str, Any], conn: Optional[sqlite3.Connection] = None) -> bool:
        """
        Insert or update a single job record. Returns True if new, False if updated.
        Can accept an external connection for batch operations.
        """
        def _do_upsert(c: sqlite3.Connection) -> bool:
            job_id = self._to_str(job.get("job_id", ""))
            title = self._to_str(job.get("title", ""))
            company = self._to_str(job.get("company", ""))
            
            if not job_id:
                job_id = f"auto_{hashlib.md5((title + company).encode()).hexdigest()[:12]}"

            location = self._to_str(job.get("location", ""))
            country = self._to_str(job.get("country", ""))
            category = self._to_str(job.get("category", ""))
            experience_level = self._to_str(job.get("experience_level", "Mid-Level"), "Mid-Level")
            job_type = self._to_str(job.get("job_type", "Full-time"), "Full-time")
            source_url = self._to_str(job.get("source_url", ""))
            source_api = self._to_str(job.get("source_api", ""))
            cleaned_description = self._to_str(job.get("cleaned_description", ""))
            original_description = self._to_str(job.get("original_description", ""))
            posted_at = self._to_str(job.get("posted_at", job.get("date_posted", "")))
            normalized_country = self._to_str(job.get("normalized_country", ""))
            
            # Boolean/Integer is_remote
            is_remote_raw = job.get("is_remote", False)
            if isinstance(is_remote_raw, str):
                is_remote_val = 1 if is_remote_raw.lower() in ("true", "1", "yes", "remote") else 0
            else:
                is_remote_val = 1 if bool(is_remote_raw) else 0

            work_mode = self._to_str(job.get("work_mode", "On-site"), "On-site")

            # Check if exists
            existing = c.execute("SELECT id FROM jobs WHERE job_id = ?", (job_id,)).fetchone()

            if existing:
                c.execute("""
                    UPDATE jobs SET
                        title = ?, company = ?, location = ?, country = ?,
                        category = ?, experience_level = ?, job_type = ?,
                        source_url = ?, source_api = ?,
                        cleaned_description = ?, original_description = ?,
                        posted_at = ?,
                        normalized_country = ?, is_remote = ?, work_mode = ?,
                        updated_at = datetime('now')
                    WHERE job_id = ?
                """, (
                    title, company, location, country,
                    category, experience_level, job_type,
                    source_url, source_api,
                    cleaned_description, original_description,
                    posted_at, normalized_country, is_remote_val,
                    work_mode, job_id
                ))
                row_id = existing["id"]
                is_new = False
            else:
                cursor = c.execute("""
                    INSERT INTO jobs (
                        job_id, title, company, location, country,
                        category, experience_level, job_type,
                        source_url, source_api,
                        cleaned_description, original_description,
                        posted_at,
                        normalized_country, is_remote, work_mode
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job_id, title, company, location, country,
                    category, experience_level, job_type,
                    source_url, source_api,
                    cleaned_description, original_description,
                    posted_at, normalized_country, is_remote_val,
                    work_mode
                ))
                row_id = cursor.lastrowid
                is_new = True

            # Handle skills (many-to-many)
            skills = job.get("required_skills") or job.get("skills") or []
            if isinstance(skills, str):
                skills = [s.strip() for s in skills.split(",") if s.strip()]
            elif not isinstance(skills, list):
                skills = []

            if skills and row_id:
                # Clear existing skills for this job
                c.execute("DELETE FROM job_skills WHERE job_id = ?", (row_id,))
                for skill_name in skills:
                    skill_name = str(skill_name).strip()
                    if not skill_name:
                        continue
                    skill_lower = skill_name.lower()
                    # Upsert skill
                    c.execute("INSERT OR IGNORE INTO skills (name, name_lower) VALUES (?, ?)", (skill_name, skill_lower))
                    skill_row = c.execute("SELECT id FROM skills WHERE name_lower = ?", (skill_lower,)).fetchone()
                    if skill_row:
                        c.execute("INSERT OR IGNORE INTO job_skills (job_id, skill_id) VALUES (?, ?)", (row_id, skill_row["id"]))

            return is_new

        if conn:
            return _do_upsert(conn)
        else:
            with self._get_conn() as c:
                return _do_upsert(c)

    def bulk_import_jobs(self, jobs: List[Dict[str, Any]], show_progress: bool = True) -> Tuple[int, int]:
        """
        Bulk import a list of job dicts into the database.
        Returns (new_count, updated_count).
        """
        new_count = 0
        updated_count = 0
        total = len(jobs)

        with self._get_conn() as conn:
            for idx, job in enumerate(jobs):
                is_new = self.upsert_job(job, conn=conn)
                if is_new:
                    new_count += 1
                else:
                    updated_count += 1

                if show_progress and (idx + 1) % 500 == 0:
                    print(f"  ⏳ Imported {idx + 1}/{total} jobs... ({new_count} new, {updated_count} updated)")

        if show_progress:
            print(f"  ✅ Import complete: {new_count} new + {updated_count} updated = {total} total processed")

        return new_count, updated_count

    def delete_job(self, job_id: str) -> bool:
        """Delete a job by its job_id. Returns True if deleted."""
        with self._get_conn() as conn:
            cursor = conn.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
            return cursor.rowcount > 0

    def delete_jobs_batch(self, job_ids: List[str]) -> int:
        """Delete multiple jobs by job_id. Returns count deleted."""
        with self._get_conn() as conn:
            deleted = 0
            for jid in job_ids:
                cursor = conn.execute("DELETE FROM jobs WHERE job_id = ?", (jid,))
                deleted += cursor.rowcount
            return deleted

    # ==============================================================
    # Query Operations
    # ==============================================================

    def get_total_count(self) -> int:
        """Returns total number of jobs in the database."""
        with self._get_conn() as conn:
            row = conn.execute("SELECT COUNT(*) as cnt FROM jobs").fetchone()
            return row["cnt"]

    def get_all_jobs(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Returns all jobs as a list of dicts (with skills)."""
        with self._get_conn() as conn:
            if limit:
                rows = conn.execute("SELECT * FROM jobs ORDER BY id LIMIT ?", (limit,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM jobs ORDER BY id").fetchall()
            return [self._row_to_dict(conn, row) for row in rows]

    def get_jobs_by_country(self, normalized_country: str) -> List[Dict[str, Any]]:
        """Returns jobs filtered by normalized country."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE normalized_country = ? ORDER BY id",
                (normalized_country,)
            ).fetchall()
            return [self._row_to_dict(conn, row) for row in rows]

    def get_remote_jobs(self) -> List[Dict[str, Any]]:
        """Returns all remote jobs."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE is_remote = 1 ORDER BY id"
            ).fetchall()
            return [self._row_to_dict(conn, row) for row in rows]

    def get_jobs_by_source(self, source_api: str) -> List[Dict[str, Any]]:
        """Returns jobs filtered by source API."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE source_api = ? ORDER BY id",
                (source_api,)
            ).fetchall()
            return [self._row_to_dict(conn, row) for row in rows]

    def search_jobs(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Full-text search across title, company, and description."""
        with self._get_conn() as conn:
            # Use FTS5 for fast full-text search
            rows = conn.execute("""
                SELECT j.* FROM jobs j
                INNER JOIN jobs_fts fts ON j.id = fts.rowid
                WHERE jobs_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query, limit)).fetchall()
            return [self._row_to_dict(conn, row) for row in rows]

    def get_jobs_for_matching(
        self,
        country: Optional[str] = None,
        remote_only: bool = False,
        normalized_country: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Returns jobs optimized for the matcher.
        Replaces the old JSON file loading approach.
        """
        with self._get_conn() as conn:
            conditions = []
            params = []

            if remote_only:
                conditions.append("is_remote = 1")
            elif normalized_country:
                conditions.append("normalized_country = ?")
                params.append(normalized_country)
            elif country:
                # Map country aliases to normalized_country values
                alias_map = {
                    "egypt": "Egypt", "cairo": "Egypt", "alexandria": "Egypt",
                    "saudi": "Saudi_Arabia", "saudi arabia": "Saudi_Arabia",
                    "ksa": "Saudi_Arabia", "riyadh": "Saudi_Arabia",
                    "uae": "UAE", "dubai": "UAE", "emirates": "UAE",
                    "germany": "Germany", "berlin": "Germany", "munich": "Germany",
                    "uk": "United_Kingdom", "united kingdom": "United_Kingdom", "london": "United_Kingdom",
                    "france": "France", "paris": "France",
                    "usa": "USA", "us": "USA", "united states": "USA",
                    "netherlands": "Netherlands", "holland": "Netherlands", "amsterdam": "Netherlands",
                    "switzerland": "Switzerland", "zurich": "Switzerland",
                    "remote": None,  # Will be handled as remote_only
                }
                normalized = alias_map.get(country.lower().strip())
                if normalized is None:
                    conditions.append("is_remote = 1")
                elif normalized:
                    conditions.append("normalized_country = ?")
                    params.append(normalized)

            where_clause = " AND ".join(conditions) if conditions else "1=1"
            rows = conn.execute(f"SELECT * FROM jobs WHERE {where_clause} ORDER BY id", params).fetchall()
            return [self._row_to_dict(conn, row) for row in rows]

    # ==============================================================
    # Statistics & Analytics
    # ==============================================================

    def get_stats(self) -> Dict[str, Any]:
        """Returns comprehensive database statistics."""
        with self._get_conn() as conn:
            total = conn.execute("SELECT COUNT(*) as cnt FROM jobs").fetchone()["cnt"]
            remote = conn.execute("SELECT COUNT(*) as cnt FROM jobs WHERE is_remote = 1").fetchone()["cnt"]
            unique_skills = conn.execute("SELECT COUNT(*) as cnt FROM skills").fetchone()["cnt"]
            unique_companies = conn.execute("SELECT COUNT(DISTINCT company) as cnt FROM jobs").fetchone()["cnt"]

            # By country
            country_rows = conn.execute("""
                SELECT normalized_country, COUNT(*) as cnt 
                FROM jobs 
                GROUP BY normalized_country 
                ORDER BY cnt DESC
            """).fetchall()
            by_country = {row["normalized_country"] or "Unknown": row["cnt"] for row in country_rows}

            # By experience level
            level_rows = conn.execute("""
                SELECT experience_level, COUNT(*) as cnt 
                FROM jobs 
                GROUP BY experience_level 
                ORDER BY cnt DESC
            """).fetchall()
            by_level = {row["experience_level"]: row["cnt"] for row in level_rows}

            # By source
            source_rows = conn.execute("""
                SELECT source_api, COUNT(*) as cnt 
                FROM jobs 
                GROUP BY source_api 
                ORDER BY cnt DESC
            """).fetchall()
            by_source = {row["source_api"]: row["cnt"] for row in source_rows}

            # Top skills
            top_skills_rows = conn.execute("""
                SELECT s.name, COUNT(js.job_id) as usage_count
                FROM skills s
                INNER JOIN job_skills js ON s.id = js.skill_id
                GROUP BY s.id
                ORDER BY usage_count DESC
                LIMIT 30
            """).fetchall()
            top_skills = {row["name"]: row["usage_count"] for row in top_skills_rows}

            return {
                "total_jobs": total,
                "total_remote": remote,
                "total_onsite": total - remote,
                "unique_skills": unique_skills,
                "unique_companies": unique_companies,
                "by_country": by_country,
                "by_experience_level": by_level,
                "by_source": by_source,
                "top_skills": top_skills,
                "db_path": self.db_path,
                "db_size_mb": round(os.path.getsize(self.db_path) / (1024 * 1024), 2) if os.path.exists(self.db_path) else 0
            }

    def get_skills_for_job(self, job_internal_id: int, conn: sqlite3.Connection) -> List[str]:
        """Returns list of skill names for a given job's internal ID."""
        rows = conn.execute("""
            SELECT s.name FROM skills s
            INNER JOIN job_skills js ON s.id = js.skill_id
            WHERE js.job_id = ?
            ORDER BY s.name
        """, (job_internal_id,)).fetchall()
        return [row["name"] for row in rows]

    # ==============================================================
    # Export Operations (DB → JSON)
    # ==============================================================

    def export_to_json(self, output_path: str, country: Optional[str] = None, remote_only: bool = False) -> int:
        """
        Export jobs from the database back to JSON format.
        Useful for backward compatibility and data portability.
        Returns the number of jobs exported.
        """
        if remote_only:
            jobs = self.get_remote_jobs()
        elif country:
            jobs = self.get_jobs_by_country(country)
        else:
            jobs = self.get_all_jobs()

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(jobs, f, ensure_ascii=False, indent=2)

        return len(jobs)

    def export_partitioned(self, base_dir: Optional[str] = None) -> Dict[str, int]:
        """
        Export all country partitions + all_remote + gulf_region to by_country/ directory.
        Returns dict of filename → count.
        """
        if not base_dir:
            base_dir = os.path.join(os.path.dirname(self.db_path), "by_country")
        os.makedirs(base_dir, exist_ok=True)

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
            "Other_International": "jobs_other_international.json",
        }

        results = {}
        for country_key, filename in country_files.items():
            jobs = self.get_jobs_by_country(country_key)
            path = os.path.join(base_dir, filename)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(jobs, f, ensure_ascii=False, indent=2)
            results[filename] = len(jobs)

        # All remote
        remote_jobs = self.get_remote_jobs()
        path = os.path.join(base_dir, "jobs_all_remote.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(remote_jobs, f, ensure_ascii=False, indent=2)
        results["jobs_all_remote.json"] = len(remote_jobs)

        # Gulf region
        saudi_jobs = self.get_jobs_by_country("Saudi_Arabia")
        uae_jobs = self.get_jobs_by_country("UAE")
        gulf_jobs = saudi_jobs + uae_jobs
        path = os.path.join(base_dir, "jobs_gulf_region.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(gulf_jobs, f, ensure_ascii=False, indent=2)
        results["jobs_gulf_region.json"] = len(gulf_jobs)

        # Summary index
        stats = self.get_stats()
        summary = {
            "total_jobs": stats["total_jobs"],
            "total_remote_jobs": stats["total_remote"],
            "files_breakdown": results,
            "exported_at": datetime.now().isoformat()
        }
        path = os.path.join(base_dir, "summary_index.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        # Also store in partition_summaries table
        self.save_partition_summary(summary)

        return results

    # ==============================================================
    # Candidate Profile Operations (CVs in DB)
    # ==============================================================

    def save_candidate(self, profile_data: Dict[str, Any], source_filename: str = "", conn: Optional[sqlite3.Connection] = None) -> int:
        """
        Saves or updates an extracted candidate profile in the candidates table.
        Returns the candidate ID.
        """
        p_info = profile_data.get("personal_info") or {}
        full_name = self._to_str(p_info.get("full_name") or profile_data.get("candidate_name") or "Candidate")
        headline = self._to_str(p_info.get("headline", ""))
        email = self._to_str(p_info.get("email", ""))
        phone = self._to_str(p_info.get("phone", ""))
        location = self._to_str(p_info.get("location", ""))
        primary_domain = self._to_str(profile_data.get("primary_domain", "Software Engineering"))
        seniority = self._to_str(profile_data.get("seniority_level", "Junior"))
        years_exp = float(profile_data.get("total_years_experience") or 0.0)
        summary = self._to_str(profile_data.get("professional_summary", ""))
        
        flat_skills = profile_data.get("normalized_skills_flat") or []
        skills_str = ", ".join(str(s) for s in flat_skills) if isinstance(flat_skills, list) else str(flat_skills)
        profile_json = json.dumps(profile_data, ensure_ascii=False)

        def _do_save_cand(c: sqlite3.Connection) -> int:
            existing = None
            if email:
                existing = c.execute("SELECT id FROM candidates WHERE email = ? AND email != ''", (email,)).fetchone()
            if not existing and full_name:
                existing = c.execute("SELECT id FROM candidates WHERE full_name = ?", (full_name,)).fetchone()

            if existing:
                cid = existing["id"]
                c.execute("""
                    UPDATE candidates SET
                        full_name = ?, headline = ?, email = ?, phone = ?,
                        location = ?, primary_domain = ?, seniority_level = ?,
                        total_years_experience = ?, professional_summary = ?,
                        skills_flat = ?, profile_json = ?, source_filename = ?,
                        updated_at = datetime('now')
                    WHERE id = ?
                """, (
                    full_name, headline, email, phone, location,
                    primary_domain, seniority, years_exp, summary,
                    skills_str, profile_json, source_filename, cid
                ))
                return cid
            else:
                cursor = c.execute("""
                    INSERT INTO candidates (
                        full_name, headline, email, phone, location,
                        primary_domain, seniority_level, total_years_experience,
                        professional_summary, skills_flat, profile_json,
                        source_filename
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    full_name, headline, email, phone, location,
                    primary_domain, seniority, years_exp, summary,
                    skills_str, profile_json, source_filename
                ))
                return cursor.lastrowid

        if conn:
            return _do_save_cand(conn)
        else:
            with self._get_conn() as c:
                return _do_save_cand(c)

    def get_candidate(self, candidate_id: int) -> Optional[Dict[str, Any]]:
        """Returns a candidate by ID."""
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,)).fetchone()
            if row:
                d = dict(row)
                d["profile"] = json.loads(d["profile_json"])
                return d
            return None

    def get_all_candidates(self) -> List[Dict[str, Any]]:
        """Returns all candidates."""
        with self._get_conn() as conn:
            rows = conn.execute("SELECT id, full_name, headline, email, primary_domain, seniority_level, total_years_experience, source_filename, created_at FROM candidates ORDER BY id DESC").fetchall()
            return [dict(r) for r in rows]

    # ==============================================================
    # Career Agent Report Operations (Reports in DB)
    # ==============================================================

    def save_report(
        self,
        report_data: Dict[str, Any],
        candidate_profile: Optional[Dict[str, Any]] = None,
        source_cv: str = ""
    ) -> int:
        """
        Saves a CareerAgentReport into the reports table and breaks out
        the job evaluations into report_evaluations.
        Returns report ID.
        """
        rep = report_data.get("career_agent_report") if "career_agent_report" in report_data else report_data
        cand = candidate_profile or report_data.get("candidate_profile") or {}

        cand_name = self._to_str(rep.get("candidate_name") or (cand.get("personal_info") or {}).get("full_name") or "Candidate")
        target_domain = self._to_str(rep.get("target_domain") or cand.get("primary_domain") or "Engineering")
        seniority = self._to_str(rep.get("seniority_assessment", ""))
        arabic_summary = self._to_str(rep.get("executive_arabic_summary", ""))
        english_summary = self._to_str(rep.get("executive_english_summary", ""))
        
        full_report_wrapper = {
            "candidate_profile": cand,
            "career_agent_report": rep
        }
        report_json = json.dumps(full_report_wrapper, ensure_ascii=False)

        with self._get_conn() as conn:
            cursor = conn.execute("""
                INSERT INTO reports (
                    candidate_name, target_domain, seniority_assessment,
                    executive_arabic_summary, executive_english_summary,
                    report_json, source_cv
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                cand_name, target_domain, seniority,
                arabic_summary, english_summary, report_json, source_cv
            ))
            report_id = cursor.lastrowid

            # Save individual job evaluations
            evals = rep.get("job_evaluations") or []
            for ev in evals:
                conn.execute("""
                    INSERT INTO report_evaluations (
                        report_id, job_rank, job_id, job_title, company,
                        location, source_url, agent_match_score,
                        agent_skills_score, agent_seniority_score,
                        agent_gap_points_to_100, matched_skills,
                        missing_skills, scoring_rationale, exact_action_to_100,
                        cover_letter, linkedin_pitch
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    report_id,
                    int(ev.get("job_rank", 1)),
                    self._to_str(ev.get("job_id", "")),
                    self._to_str(ev.get("job_title", "Software Engineer")),
                    self._to_str(ev.get("company", "")),
                    self._to_str(ev.get("location", "")),
                    self._to_str(ev.get("source_url", "")),
                    float(ev.get("agent_match_score", 0.0)),
                    float(ev.get("agent_skills_score", 0.0)),
                    float(ev.get("agent_seniority_score", 0.0)),
                    float(ev.get("agent_gap_points_to_100", 0.0)),
                    self._to_str(ev.get("matched_skills", [])),
                    self._to_str(ev.get("missing_skills", [])),
                    self._to_str(ev.get("scoring_rationale", "")),
                    self._to_str(ev.get("exact_action_to_100", "")),
                    self._to_str(ev.get("cover_letter", "")),
                    self._to_str(ev.get("linkedin_pitch", ""))
                ))

            # Also ensure candidate is saved if profile is present
            if cand:
                self.save_candidate(cand, source_filename=source_cv, conn=conn)

            return report_id

    def get_all_reports(self) -> List[Dict[str, Any]]:
        """Returns all reports summary list."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT id, candidate_name, target_domain, seniority_assessment,
                       source_cv, created_at,
                       (SELECT COUNT(*) FROM report_evaluations re WHERE re.report_id = r.id) as evaluations_count,
                       (SELECT MAX(agent_match_score) FROM report_evaluations re WHERE re.report_id = r.id) as top_match_score
                FROM reports r
                ORDER BY id DESC
            """).fetchall()
            return [dict(r) for r in rows]

    def get_report(self, report_id: int) -> Optional[Dict[str, Any]]:
        """Returns full report dict by ID."""
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
            if row:
                d = dict(row)
                d["report"] = json.loads(d["report_json"])
                eval_rows = conn.execute("SELECT * FROM report_evaluations WHERE report_id = ? ORDER BY job_rank", (report_id,)).fetchall()
                d["evaluations"] = [dict(r) for r in eval_rows]
                return d
            return None

    # ==============================================================
    # Partition Summaries
    # ==============================================================

    def save_partition_summary(self, summary_data: Dict[str, Any]):
        """Saves partition metadata summary to database."""
        with self._get_conn() as conn:
            conn.execute("DELETE FROM partition_summaries")
            conn.execute("""
                INSERT INTO partition_summaries (total_jobs, total_remote, summary_json)
                VALUES (?, ?, ?)
            """, (
                int(summary_data.get("total_jobs", 0)),
                int(summary_data.get("total_remote_jobs", 0)),
                json.dumps(summary_data, ensure_ascii=False)
            ))

    def get_partition_summary(self) -> Optional[Dict[str, Any]]:
        """Returns partition summary."""
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM partition_summaries ORDER BY id DESC LIMIT 1").fetchone()
            if row:
                return json.loads(row["summary_json"])
            return None

    # ==============================================================
    # Master JSON Importer
    # ==============================================================

    def import_all_existing_jsons(self, project_root: Optional[str] = None) -> Dict[str, int]:
        """
        Scans all directories for existing JSON files:
        - data/extracted_cvs/*.json -> candidates table
        - data/agent_reports/*.json -> reports table
        - data/processed/by_country/summary_index.json -> partition_summaries table
        Returns counts of records imported.
        """
        if not project_root:
            project_root = os.path.dirname(os.path.dirname(self.db_path))

        counts = {
            "candidates_imported": 0,
            "reports_imported": 0,
            "summaries_imported": 0
        }

        # 1. Extracted CVs
        cvs_dir = os.path.join(project_root, "data", "extracted_cvs")
        if os.path.exists(cvs_dir):
            for fname in os.listdir(cvs_dir):
                if fname.endswith(".json"):
                    fpath = os.path.join(cvs_dir, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        self.save_candidate(data, source_filename=fname)
                        counts["candidates_imported"] += 1
                    except Exception as e:
                        print(f"⚠️ Error importing candidate {fname}: {e}")

        # 2. Agent Reports
        reports_dir = os.path.join(project_root, "data", "agent_reports")
        if os.path.exists(reports_dir):
            for fname in os.listdir(reports_dir):
                if fname.endswith(".json"):
                    fpath = os.path.join(reports_dir, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        self.save_report(data, source_cv=fname)
                        counts["reports_imported"] += 1
                    except Exception as e:
                        print(f"⚠️ Error importing report {fname}: {e}")

        # 3. Partition Summary
        summary_path = os.path.join(project_root, "data", "processed", "by_country", "summary_index.json")
        if os.path.exists(summary_path):
            try:
                with open(summary_path, "r", encoding="utf-8") as f:
                    s_data = json.load(f)
                self.save_partition_summary(s_data)
                counts["summaries_imported"] += 1
            except Exception as e:
                print(f"⚠️ Error importing summary: {e}")

        return counts

    # ==============================================================
    # Maintenance Operations
    # ==============================================================

    def vacuum(self):
        """Reclaims unused space in the database file."""
        with self._get_conn() as conn:
            conn.execute("VACUUM")

    def rebuild_fts(self):
        """Rebuilds the full-text search index."""
        with self._get_conn() as conn:
            conn.execute("INSERT INTO jobs_fts(jobs_fts) VALUES('rebuild')")

    # ==============================================================
    # Internal Helpers
    # ==============================================================

    def _row_to_dict(self, conn: sqlite3.Connection, row: sqlite3.Row) -> Dict[str, Any]:
        """Converts a database row to a dict matching the original JSON schema."""
        d = dict(row)
        # Get skills for this job
        d["required_skills"] = self.get_skills_for_job(d["id"], conn)
        # Convert is_remote from int to bool
        d["is_remote"] = bool(d.get("is_remote", 0))
        # Remove internal fields for clean output
        d.pop("id", None)
        d.pop("created_at", None)
        d.pop("updated_at", None)
        return d


# ==============================================================
# Convenience Functions
# ==============================================================

def get_db(db_path: Optional[str] = None) -> JobsDatabase:
    """Factory function to get a database instance."""
    return JobsDatabase(db_path)


def migrate_json_to_db(json_path: str, db_path: Optional[str] = None, partition_data: bool = True) -> JobsDatabase:
    """
    One-shot migration: Imports all jobs from a JSON file into a new SQLite database.
    Optionally applies the country/remote partitioning logic.
    """
    print("=" * 70)
    print("🚀 JSON → SQLite DATABASE MIGRATION")
    print("=" * 70)

    if not os.path.exists(json_path):
        print(f"❌ JSON file not found: {json_path}")
        return None

    # Load JSON data
    print(f"📂 Loading JSON data from: {json_path}")
    with open(json_path, "r", encoding="utf-8") as f:
        jobs = json.load(f)
    print(f"  ├ Loaded {len(jobs)} job records")

    # Apply partition metadata if needed
    if partition_data:
        print("  ├ Computing country/remote partition metadata...")
        from scripts.partition_jobs import detect_country_and_mode
        for job in jobs:
            if not job.get("normalized_country"):
                cntry, is_rem, mode = detect_country_and_mode(job)
                job["normalized_country"] = cntry
                job["is_remote"] = is_rem
                job["work_mode"] = mode

    # Create database and import
    db = JobsDatabase(db_path)
    print(f"  ├ Database file: {db.db_path}")
    print(f"  ├ Importing {len(jobs)} jobs into SQLite...")

    new_count, updated_count = db.bulk_import_jobs(jobs)

    # Stats
    stats = db.get_stats()
    print(f"\n{'=' * 70}")
    print(f"📊 MIGRATION COMPLETE!")
    print(f"  ├ Total Jobs in DB: {stats['total_jobs']}")
    print(f"  ├ Remote Jobs: {stats['total_remote']}")
    print(f"  ├ Unique Skills: {stats['unique_skills']}")
    print(f"  ├ Unique Companies: {stats['unique_companies']}")
    print(f"  ├ DB File Size: {stats['db_size_mb']} MB")
    print(f"  │")
    print(f"  ├ 🌍 By Country:")
    for country, count in stats["by_country"].items():
        print(f"      • {country:<28} : {count:>4} jobs")
    print(f"  │")
    print(f"  ├ 🎯 By Experience Level:")
    for level, count in stats["by_experience_level"].items():
        pct = (count / stats['total_jobs']) * 100 if stats['total_jobs'] > 0 else 0
        print(f"      • {level:<28} : {count:>4} jobs ({pct:.1f}%)")
    print(f"  │")
    print(f"  ├ 🔗 By Source:")
    for source, count in stats["by_source"].items():
        print(f"      • {source:<32} : {count:>4} jobs")
    print(f"{'=' * 70}\n")

    return db
