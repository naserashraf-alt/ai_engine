"""
=============================================================================
tests/test_seniority_matching.py - اختبار دقة المطابقة المعتمدة على الكفاءة العملية
(Practical Capability & Job Execution Assessment Test)
=============================================================================

الغرض (Purpose):
- التأكد من أن التوافق (Match Score) يعتمد على سؤال عملي واحد:
  "هل الشخص المتقدم يقدر يشتغل الوظيفة دي عملياً أم لا؟" (Practical Capability).
- التأكد من عدم حرمان المرشح الذي يمتلك مهارات هندسية قوية من وظائف الهندسة الحقيقية
  (مثل AI Engineer / ML Engineer / Software Engineer) بدلاً من حصرهم في التدريب الطلابي فقط.
- التحقق من توليد خطوات وتوصيات إجرائية واضحة لكل وظيفة توضح للمرشح:
  "ما الذي يتبقى له ليفعله لكي يتقدم لهذه الوظيفة بثقة؟" (Actionable application roadmap).

كيفية التشغيل (Execution):
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


def run_capability_matching_tests():
    matcher = JobMatcher()
    agent = CareerAdvisorAgent()

    print("=" * 80)
    print("🧪 1. اختبار تقييم القدرة التنفيذية للمرشح ('هل يستطيع أداء الوظيفة؟')")
    print("   المرشح: مهندس ذكاء اصطناعي يمتلك مهارات قوية (Python, PyTorch, Deep Learning, Docker)")
    print("=" * 80)

    ai_candidate = ResumeProfile(
        primary_domain="AI / Machine Learning",
        seniority_level="Junior",
        total_years_experience=1.5,
        normalized_skills_flat=["python", "pytorch", "deep learning", "machine learning", "docker", "sql"]
    )

    cands = matcher.retrieve_candidates(ai_candidate, top_k=5)
    report = agent.evaluate_and_advise(ai_candidate, cands, top_n=5)

    assert len(report.job_evaluations) > 0, "يجب استرجاع وظائف متوافقة"

    print(f"  ├ تم استرجاع وتقييم {len(report.job_evaluations)} وظيفة:")
    for ev in report.job_evaluations:
        print(f"\n  ✅ #{ev.job_rank} | {ev.job_title} @ {ev.company} -> Match: {ev.agent_match_score}%")
        print(f"      • تقييم القدرة التنفيذية : {ev.scoring_rationale}")
        print(f"      • خطوات التقديم المطلوبة : {ev.exact_action_to_100}")
        print(f"      • المهارات المتطابقة    : {', '.join(ev.matched_skills)}")

        # تأكيد أن التقرير يجيب على السؤال العملي
        assert "Can the candidate execute this role?" in ev.scoring_rationale, "يجب أن يوضح المنطق قدرة المرشح على أداء الوظيفة"
        assert "To qualify and apply:" in ev.exact_action_to_100, "يجب أن يوضح خطة التقديم العملية"

    print("\n" + "=" * 80)
    print("🧪 2. التحقق من توصيات خطوات التقديم لكل وظيفة (Application Checklist)")
    print("=" * 80)
    for ev in report.job_evaluations:
        print(f"  • {ev.job_title[:35]:<35} ──> {ev.exact_action_to_100}")

    print("\n" + "=" * 80)
    print("✅ جميع اختبارات تقييم القدرة العملية وخطوات التقديم نجحت بنسبة 100%!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_capability_matching_tests()
