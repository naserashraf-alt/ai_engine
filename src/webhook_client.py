"""
=============================================================================
src/webhook_client.py - Asynchronous Webhook Dispatcher for CareerK Backend
=============================================================================

Purpose:
- Dispatches matching completion callbacks to the Core NestJS backend server.
- Supports both Direct Job matching and Scraped Jobs matching notifications.
- Strictly adheres to the payload contracts documented in matching_api.md.
=============================================================================
"""

import os
import sys
import time
import httpx
from typing import Dict, Any, Optional
from datetime import datetime, timezone

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')


class CareerkWebhookClient:
    """Client for dispatching asynchronous callbacks to careerk NestJS backend."""

    def __init__(
        self,
        direct_callback_url: Optional[str] = None,
        scraped_callback_url: Optional[str] = None,
        timeout_seconds: float = 10.0
    ):
        self.direct_callback_url = direct_callback_url or os.getenv(
            "MATCHING_DIRECT_CALLBACK_URL",
            "http://localhost:3000/internal/matching/direct/completed"
        )
        self.scraped_callback_url = scraped_callback_url or os.getenv(
            "MATCHING_SCRAPED_CALLBACK_URL",
            "http://localhost:3000/internal/matching/scraped/completed"
        )
        self.timeout_seconds = timeout_seconds

    async def send_direct_completed(
        self,
        job_id: str,
        request_id: str,
        processed_candidates: int,
        upserted_matches: int,
        started_at: datetime,
        finished_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Sends success callback to POST /internal/matching/direct/completed
        """
        finished = finished_at or datetime.now(timezone.utc)
        payload = {
            "type": "direct",
            "status": "completed",
            "jobId": str(job_id),
            "requestId": str(request_id),
            "processedJobs": 1,
            "processedCandidates": int(processed_candidates),
            "upsertedMatches": int(upserted_matches),
            "startedAt": started_at.isoformat(),
            "finishedAt": finished.isoformat()
        }

        return await self._post_callback(self.direct_callback_url, payload)

    async def send_direct_failed(
        self,
        job_id: str,
        request_id: str,
        error_message: str,
        started_at: datetime,
        finished_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Sends failure callback to POST /internal/matching/direct/completed
        """
        finished = finished_at or datetime.now(timezone.utc)
        payload = {
            "type": "direct",
            "status": "failed",
            "jobId": str(job_id),
            "requestId": str(request_id),
            "error": str(error_message)[:200],
            "startedAt": started_at.isoformat(),
            "finishedAt": finished.isoformat()
        }

        return await self._post_callback(self.direct_callback_url, payload)

    async def send_scraped_completed(
        self,
        request_id: str,
        since: datetime,
        until: datetime,
        processed_jobs: int,
        processed_candidates: int,
        upserted_matches: int,
        started_at: datetime,
        finished_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Sends success callback to POST /internal/matching/scraped/completed
        """
        finished = finished_at or datetime.now(timezone.utc)
        payload = {
            "type": "scraped",
            "status": "completed",
            "since": since.isoformat(),
            "until": until.isoformat(),
            "requestId": str(request_id),
            "processedJobs": int(processed_jobs),
            "processedCandidates": int(processed_candidates),
            "upsertedMatches": int(upserted_matches),
            "startedAt": started_at.isoformat(),
            "finishedAt": finished.isoformat()
        }

        return await self._post_callback(self.scraped_callback_url, payload)

    async def _post_callback(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Sends HTTP POST with error handling and logging."""
        headers = {"Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code in [200, 201]:
                    return {"status": "delivered", "response": resp.json() if resp.text else {}}
                else:
                    return {
                        "status": "rejected",
                        "http_code": resp.status_code,
                        "error": resp.text
                    }
        except httpx.ConnectError:
            print(f"ℹ️ [Webhook Notice]: Careerk backend at {url} is not currently running. Callback logged safely.")
            return {"status": "backend_offline", "url": url}
        except Exception as e:
            print(f"⚠️ [Webhook Error]: Failed to post callback to {url}: {e}")
            return {"status": "error", "message": str(e)}
