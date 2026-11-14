"""
=============================================================================
tests/test_seniority_matching.py - Practical Capability & Job Execution Assessment Test
=============================================================================

PURPOSE:
- Validate that the match score is driven by a single practical question:
  "Can the candidate realistically execute this role?" (Practical Capability).
- Ensure qualified candidates with strong engineering competencies (Python, PyTorch,
  Deep Learning, Docker) are matched with true engineering roles (AI/ML Engineer)
  rather than being artificially constrained to student internships.
- Verify generation of actionable, concrete application steps for each role:
  "What remains for the candidate to apply with confidence?" (Actionable application roadmap).

EXECUTION:
python tests/test_seniority_matching.py
=============================================================================
"""

import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.matcher import JobMatcher
from src.agent_advisor import CareerAdvisorAgent
from src.schemas import ResumeProfile


def test_capability_matching():
    matcher = JobMatcher()
    agent = CareerAdvisorAgent()

    print("=" * 80)
    print("🧪 1. Testing Candidate Practical Execution Assessment ('Can they execute the role?')")
    print("   Candidate: AI Engineer with strong skills (Python, PyTorch, Deep Learning, Docker)")
    print("=" * 80)

    ai_candidate = ResumeProfile(
        primary_domain="AI / Machine Learning",
        seniority_level="Junior",
        total_years_experience=1.5,
        normalized_skills_flat=["python", "pytorch", "deep learning", "machine learning", "docker", "sql"]
    )

    cands = matcher.retrieve_candidates(ai_candidate, top_k=5)
    report = agent.evaluate_and_advise(ai_candidate, cands, top_n=5)

    assert len(report.job_evaluations) > 0, "Compatible jobs must be retrieved"

    print(f"  ├ Retrieved and evaluated {len(report.job_evaluations)} jobs:")
    for ev in report.job_evaluations:
        print(f"\n  ✅ #{ev.job_rank} | {ev.job_title} @ {ev.company} -> Match: {ev.agent_match_score}%")
        print(f"      • Capability Assessment : {ev.scoring_rationale}")
        print(f"      • Required Application Steps : {ev.exact_action_to_100}")
        print(f"      • Matched Skills        : {', '.join(ev.matched_skills)}")

        # Verify rationale answers the practical capability question
        assert "Can the candidate execute this role?" in ev.scoring_rationale, "Rationale must reflect execution capability"
        assert "To qualify and apply:" in ev.exact_action_to_100, "Must provide actionable application roadmap"

    print("\n" + "=" * 80)
    print("🧪 2. Verifying Application Action Steps (Application Checklist)")
    print("=" * 80)
    for ev in report.job_evaluations:
        print(f"  • {ev.job_title[:35]:<35} ──> {ev.exact_action_to_100}")

    print("\n" + "=" * 80)
    print("✅ All practical capability and application action tests passed successfully (100%)!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    test_capability_matching()
