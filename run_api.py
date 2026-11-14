"""
=============================================================================
run_api.py - Microservice Launcher (FastAPI on Port 8000)
=============================================================================
"""

import os
import sys
import time
import threading
import webbrowser

# Ensure working directory and sys.path are always ai_engine project root
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)
try:
    os.chdir(PROJECT_DIR)
except Exception:
    pass

from src.api_server import app
import uvicorn


def open_browser():
    """Automatically launches the browser to interactive Swagger API docs."""
    time.sleep(1.2)
    try:
        webbrowser.open("http://localhost:8000/docs")
    except Exception:
        pass


if __name__ == "__main__":
    print("=" * 80)
    print("🚀 Starting يلا نشتغل (Yalla Neshtaghal) AI Engine Microservice at http://localhost:8000")
    print("📚 Interactive Swagger API Docs: http://localhost:8000/docs")
    print("🌐 Opening documentation in your browser automatically...")
    print("=" * 80)

    # Launch browser in a background daemon thread
    threading.Thread(target=open_browser, daemon=True).start()

    # Run uvicorn server directly with the app instance
    uvicorn.run(app, host="0.0.0.0", port=8000)
