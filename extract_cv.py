"""
=============================================================================
extract_cv.py - Standalone CV Extractor CLI
=============================================================================

PURPOSE:
- Parse and analyze PDF resumes to extract complete structured candidate profiles without matching.
- Print structured candidate cards and persist profiles directly to the candidates table in SQLite.

EXECUTION:
python extract_cv.py data/sample_cvs/Naser_Ashraf_Resume.pdf
=============================================================================
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Ensure UTF-8 output encoding for Windows terminal
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Ensure ai_project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.ai_extractor import AIExtractor
from src.schemas import ResumeProfile


def print_resume_card(profile: ResumeProfile):
    """Prints a beautiful, structured terminal card of the extracted profile."""
    p_info = profile.personal_info
    meta = profile.extraction_metadata

    print("\n" + "═" * 78)
    print(f" 👤 CANDIDATE PROFILE: {p_info.full_name or 'N/A'}")
    if p_info.headline:
        print(f"    💼 Headline: {p_info.headline}")
    print(f"    📧 Email: {p_info.email or 'N/A'} | 📱 Phone: {p_info.phone or 'N/A'}")
    if p_info.location:
        print(f"    📍 Location: {p_info.location}")
    if p_info.links:
        links_str = " | ".join([f"{k.capitalize()}: {v}" for k, v in p_info.links.items()])
        print(f"    🔗 Links: {links_str}")
    print("═" * 78)

    print(f"\n🎯 DOMAIN & SENIORITY CLASSIFICATION:")
    print(f"   • Primary Technical Domain : {profile.primary_domain}")
    print(f"   • Seniority Level          : {profile.seniority_level}")
    print(f"   • Total Relevant Experience: {profile.total_years_experience} Years")

    if profile.professional_summary:
        print(f"\n📝 EXECUTIVE SUMMARY:")
        print(f"   {profile.professional_summary.strip()}")

    print(f"\n🛠️ EXTRACTED SKILLS INVENTORY ({len(profile.normalized_skills_flat)} Normalized Tech Skills):")
    if profile.skills.technical_skills:
        print(f"   • Technical / Hard Skills : {', '.join(profile.skills.technical_skills)}")
    if profile.skills.tools_and_platforms:
        print(f"   • Tools & Platforms       : {', '.join(profile.skills.tools_and_platforms)}")
    if profile.skills.soft_skills:
        print(f"   • Soft Skills             : {', '.join(profile.skills.soft_skills)}")

    if profile.work_experience:
        print(f"\n💼 WORK EXPERIENCE ({len(profile.work_experience)} Roles):")
        for idx, exp in enumerate(profile.work_experience, 1):
            date_range = f"{exp.start_date or 'N/A'} ➔ {exp.end_date or 'Present'}"
            status = " [ACTIVE]" if exp.is_current else ""
            print(f"   {idx}. {exp.job_title} @ {exp.company} ({date_range}){status}")
            if exp.location:
                print(f"      📍 {exp.location}")
            if exp.description:
                print(f"      ℹ️ {exp.description}")
            for ach in exp.key_achievements[:3]:
                print(f"      - {ach}")
            if exp.technologies_used:
                print(f"      ⚙️ Tech Used: {', '.join(exp.technologies_used)}")

    if profile.education:
        print(f"\n🎓 EDUCATION ({len(profile.education)} Entries):")
        for idx, edu in enumerate(profile.education, 1):
            study = f" in {edu.field_of_study}" if edu.field_of_study else ""
            year = f" ({edu.graduation_year})" if edu.graduation_year else ""
            print(f"   {idx}. {edu.degree}{study} ➔ {edu.institution}{year}")
            if edu.grade_or_gpa:
                print(f"      🏆 Grade/GPA: {edu.grade_or_gpa}")

    if profile.projects:
        print(f"\n🚀 KEY PROJECTS ({len(profile.projects)}):")
        for idx, proj in enumerate(profile.projects, 1):
            print(f"   {idx}. {proj.title}")
            if proj.description:
                print(f"      📄 {proj.description}")
            if proj.technologies:
                print(f"      🛠️ Tech: {', '.join(proj.technologies)}")
            if proj.url:
                print(f"      🔗 Link: {proj.url}")

    if profile.certifications:
        print(f"\n📜 CERTIFICATIONS & LICENSES ({len(profile.certifications)}):")
        for idx, cert in enumerate(profile.certifications, 1):
            date_str = f" ({cert.issue_date})" if cert.issue_date else ""
            print(f"   {idx}. {cert.name} ➔ {cert.issuer}{date_str}")

    if profile.languages:
        print(f"\n🗣️ LANGUAGES:")
        langs_str = ", ".join([f"{l.language} ({l.proficiency})" for l in profile.languages])
        print(f"   • {langs_str}")

    print("\n" + "─" * 78)
    provider_badge = meta.get("provider", "unknown").upper()
    model_badge = meta.get("model", "default")
    elapsed = meta.get("execution_time_seconds", 0.0)
    pages = meta.get("num_pages", 1)
    chars = meta.get("char_count", 0)
    live_status = "🟢 LIVE AI" if meta.get("is_live_ai") else "🟡 HEURISTIC FALLBACK (Offline)"
    print(f" ⚙️ ENGINE: {provider_badge} ({model_badge}) | {live_status} | ⏱️ {elapsed}s | 📄 {pages} pages ({chars} chars)")
    print("─" * 78 + "\n")


def process_cv_file(pdf_path: str, extractor: AIExtractor, output_dir: str = None) -> ResumeProfile:
    """Processes a single PDF file and optionally saves structured JSON."""
    filename = os.path.basename(pdf_path)
    print(f"\n▶️ Processing: {filename} ...")
    
    profile = extractor.extract_from_pdf(pdf_path)
    print_resume_card(profile)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        out_name = Path(filename).stem + "_extracted.json"
        out_path = os.path.join(output_dir, out_name)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(profile.model_dump(), f, ensure_ascii=False, indent=2)
        print(f"💾 Structured Profile Saved ➔ {out_path}")

    # Save to SQLite Database
    try:
        from src.database import JobsDatabase
        db = JobsDatabase()
        cand_id = db.save_candidate(profile.model_dump(), source_filename=filename)
        print(f"🗄️ Candidate Profile Saved to SQLite Database (candidates table, ID: #{cand_id})\n")
    except Exception as e:
        print(f"⚠️ Note: DB save skipped: {e}\n")

    return profile


def main():
    parser = argparse.ArgumentParser(description="AI Resume Extractor (Gemini, OpenAI, Ollama)")
    parser.add_argument("pdf", nargs="?", default=None, help="Path to the PDF resume to parse")
    parser.add_argument("--all", action="store_true", help="Extract all PDFs found in data/sample_cvs/")
    parser.add_argument("--provider", type=str, default="gemini", choices=["gemini", "openai", "ollama"], help="AI Provider (default: gemini)")
    parser.add_argument("--model", type=str, default=None, help="Model name (e.g. gemini-2.0-flash, gpt-4o-mini, llama3.2)")
    parser.add_argument("--output-dir", type=str, default=os.path.join(BASE_DIR, "data", "extracted_cvs"), help="Directory to save extracted JSONs")
    parser.add_argument("--no-save", action="store_true", help="Do not write output JSON to disk")

    args = parser.parse_args()
    save_dir = None if args.no_save else args.output_dir

    # Initialize AI Extractor
    extractor = AIExtractor(provider=args.provider, model=args.model)

    sample_cvs_dir = os.path.join(BASE_DIR, "data", "sample_cvs")
    target_files = []

    if args.all or not args.pdf:
        if args.pdf:
            target_files = [args.pdf]
        else:
            if os.path.exists(sample_cvs_dir):
                target_files = [
                    os.path.join(sample_cvs_dir, f)
                    for f in os.listdir(sample_cvs_dir)
                    if f.lower().endswith(".pdf")
                ]
            if not target_files:
                print("❌ No PDF files found to process. Please specify a file path or place PDFs in data/sample_cvs/")
                sys.exit(1)
    else:
        if os.path.exists(args.pdf):
            target_files = [args.pdf]
        else:
            rel = os.path.join(sample_cvs_dir, args.pdf)
            if os.path.exists(rel):
                target_files = [rel]
            else:
                print(f"❌ Error: File not found at '{args.pdf}'")
                sys.exit(1)

    print("\n" + "🤖 " * 15)
    print(f"  AI RESUME EXTRACTION SUBSYSTEM [Provider: {args.provider.upper()}]")
    print("🤖 " * 15)
    print(f"📂 Found {len(target_files)} PDF resume(s) to process.")

    for pdf_file in target_files:
        try:
            process_cv_file(pdf_file, extractor, output_dir=save_dir)
        except Exception as e:
            print(f"❌ Failed to extract '{pdf_file}': {e}")


if __name__ == "__main__":
    main()
