"""
=============================================================================
run_agent.py - المايسترو ومنفذ خط الأنابيب الكامل عبر Terminal (CLI Pipeline)
=============================================================================

الغرض (Purpose):
- تنفيذ خط الأنابيب الذكي كاملاً من سطر الأوامر (End-to-End Execution):
  1. استخراج الـ CV باستخدام AI Extractor.
  2. سحب أفضل الوظائف المتوافقة من قاعدة البيانات SQLite عبر JobMatcher.
  3. استدعاء CareerAdvisorAgent لحساب درجات التوافق وتحليل الفجوات وخطط ATS.
  4. طباعة النتائج في التيرمينال وحفظها تلقائياً في قاعدة البيانات jobs.db.

كيفية التشغيل (Execution):
python run_agent.py [اسم ملف السيرة الذاتية] [--country مصر] [--provider gemini]
=============================================================================
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.ai_extractor import AIExtractor
from src.matcher import JobMatcher
from src.agent_advisor import CareerAdvisorAgent
from src.schemas import ResumeProfile, CareerAgentReport, AgentJobEvaluation


def print_agent_report_to_terminal(
    profile: ResumeProfile,
    report: CareerAgentReport
):
    """Renders the executive AI Career Advisor report in the console."""
    p = profile.personal_info

    print("\n" + "═" * 80)
    print(f" 🚀 AI CAREER AGENT INTELLIGENCE REPORT: {p.full_name.upper() or 'CANDIDATE'}")
    print(f"    💼 Target Role: {profile.seniority_level} {profile.primary_domain}")
    print(f"    📧 {p.email or 'N/A'} | 📱 {p.phone or 'N/A'} | 📍 {p.location or 'Global'}")
    print("═" * 80)

    # 1. Top Matched Jobs Scored by AI
    print(f"\n🏆 TOP {len(report.job_evaluations)} MATCHED OPPORTUNITIES (PRACTICAL EXECUTION EVALUATION):")
    for ev in report.job_evaluations:
        print(f"\n   #{ev.job_rank} | Practical Match Score: {ev.agent_match_score}% ──> {ev.job_title}")
        print(f"        🏢 Company          : {ev.company} | 📍 Location: {ev.location}")
        print(f"        📊 Sub-Scores       : Skills Fit: {ev.agent_skills_score}% | Execution Readiness: {ev.agent_seniority_score}%")
        print(f"        🎯 Capability Gap   : Needs +{ev.agent_gap_points_to_100}% points to reach perfect execution fit")
        print(f"        🧠 Capability Check : {ev.scoring_rationale}")
        print(f"        📋 What to do to apply: {ev.exact_action_to_100}")
        print(f"        ✅ Matched Skills   : {', '.join(ev.matched_skills[:6]) if ev.matched_skills else 'Domain Baseline'}")
        if ev.missing_skills:
            print(f"        ❌ Missing Skills   : {', '.join(ev.missing_skills[:6])}")
        print(f"        🔗 Apply URL        : {ev.source_url}")

    # 2. Executive Arabic Summary
    print("\n" + "─" * 80)
    print(" 🌟 الملخص التنفيذي والاستراتيجي (Executive Arabic Strategy):")
    print("─" * 80)
    print(f"\n{report.executive_arabic_summary.strip()}\n")

    # 3. Deep Job Diagnostics
    print("─" * 80)
    print(" 🔬 DEEP JOB DIAGNOSTICS & INTERVIEW PREPARATION (BY AI AGENT):")
    print("─" * 80)
    for ev in report.job_evaluations:
        print(f"\n   [Job #{ev.job_rank}] {ev.job_title} @ {ev.company} ({ev.agent_match_score}%)")
        print(f"   💡 Why Matched    : {ev.why_matched}")
        print(f"   🎯 Action to 100% : {ev.exact_action_to_100}")
        print(f"   ❓ Interview Q    : \"{ev.likely_interview_question}\"")
        print(f"   🔑 Winning Tip    : {ev.model_interview_answer_tip}")

    # 4. ATS Resume Makeovers
    print("\n" + "─" * 80)
    print(" 📝 ZERO-SHOT ATS RESUME MAKEOVERS (Google XYZ Impact Formula):")
    print("─" * 80)
    for idx, m in enumerate(report.ats_resume_makeovers, 1):
        print(f"\n   [Makeover #{idx}] Section: {m.section}")
        print(f"   ❌ Before : \"{m.before_bullet}\"")
        print(f"   ✅ After  : \"{m.after_bullet}\"")
        print(f"   💡 Impact : {m.rationale}")

    # 5. 12-Week Production Roadmap
    print("\n" + "─" * 80)
    print(" 🗺️ 12-WEEK PRODUCTION CAREER ROADMAP:")
    print("─" * 80)
    for phase in report.production_roadmap:
        print(f"\n   📅 Phase {phase.phase_number}: {phase.phase_title} ({phase.duration_weeks})")
        print(f"      🛠️ Core Tech   : {', '.join(phase.core_technologies)}")
        print(f"      🎯 Milestones  :")
        for mile in phase.weekly_milestones:
            print(f"         • {mile}")
        print(f"      🚀 Capstone    : {phase.capstone_project_title}")
        print(f"         Specs       : {phase.capstone_project_description}")

    print("\n" + "═" * 80 + "\n")


def run_pipeline(
    pdf_path: str,
    top_n: int = 5,
    country: str = None,
    remote_only: bool = False,
    provider: str = "gemini",
    output_dir: str = os.path.join(BASE_DIR, "data", "agent_reports")
):
    """Executes the master career agent pipeline with direct AI matching & gap calculation."""
    if not os.path.exists(pdf_path):
        sample_path = os.path.join(BASE_DIR, "data", "sample_cvs", pdf_path)
        if os.path.exists(sample_path):
            pdf_path = sample_path
        else:
            print(f"❌ Error: Resume file not found at '{pdf_path}'")
            return

    filename = os.path.basename(pdf_path)
    print("\n" + "🌟 " * 15)
    print("  AI CAREER ADVISOR AGENT — DIRECT AI MATCHING & GAP ENGINE")
    print("🌟 " * 15)
    print(f"📄 Target Resume : {filename}")
    if remote_only:
        print("🌐 Mode Filter   : Remote-Only Opportunities")
    elif country:
        print(f"📍 Geo Filter    : Country = '{country}'")

    # STAGE 1: AI Extraction
    print(f"\n[1/3] 🤖 Extracting candidate profile using AI Extractor ({provider.upper()})...")
    extractor = AIExtractor(provider=provider)
    profile = extractor.extract_from_pdf(pdf_path)
    print(f"      ✅ Extracted Candidate: {profile.personal_info.full_name}")
    print(f"      ✅ Domain & Seniority : {profile.seniority_level} {profile.primary_domain}")
    print(f"      ✅ Normalized Skills  : {len(profile.normalized_skills_flat)} skills cataloged")

    # STAGE 2: Retrieve Relevant Target Roles
    print(f"\n[2/3] 🔍 Retrieving candidate target roles from active database...")
    matcher = JobMatcher()
    candidate_jobs = matcher.retrieve_candidates(
        profile,
        top_k=top_n * 2,
        country=country,
        remote_only=remote_only
    )
    print(f"      ✅ Retrieved {len(candidate_jobs)} potential roles for deep AI evaluation.")

    # STAGE 3: AI Agent Evaluates, Scores & Calculates Gaps
    print(f"\n[3/3] 🧠 AI Agent is evaluating candidate, computing Match Scores & Gap Analysis...")
    agent = CareerAdvisorAgent()
    report = agent.evaluate_and_advise(profile, candidate_jobs, top_n=top_n)

    # Visualization
    print_agent_report_to_terminal(profile, report)

    # Persistence
    os.makedirs(output_dir, exist_ok=True)
    out_file = os.path.join(output_dir, f"{Path(filename).stem}_agent_report.json")
    full_output = {
        "candidate_profile": profile.model_dump(),
        "career_agent_report": report.model_dump()
    }
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(full_output, f, ensure_ascii=False, indent=2)
    print(f"💾 Full Intelligence Report Saved ➔ {out_file}")

    # Generate Executive PDF Dossier
    try:
        from src.pdf_generator import generate_career_dossier_pdf
        pdf_out_file = os.path.join(output_dir, f"{Path(filename).stem}_executive_dossier.pdf")
        generate_career_dossier_pdf(report, candidate_profile=profile, output_path=pdf_out_file)
        print(f"📄 Executive PDF Dossier Saved ➔ {pdf_out_file}")
    except Exception as e:
        print(f"⚠️ Note: PDF dossier generation skipped: {e}")

    # Persistence to SQLite Database
    try:
        from src.database import JobsDatabase
        db = JobsDatabase()
        rep_id = db.save_report(report.model_dump(), candidate_profile=profile.model_dump(), source_cv=filename)
        print(f"🗄️ Full Career Agent Report Saved to SQLite Database (reports table, ID: #{rep_id})\n")
    except Exception as e:
        print(f"⚠️ Note: DB save skipped: {e}\n")


def main():
    parser = argparse.ArgumentParser(description="Master AI Career Agent Pipeline")
    parser.add_argument("pdf", nargs="?", default="Naser_Ashraf_Resume.pdf", help="CV PDF or DOCX filename or path")
    parser.add_argument("--country", type=str, default=None, help="Country filter (e.g. Egypt, Germany, UK, USA, Saudi, UAE)")
    parser.add_argument("--remote", action="store_true", help="Remote-only positions filter")
    parser.add_argument("--top", type=int, default=5, help="Number of top matched jobs to evaluate (default: 5)")
    parser.add_argument("--provider", type=str, default="gemini", choices=["gemini", "openai", "ollama"], help="AI Provider")
    parser.add_argument("--output-dir", type=str, default=os.path.join(BASE_DIR, "data", "agent_reports"), help="Output directory for reports")

    args = parser.parse_args()
    run_pipeline(
        pdf_path=args.pdf,
        top_n=args.top,
        country=args.country,
        remote_only=args.remote,
        provider=args.provider,
        output_dir=args.output_dir
    )


if __name__ == "__main__":
    main()
