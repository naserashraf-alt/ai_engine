"""
=============================================================================
config.py - Central Configuration & System Environment Paths
=============================================================================

PURPOSE:
- Unified single source of truth for all directory and database paths across the project.
- Prevents fragile relative paths and guarantees stable cross-module connectivity.

MANAGED PATHS:
- Base project directory (BASE_DIR)
- Central SQLite database path (DB_PATH)
- Resume, reports, and processed datasets directories

DEPENDENCIES:
- Imported in: src/database.py, src/matcher.py, app.py, run_agent.py, extract_cv.py
=============================================================================
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Root project directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Data directories
DATA_DIR = os.path.join(BASE_DIR, "data")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
BY_COUNTRY_DIR = os.path.join(PROCESSED_DIR, "by_country")
SAMPLE_CVS_DIR = os.path.join(DATA_DIR, "sample_cvs")
EXTRACTED_CVS_DIR = os.path.join(DATA_DIR, "extracted_cvs")
AGENT_REPORTS_DIR = os.path.join(DATA_DIR, "agent_reports")

# Central SQLite database and primary dataset path
DB_PATH = os.path.join(PROCESSED_DIR, "jobs.db")
JOBS_DATASET_JSON = os.path.join(PROCESSED_DIR, "jobs_dataset.json")

# Ensure required core directories exist
for _d in [DATA_DIR, PROCESSED_DIR, BY_COUNTRY_DIR, SAMPLE_CVS_DIR, EXTRACTED_CVS_DIR, AGENT_REPORTS_DIR]:
    os.makedirs(_d, exist_ok=True)

# AI Provider Settings
DEFAULT_AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
