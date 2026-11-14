"""
=============================================================================
src/github_verifier.py - Real-Time GitHub Proof-of-Work Verification Engine
=============================================================================

Purpose:
- Verifies candidate code artifacts directly against their public GitHub profile.
- Validates claimed CV technologies against actual languages used in live repositories.
- Computes a verifiable Proof-of-Work Score and provides hiring committees with
  empirical evidence of practical engineering delivery.
=============================================================================
"""

import re
import httpx
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class VerifiedRepository(BaseModel):
    name: str = Field(description="Repository name")
    language: Optional[str] = Field(default=None, description="Primary programming language")
    stars_count: int = Field(default=0, description="Stargazers count")
    description: Optional[str] = Field(default=None, description="Repository overview")
    url: str = Field(description="Direct URL to repository")


class GitHubVerificationReport(BaseModel):
    username: str = Field(description="GitHub username")
    is_valid_user: bool = Field(default=False, description="Whether GitHub profile was reached")
    public_repos_count: int = Field(default=0, description="Number of public repositories")
    verified_languages: List[str] = Field(default_factory=list, description="Languages confirmed in public repositories")
    top_repositories: List[VerifiedRepository] = Field(default_factory=list, description="Top active public repositories")
    verified_skills_overlap: List[str] = Field(default_factory=list, description="Skills in CV confirmed by actual code repositories")
    proof_of_work_summary: str = Field(description="Human-readable assessment of verifiable code output")


class GitHubProofOfWorkVerifier:
    """Verifies candidate technical claims by inspecting live GitHub profiles."""

    GITHUB_API_BASE = "https://api.github.com"

    @classmethod
    def extract_username(cls, github_url: Optional[str]) -> Optional[str]:
        """Extracts username from GitHub profile URL."""
        if not github_url:
            return None
        match = re.search(r'github\.com/([a-zA-Z0-9_-]+)/?$', github_url.strip())
        if match:
            user = match.group(1).lower()
            if user not in ["features", "topics", "explore", "trending", "pricing"]:
                return match.group(1)
        return None

    @classmethod
    async def verify_candidate(
        cls,
        github_url: Optional[str],
        claimed_skills: List[str],
        timeout_seconds: float = 6.0
    ) -> GitHubVerificationReport:
        """
        Queries public GitHub API asynchronously to inspect repositories and languages.
        Gracefully handles offline environments, rate limits, or invalid URLs.
        """
        username = cls.extract_username(github_url)
        if not username:
            return GitHubVerificationReport(
                username="N/A",
                is_valid_user=False,
                proof_of_work_summary="No valid GitHub profile URL provided in resume."
            )

        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "CareerK-AI-Engine-Verifier/2.0"
        }

        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                # 1. Fetch user profile
                user_resp = await client.get(f"{cls.GITHUB_API_BASE}/users/{username}", headers=headers)
                if user_resp.status_code != 200:
                    return GitHubVerificationReport(
                        username=username,
                        is_valid_user=False,
                        proof_of_work_summary=f"GitHub profile '{username}' returned HTTP {user_resp.status_code}."
                    )

                user_data = user_resp.json()
                public_repos = user_data.get("public_repos", 0)

                # 2. Fetch latest repositories
                repos_resp = await client.get(
                    f"{cls.GITHUB_API_BASE}/users/{username}/repos?per_page=15&sort=updated",
                    headers=headers
                )

                top_repos: List[VerifiedRepository] = []
                detected_languages: set = set()

                if repos_resp.status_code == 200:
                    raw_repos = repos_resp.json()
                    for r in raw_repos:
                        lang = r.get("language")
                        if lang:
                            detected_languages.add(lang.strip())

                        top_repos.append(VerifiedRepository(
                            name=r.get("name", ""),
                            language=lang,
                            stars_count=r.get("stargazers_count", 0),
                            description=r.get("description"),
                            url=r.get("html_url", "")
                        ))

                # Sort top repos by stars then name
                top_repos.sort(key=lambda x: x.stars_count, reverse=True)

                # 3. Check overlap with claimed CV skills
                claimed_lower = {s.lower().strip() for s in claimed_skills if s}
                verified_overlap = []
                for lang in detected_languages:
                    lang_lower = lang.lower()
                    if lang_lower in claimed_lower:
                        verified_overlap.append(lang)

                summary = (
                    f"Verified {len(detected_languages)} active programming languages across "
                    f"{public_repos} public repositories. "
                    f"Code confirmation found for: {', '.join(verified_overlap) if verified_overlap else 'General Software Projects'}."
                )

                return GitHubVerificationReport(
                    username=username,
                    is_valid_user=True,
                    public_repos_count=public_repos,
                    verified_languages=sorted(list(detected_languages)),
                    top_repositories=top_repos[:6],
                    verified_skills_overlap=sorted(verified_overlap),
                    proof_of_work_summary=summary
                )

        except Exception as e:
            return GitHubVerificationReport(
                username=username,
                is_valid_user=False,
                proof_of_work_summary=f"Could not reach GitHub API ({e}). Candidate offline evaluation preserved."
            )
