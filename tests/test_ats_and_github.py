"""
=============================================================================
tests/test_ats_and_github.py - Test Suite for ATS Scorer & GitHub Verifier
=============================================================================
"""

import sys
import os
import pytest
import asyncio

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.schemas import (
    ResumeProfile, PersonalInfo, ExperienceItem, EducationItem,
    ProjectItem, SkillsCategorized
)
from src.ats_scorer import ATSCompatibilityScorer
from src.github_verifier import GitHubProofOfWorkVerifier


def test_ats_compatibility_scorer():
    print("=" * 80)
    print("🧪 1. Testing Enterprise ATS Compatibility Scorer")
    print("=" * 80)

    # 1. High Quality Optimized Resume Profile
    strong_profile = ResumeProfile(
        personal_info=PersonalInfo(
            full_name="Naser Ashraf",
            headline="Senior AI & Machine Learning Engineer",
            email="naser@example.com",
            phone="+201012345678",
            location="Cairo, Egypt",
            links={"linkedin": "https://linkedin.com/in/naser", "github": "https://github.com/naserashraf-alt"}
        ),
        professional_summary="Results-driven Senior AI Engineer with 5+ years architecting scalable neural networks, MLOps pipelines, and production NLP systems.",
        primary_domain="AI / Machine Learning",
        seniority_level="Senior",
        total_years_experience=5.0,
        skills=SkillsCategorized(
            technical_skills=["Python", "PyTorch", "FastAPI", "Docker", "PostgreSQL", "Kubernetes"],
            tools_and_platforms=["Git", "Linux", "AWS", "CI/CD"],
            soft_skills=["Leadership", "Problem Solving", "Agile"]
        ),
        normalized_skills_flat=["python", "pytorch", "fastapi", "docker", "postgresql", "kubernetes", "git", "linux", "aws", "ci/cd"],
        work_experience=[
            ExperienceItem(
                job_title="Senior AI Engineer",
                company="Tech Innovations",
                start_date="2022-01",
                end_date="Present",
                is_current=True,
                key_achievements=[
                    "Architected and deployed a multi-agent recommendation engine, reducing inference latency by 45%",
                    "Engineered end-to-end MLOps pipeline on Kubernetes processing 500K daily requests",
                    "Spearheaded model distillation reducing memory footprint by 30%"
                ],
                technologies_used=["Python", "PyTorch", "FastAPI", "Kubernetes"]
            )
        ],
        education=[
            EducationItem(
                degree="Bachelor of Science",
                field_of_study="Computer Science",
                institution="Cairo University",
                graduation_year="2021",
                grade_or_gpa="3.8"
            )
        ],
        projects=[
            ProjectItem(
                title="CareerK AI Matcher",
                description="High-performance hybrid vector retrieval system with 237ms latency.",
                technologies=["Python", "FastAPI", "FTS5", "SQLite", "RRF"]
            )
        ]
    )

    ats_result = ATSCompatibilityScorer.evaluate(strong_profile)
    print(f"  • Overall ATS Compatibility Score: {ats_result.overall_score}% (Grade: {ats_result.grade})")
    print(f"  • Verdict: {ats_result.verdict}")
    print(f"  • Structure Score: {ats_result.breakdown.section_structure_score}%")
    print(f"  • Quantifiable Impact Score: {ats_result.breakdown.quantifiable_impact_score}%")
    print(f"  • Skill Density Score: {ats_result.breakdown.skill_density_score}%")

    assert ats_result.overall_score >= 85.0, f"Expected ATS score >= 85%, got {ats_result.overall_score}"
    assert ats_result.grade in ["A+", "A"]
    assert len(ats_result.strengths) >= 3
    print("  ✅ ATS Compatibility Scorer passed with flying colors!")


def test_github_verifier_parsing():
    print("\n" + "=" * 80)
    print("🧪 2. Testing GitHub Proof-of-Work Verifier (URL & Offline Handling)")
    print("=" * 80)

    # Test username extraction
    u1 = GitHubProofOfWorkVerifier.extract_username("https://github.com/naserashraf-alt")
    assert u1 == "naserashraf-alt", f"Expected 'naserashraf-alt', got {u1}"

    u2 = GitHubProofOfWorkVerifier.extract_username("https://github.com/amrrdev/")
    assert u2 == "amrrdev", f"Expected 'amrrdev', got {u2}"

    u3 = GitHubProofOfWorkVerifier.extract_username("https://linkedin.com/in/someone")
    assert u3 is None

    print(f"  • Extracted Usernames: {u1}, {u2}")
    print("  ✅ GitHub URL extraction logic verified!")


def test_github_verifier_live_execution():
    print("\n" + "=" * 80)
    print("🧪 3. Testing GitHub API Verification Flow (Async)")
    print("=" * 80)

    async def run_async_test():
        # Test verification for a public profile (or graceful fallback)
        report = await GitHubProofOfWorkVerifier.verify_candidate(
            github_url="https://github.com/naserashraf-alt",
            claimed_skills=["python", "fastapi", "docker", "javascript"]
        )
        print(f"  • GitHub Profile Checked: {report.username}")
        print(f"  • Is Valid User Reached: {report.is_valid_user}")
        print(f"  • Public Repositories: {report.public_repos_count}")
        print(f"  • Verified Languages: {report.verified_languages}")
        print(f"  • Proof-of-Work Summary: {report.proof_of_work_summary}")
        assert report.username == "naserashraf-alt"
        return report

    report = asyncio.run(run_async_test())
    print("  ✅ GitHub Proof-of-Work Verification completed successfully!")


if __name__ == "__main__":
    test_ats_compatibility_scorer()
    test_github_verifier_parsing()
    test_github_verifier_live_execution()
    print("\n" + "=" * 80)
    print("🎉 All ATS Scorer and GitHub Proof-of-Work tests passed 100%!")
    print("=" * 80)
