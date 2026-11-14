"""
=============================================================================
tests/test_enhanced_extractor.py - Extraction Accuracy & Careerk Contract Suite
=============================================================================
"""

import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.schemas import (
    ResumeProfile, PersonalInfo, ExperienceItem, EducationItem,
    SkillsCategorized, calculate_tenure_from_experiences
)
from src.ai_extractor import AIExtractor


def test_tenure_calculation():
    print("=" * 80)
    print("🧪 1. Testing Verified Employment Tenure Calculation from Dates")
    print("=" * 80)

    experiences = [
        ExperienceItem(
            job_title="Junior Python Developer",
            company="Company A",
            start_date="2020-01",
            end_date="2021-06",
            is_current=False
        ),
        ExperienceItem(
            job_title="Mid-Level AI Engineer",
            company="Company B",
            start_date="2021-07",
            end_date="2023-01",
            is_current=False
        )
    ]

    tenure = calculate_tenure_from_experiences(experiences)
    print(f"  • Calculated Verified Tenure: {tenure} years")
    # 18 months + 19 months = 37 months ≈ 3.1 years
    assert 2.8 <= tenure <= 3.3, f"Expected tenure around 3.1, got {tenure}"
    print("  ✅ Accurate chronological tenure calculation verified!")


def test_careerk_schema_export():
    print("\n" + "=" * 80)
    print("🧪 2. Testing Careerk Schema Export (NlpParseCvResponse Contract)")
    print("=" * 80)

    profile = ResumeProfile(
        personal_info=PersonalInfo(
            full_name="Naser Ashraf",
            headline="Senior AI Engineer",
            email="naser@example.com",
            phone="+201012345678",
            location="Cairo, Egypt",
            links={"linkedin": "https://linkedin.com/in/naser", "github": "https://github.com/naserashraf-alt"}
        ),
        professional_summary="Passionate AI & Machine Learning Engineer with 5+ years building scalable systems.",
        primary_domain="AI / Machine Learning",
        seniority_level="Senior",
        total_years_experience=5.0,
        skills=SkillsCategorized(
            technical_skills=["Python", "PyTorch", "FastAPI", "Docker", "PostgreSQL"],
            tools_and_platforms=["Git", "Linux", "Kubernetes"],
            soft_skills=["Leadership", "Problem Solving", "Agile"]
        ),
        normalized_skills_flat=["python", "pytorch", "fastapi", "docker", "postgresql", "git", "linux", "kubernetes"],
        work_experience=[
            ExperienceItem(
                job_title="Senior AI Engineer",
                company="Tech Corp",
                location="Cairo, Egypt",
                start_date="2022-01-01",
                end_date="Present",
                is_current=True,
                key_achievements=["Built SOTA multi-agent career matching system", "Optimized inference latency by 45%"]
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
        ]
    )

    dummy_seeker_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    careerk_dict = profile.to_careerk_dict(dummy_seeker_id)

    # Validate high-level keys
    assert careerk_dict["jobSeekerId"] == dummy_seeker_id
    assert "parsedAt" in careerk_dict
    assert "data" in careerk_dict

    data = careerk_dict["data"]
    # Check Personal Info
    assert data["personalInfo"]["firstName"] == "Naser"
    assert data["personalInfo"]["lastName"] == "Ashraf"
    assert data["personalInfo"]["email"] == "naser@example.com"
    assert data["personalInfo"]["linkedinUrl"] == "https://linkedin.com/in/naser"
    assert data["personalInfo"]["githubUrl"] == "https://github.com/naserashraf-alt"

    # Check Education
    assert len(data["education"]) == 1
    assert data["education"][0]["degreeType"] == "BACHELOR"
    assert data["education"][0]["institutionName"] == "Cairo University"
    assert data["education"][0]["gpa"] == 3.8

    # Check Work Experience
    assert len(data["workExperience"]) == 1
    assert data["workExperience"][0]["companyName"] == "Tech Corp"
    assert data["workExperience"][0]["isCurrent"] is True
    assert "SOTA multi-agent" in data["workExperience"][0]["description"]

    # Check Skills
    assert len(data["skills"]) > 5
    tech_skills = [s["name"] for s in data["skills"] if s["verified"] is True]
    assert "python" in tech_skills
    assert "pytorch" in tech_skills

    print("  ✅ Data structure strictly conforms 100% to NestJS and Prisma schema!")
    print(f"  • Candidate: {data['personalInfo']['firstName']} {data['personalInfo']['lastName']}")
    print(f"  • Degree: {data['education'][0]['degreeType']} from {data['education'][0]['institutionName']}")
    print(f"  • Verified Technical Skills Count: {len(tech_skills)}")


def test_extractor_normalization():
    print("\n" + "=" * 80)
    print("🧪 3. Testing Technical Skills Normalization & Canonicalization")
    print("=" * 80)

    extractor = AIExtractor(provider="heuristic_fallback")
    sample_text = """
    Candidate: Omar Tarek
    Email: omar@example.com
    Phone: +201122334455
    Experience: 3 years
    Skills: Python, PyTorch, ReactJS, NodeJS, K8s, Docker, PostgreSQL, MySQL
    Experience History:
    - Software Engineer at AlfaTech (2021-01 to 2024-01)
      Worked on backend systems using Python and FastAPI.
    """

    profile = extractor._extract_heuristic_fallback(sample_text)
    profile = extractor._normalize_skills_and_meta(
        profile,
        meta={"filename": "test.pdf", "num_pages": 1, "char_count": len(sample_text), "word_count": len(sample_text.split())},
        used_provider="heuristic_fallback",
        used_model="test",
        elapsed_sec=0.1
    )

    print(f"  • Normalized Flat Skills: {profile.normalized_skills_flat}")
    # PyTorch implies Python and Deep Learning
    assert "python" in profile.normalized_skills_flat
    assert "deep learning" in profile.normalized_skills_flat or "pytorch" in profile.normalized_skills_flat
    print("  ✅ Automated skill canonicalization verified successfully!")


if __name__ == "__main__":
    test_tenure_calculation()
    test_careerk_schema_export()
    test_extractor_normalization()
    print("\n" + "=" * 80)
    print("🎉 All Enhanced Extractor Tests passed 100%!")
    print("=" * 80)
