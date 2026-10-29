"""
=============================================================================
config.py - إعدادات النظام والمسارات المركزية (Central Configuration & Paths)
=============================================================================

الغرض من الملف (Purpose):
- نقطة مرجعية موحدة لجميع مسارات المجلدات وقاعدة البيانات في المشروع.
- يمنع تكرار المسارات النسبية الهشة ويضمن اتصالاً قوياً بين جميع الموديولات.

المسارات المدارة (Managed Paths):
- مسار المشروع الأساسي (BASE_DIR)
- مسار قاعدة البيانات SQLite (DB_PATH)
- مسارات السير الذاتية والتقارير والبيانات المعالجة

الاتصالات والتبعيات (Dependencies & Connections):
- يُستورد في: src/database.py, src/matcher.py, app.py, run_agent.py, extract_cv.py
=============================================================================
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# تحميل المتغيرات البيئية من .env
load_dotenv()

# المسار الجذري للمشروع
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# مسارات مجلد البيانات (Data Directories)
DATA_DIR = os.path.join(BASE_DIR, "data")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
BY_COUNTRY_DIR = os.path.join(PROCESSED_DIR, "by_country")
SAMPLE_CVS_DIR = os.path.join(DATA_DIR, "sample_cvs")
EXTRACTED_CVS_DIR = os.path.join(DATA_DIR, "extracted_cvs")
AGENT_REPORTS_DIR = os.path.join(DATA_DIR, "agent_reports")

# مسار قاعدة البيانات المركزية SQLite
DB_PATH = os.path.join(PROCESSED_DIR, "jobs.db")
JOBS_DATASET_JSON = os.path.join(PROCESSED_DIR, "jobs_dataset.json")

# التأكد التلقائي من وجود المجلدات الأساسية
for _d in [DATA_DIR, PROCESSED_DIR, BY_COUNTRY_DIR, SAMPLE_CVS_DIR, EXTRACTED_CVS_DIR, AGENT_REPORTS_DIR]:
    os.makedirs(_d, exist_ok=True)

# إعدادات مزودي الذكاء الاصطناعي (AI Provider Settings)
DEFAULT_AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
