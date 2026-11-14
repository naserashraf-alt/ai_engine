"""
=============================================================================
tests/test_api_server.py - Integration Test Suite for FastAPI Microservice
=============================================================================
"""

import sys
import os
import pytest
from fastapi.testclient import TestClient

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.api_server import app


def test_api_server_endpoints():
    print("=" * 80)
    print("🧪 Starting FastAPI Microservice Integration Tests (Careerk Contracts)")
    print("=" * 80)

    with TestClient(app) as client:
        # 1. Test Health Check
        print("\n🔹 1. Testing Health Check: GET /health")
        resp = client.get("/health")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] in ["yalla_neshtaghal_ai_engine", "ai_engine"]
        assert data["indexed_jobs_count"] >= 2500
        print(f"  ✅ Health check verified: {data['indexed_jobs_count']} active jobs indexed!")

        # 2. Test Direct Job Matching Endpoint
        print("\n🔹 2. Testing Direct Job Notification: POST /match/direct-job")
        direct_payload = {"jobId": "test-direct-job-uuid-12345"}
        resp = client.post("/match/direct-job", json=direct_payload)
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}"
        data = resp.json()
        assert data["type"] == "direct"
        assert data["status"] == "accepted"
        assert data["jobId"] == "test-direct-job-uuid-12345"
        print("  ✅ Immediate 201 Accepted response strictly matches NestJS contract!")

        # 3. Test Job Seeker Matching Endpoint
        print("\n🔹 3. Testing Job Seeker Recalculation: POST /match/job-seeker")
        seeker_payload = {
            "jobSeekerId": "test-job-seeker-uuid-67890",
            "requestId": "req-integration-001",
            "scrapedLookbackDays": 30
        }
        resp = client.post("/match/job-seeker", json=seeker_payload)
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}"
        data = resp.json()
        assert data["type"] == "job-seeker"
        assert data["status"] == "accepted"
        assert data["requestId"] == "req-integration-001"
        assert data["jobSeekerId"] == "test-job-seeker-uuid-67890"
        print("  ✅ Immediate 201 Accepted for candidate matching verified!")

        # 4. Test GitHub Verification Endpoint
        print("\n🔹 4. Testing Live GitHub Verification: POST /verify/github")
        gh_payload = {
            "githubUrl": "https://github.com/naserashraf-alt",
            "claimedSkills": ["python", "docker", "fastapi"]
        }
        resp = client.post("/verify/github", json=gh_payload)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        gh_data = resp.json()
        assert gh_data["username"] == "naserashraf-alt"
        assert "verified_languages" in gh_data
        print(f"  ✅ GitHub verification endpoint functional: {gh_data['proof_of_work_summary']}")


if __name__ == "__main__":
    test_api_server_endpoints()
    print("\n" + "=" * 80)
    print("🎉 All FastAPI Microservice Integration Tests passed 100%!")
    print("=" * 80)
