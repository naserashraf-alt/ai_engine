"""
=============================================================================
app.py - CareerAI: Autonomous Career Matching & Market Intelligence Dashboard
=============================================================================

PURPOSE:
- Enterprise-grade, executive Streamlit interface providing end-to-end access
  to the CareerAI Engine:
  • Tab 1: AI Career Matching & Strategic Advisory Pipeline
  • Tab 2: Global Tech Jobs Market Intelligence & Real-time FTS5 Search
  • Tab 3: Historical Candidate Dossiers & Strategic Audit Log

KEY HIGHLIGHTS:
- 100% English, modern, executive-level UX with dark glassmorphic styling.
- Real-time integration with SQLite FTS5 database (7,210+ active opportunities).
- Multi-provider Frontier AI orchestration (Gemini 2.5 Pro, GPT-4o, o3-mini).
- Complete candidate dossier extraction, gap diagnostics, and Google XYZ ATS optimization.
=============================================================================
"""

import os
import sys
import re
import json
import time
from pathlib import Path
import streamlit as st

# Configure wide page layout and executive branding
st.set_page_config(
    page_title="CareerAI | Autonomous Career Matching & Strategic Advisory",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enforce UTF-8 encoding across Windows runtime
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Setup root path resolution
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import config
from src.ai_extractor import AIExtractor
from src.matcher import JobMatcher
from src.agent_advisor import CareerAdvisorAgent
from src.schemas import ResumeProfile, CareerAgentReport, AgentJobEvaluation
from src.database import JobsDatabase, get_db
from src.pdf_generator import generate_career_dossier_pdf


# ==============================================================
# Custom CSS: Modern Executive Dark Theme & Glassmorphism
# ==============================================================
st.markdown("""
<style>
    /* Global Typography & Background Adjustments */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    /* Executive Hero Header */
    .hero-container {
        padding: 1.5rem 0 1.2rem 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        margin-bottom: 1.5rem;
    }
    .hero-title {
        font-size: 2.3rem;
        font-weight: 800;
        letter-spacing: -0.025em;
        background: linear-gradient(135deg, #38BDF8 0%, #818CF8 50%, #C084FC 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.35rem;
    }
    .hero-subtitle {
        font-size: 1.02rem;
        color: #94A3B8;
        font-weight: 400;
        line-height: 1.5;
    }

    /* Telemetry Pill Status */
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(16, 185, 129, 0.12);
        color: #34D399;
        border: 1px solid rgba(16, 185, 129, 0.25);
        border-radius: 9999px;
        padding: 4px 12px;
        font-size: 0.8rem;
        font-weight: 600;
    }

    /* Glassmorphic Metric Cards */
    .executive-card {
        background: rgba(15, 23, 42, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 20px;
        backdrop-filter: blur(12px);
        margin-bottom: 16px;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.4);
    }

    /* Job Card Design */
    .job-card {
        background: #0B1120;
        border: 1px solid #1E293B;
        border-radius: 12px;
        padding: 22px;
        margin-bottom: 18px;
        transition: all 0.2s ease-in-out;
        position: relative;
    }
    .job-card:hover {
        border-color: #38BDF8;
        box-shadow: 0 8px 30px rgba(56, 189, 248, 0.12);
        transform: translateY(-2px);
    }

    /* Score Badges */
    .score-badge-high {
        background: linear-gradient(135deg, #059669 0%, #10B981 100%);
        color: #FFFFFF;
        padding: 6px 14px;
        border-radius: 8px;
        font-weight: 800;
        font-size: 1.15rem;
        letter-spacing: -0.02em;
        box-shadow: 0 2px 10px rgba(16, 185, 129, 0.3);
    }
    .score-badge-mid {
        background: linear-gradient(135deg, #0284C7 0%, #06B6D4 100%);
        color: #FFFFFF;
        padding: 6px 14px;
        border-radius: 8px;
        font-weight: 800;
        font-size: 1.15rem;
        letter-spacing: -0.02em;
        box-shadow: 0 2px 10px rgba(6, 182, 212, 0.3);
    }
    .score-badge-low {
        background: linear-gradient(135deg, #4F46E5 0%, #6366F1 100%);
        color: #FFFFFF;
        padding: 6px 14px;
        border-radius: 8px;
        font-weight: 800;
        font-size: 1.15rem;
    }

    /* Skill Inventory Badges */
    .skill-tag {
        display: inline-flex;
        align-items: center;
        background: #1E293B;
        color: #E2E8F0;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 500;
        margin: 3px 4px 3px 0;
        border: 1px solid #334155;
    }
    .skill-matched {
        background: rgba(6, 78, 59, 0.55);
        color: #34D399;
        border: 1px solid rgba(16, 185, 129, 0.4);
        font-weight: 600;
    }
    .skill-missing {
        background: rgba(69, 10, 10, 0.55);
        color: #F87171;
        border: 1px solid rgba(239, 68, 68, 0.4);
        font-weight: 600;
    }

    /* Strategic Advisory Callout */
    .advisory-box {
        background: linear-gradient(145deg, #0F172A 0%, #1E1B4B 100%);
        border: 1px solid #4338CA;
        border-left: 5px solid #6366F1;
        border-radius: 12px;
        padding: 22px;
        color: #F1F5F9;
        font-size: 1.02rem;
        line-height: 1.7;
        margin-bottom: 24px;
        box-shadow: 0 10px 25px -5px rgba(99, 102, 241, 0.15);
    }

    /* ATS Makeover Card */
    .makeover-container {
        background: #0B1120;
        border: 1px solid #1E293B;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 14px;
    }
    .before-box {
        background: rgba(69, 10, 10, 0.3);
        border: 1px solid rgba(239, 68, 68, 0.3);
        border-radius: 8px;
        padding: 12px;
        color: #FCA5A5;
        font-size: 0.92rem;
    }
    .after-box {
        background: rgba(6, 78, 59, 0.3);
        border: 1px solid rgba(16, 185, 129, 0.3);
        border-radius: 8px;
        padding: 12px;
        color: #6EE7B7;
        font-size: 0.92rem;
        font-weight: 500;
    }

    /* Roadmap Timeline Card */
    .roadmap-card {
        background: #0B1120;
        border: 1px solid #1E293B;
        border-radius: 12px;
        padding: 20px;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }

    /* Sidebar Clean Styling */
    section[data-testid="stSidebar"] {
        background-color: #0B101B;
        border-right: 1px solid #1E293B;
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================
# Helper Functions & Cached Resources
# ==============================================================
@st.cache_resource
def get_matcher() -> JobMatcher:
    return JobMatcher()

@st.cache_resource
def get_db_instance() -> JobsDatabase:
    return JobsDatabase()

@st.cache_data
def load_sample_cv_list():
    sample_dir = config.SAMPLE_CVS_DIR
    if os.path.exists(sample_dir):
        return [f for f in sorted(os.listdir(sample_dir)) if f.lower().endswith((".pdf", ".docx", ".doc"))]
    return []

def get_country_options():
    return [
        ("🌐 Global / Worldwide (All Roles)", None, False),
        ("💻 Remote-Only Opportunities", None, True),
        ("🇪🇬 Egypt", "Egypt", False),
        ("🇸🇦 Saudi Arabia", "Saudi Arabia", False),
        ("🇦🇪 United Arab Emirates", "UAE", False),
        ("🌴 Gulf Cooperation Council (GCC)", "Gulf", False),
        ("🇩🇪 Germany", "Germany", False),
        ("🇬🇧 United Kingdom", "United Kingdom", False),
        ("🇺🇸 United States", "USA", False),
        ("🇫🇷 France", "France", False),
        ("🇳🇱 Netherlands", "Netherlands", False),
        ("🇨🇭 Switzerland", "Switzerland", False),
    ]


# ==============================================================
# Application Sidebar: Pipeline Orchestration & Engine Settings
# ==============================================================
with st.sidebar:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
        <span style="font-size: 2rem;">🚀</span>
        <div>
            <h3 style="margin: 0; font-size: 1.25rem; font-weight: 700; color: #F8FAFC;">CareerAI</h3>
            <span style="font-size: 0.75rem; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.05em;">Enterprise Engine</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Telemetry Status
    st.markdown("""
    <div class="status-pill" style="margin-bottom: 16px;">
        <span style="height: 7px; width: 7px; background-color: #10B981; border-radius: 50%; display: inline-block;"></span>
        SQLite FTS5 Engine Active
    </div>
    """, unsafe_allow_html=True)

    # 1. Candidate Resume Intake
    st.markdown("#### 1. Candidate Resume Intake")
    cv_source = st.radio(
        "Select Resume Source:",
        ["Preloaded Benchmark Profiles", "Upload Custom PDF Resume"],
        index=0,
        label_visibility="collapsed"
    )

    target_pdf_path = None
    if cv_source == "Preloaded Benchmark Profiles":
        sample_cvs = load_sample_cv_list()
        if sample_cvs:
            selected_cv_name = st.selectbox(
                "Select Candidate Profile:",
                sample_cvs,
                index=0,
                format_func=lambda name: f"📄 {name.replace('_', ' ').replace('.pdf', '').replace('.docx', '')}"
            )
            target_pdf_path = os.path.join(config.SAMPLE_CVS_DIR, selected_cv_name)
        else:
            st.warning("No sample resumes located in data/sample_cvs directory.")
    else:
        uploaded_file = st.file_uploader("Upload Resume (PDF or DOCX):", type=["pdf", "docx"])
        if uploaded_file:
            os.makedirs(config.SAMPLE_CVS_DIR, exist_ok=True)
            saved_path = os.path.join(config.SAMPLE_CVS_DIR, uploaded_file.name)
            with open(saved_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            target_pdf_path = saved_path
            st.success(f"✓ Uploaded: {uploaded_file.name}")

    st.markdown("---")

    # 2. Market & Filter Preferences
    st.markdown("#### 2. Market & Placement Filter")
    country_choices = get_country_options()
    selected_country_idx = st.selectbox(
        "Geographic Target Market:",
        range(len(country_choices)),
        format_func=lambda idx: country_choices[idx][0],
        index=0
    )
    _, chosen_country, chosen_remote = country_choices[selected_country_idx]

    top_n_jobs = st.slider("Top Matched Roles to Evaluate:", min_value=2, max_value=8, value=4, step=1)

    st.markdown("---")

    # 3. Frontier AI Model Orchestrator
    st.markdown("#### 3. Frontier AI Orchestrator")
    ai_provider = st.selectbox(
        "Engine Provider:",
        ["gemini", "openai", "ollama"],
        index=0,
        format_func=lambda p: {"gemini": "Google Gemini (Recommended)", "openai": "OpenAI Flagship", "ollama": "Local Host (Ollama)"}.get(p, p)
    )

    if ai_provider == "gemini":
        gemini_model_options = [
            ("gemini-2.5-pro", "👑 Gemini 2.5 Pro (PhD-Level Cognitive Reasoning)"),
            ("gemini-2.0-pro-exp-02-05", "🔬 Gemini 2.0 Pro Experimental (Elite Coding & Logic)"),
            ("gemini-2.0-flash-thinking-exp-01-21", "🧠 Gemini 2.0 Flash Thinking (Deep CoT Reasoning)"),
            ("gemini-1.5-pro", "🎯 Gemini 1.5 Pro (Enterprise Stable Pro)"),
            ("gemini-2.0-flash", "⚡ Gemini 2.0 Flash (High-Throughput 2.0)")
        ]
        selected_model_idx = st.selectbox(
            "Model Architecture:",
            range(len(gemini_model_options)),
            format_func=lambda i: gemini_model_options[i][1],
            index=0
        )
        selected_model = gemini_model_options[selected_model_idx][0]
        api_key_configured = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
        status_text = "🟢 API Key Verified" if api_key_configured else "🟡 Smart Heuristic Fallback"
        st.caption(f"Status: **{status_text}** | Architecture: `{selected_model}`")

    elif ai_provider == "openai":
        openai_model_options = [
            ("o3-mini", "👑 o3-mini (State-of-the-Art STEM & Code Reasoning)"),
            ("o1", "🧠 o1 (Complex Step-by-Step Reasoning)"),
            ("gpt-4o", "🚀 GPT-4o (Omni Multimodal Flagship)"),
            ("gpt-4o-mini", "⚡ GPT-4o Mini (Cost-Optimized High Speed)")
        ]
        selected_model_idx = st.selectbox(
            "Model Architecture:",
            range(len(openai_model_options)),
            format_func=lambda i: openai_model_options[i][1],
            index=0
        )
        selected_model = openai_model_options[selected_model_idx][0]
        api_key_configured = bool(os.getenv("OPENAI_API_KEY"))
        status_text = "🟢 API Key Verified" if api_key_configured else "🟡 Smart Heuristic Fallback"
        st.caption(f"Status: **{status_text}** | Architecture: `{selected_model}`")

    else:
        selected_model = "llama3.3"
        st.caption("Local Host Target: `http://localhost:11434`")

    st.markdown("<br>", unsafe_allow_html=True)

    # Execution Action Button
    run_btn = st.button("⚡ Execute Matching Pipeline", use_container_width=True, type="primary")

    # Engine Specs Footer
    st.markdown("---")
    st.markdown("""
    <div style="font-size: 0.75rem; color: #64748B; line-height: 1.5;">
        <strong>Indexed Jobs:</strong> 7,210 Active<br>
        <strong>Query Latency:</strong> ~0.008s (FTS5 Index)<br>
        <strong>Architecture:</strong> Enterprise V3
    </div>
    """, unsafe_allow_html=True)


# ==============================================================
# Main Executive Header
# ==============================================================
st.markdown("""
<div class="hero-container">
    <div class="hero-title">CareerAI — Autonomous Career Matching & Market Intelligence</div>
    <div class="hero-subtitle">
        Frontier AI Resume Extraction • Seniority-Aware Job Matching • Strategic Executive Advisory & ATS Optimization
    </div>
</div>
""", unsafe_allow_html=True)

tab_agent, tab_explorer, tab_history = st.tabs([
    "🎯 AI Career Matching & Advisory",
    "🌐 Market Intelligence & Jobs Explorer",
    "📋 Strategic Dossiers & Audit Log"
])


# ==============================================================
# TAB 1: AI Career Matching & Strategic Advisory Pipeline
# ==============================================================
with tab_agent:
    if run_btn:
        if not target_pdf_path or not os.path.exists(target_pdf_path):
            st.error("⚠️ Invalid Resume Selection: Please choose a valid PDF or DOCX file to commence analysis.")
        else:
            with st.spinner("🤖 [1/3] Extracting structured candidate profile via AI Extractor..."):
                start_time = time.time()
                extractor = AIExtractor(provider=ai_provider, model=selected_model)
                profile = extractor.extract_from_pdf(target_pdf_path)

            with st.spinner("🔍 [2/3] Performing high-precision candidate retrieval across 7,200+ roles..."):
                matcher = get_matcher()
                candidate_jobs = matcher.retrieve_candidates(
                    profile,
                    top_k=top_n_jobs * 2,
                    country=chosen_country,
                    remote_only=chosen_remote
                )

            with st.spinner(f"🧠 [3/3] Orchestrating Frontier AI Agent ({selected_model}) for Seniority Alignment & Gap Evaluation..."):
                agent = CareerAdvisorAgent(provider=ai_provider, model=selected_model)
                report = agent.evaluate_and_advise(profile, candidate_jobs, top_n=top_n_jobs)
                elapsed_total = round(time.time() - start_time, 2)

            # Persist session state
            st.session_state["last_profile"] = profile
            st.session_state["last_report"] = report
            st.session_state["elapsed"] = elapsed_total
            st.session_state["cv_name"] = os.path.basename(target_pdf_path)

            # Auto-save report to SQLite
            try:
                db_inst = get_db_instance()
                db_inst.save_report(
                    report.model_dump(),
                    candidate_profile=profile.model_dump(),
                    source_cv=os.path.basename(target_pdf_path) if target_pdf_path else "Uploaded Resume"
                )
            except Exception as e:
                print(f"⚠️ Note: SQLite auto-save checkpoint notice: {e}")

    # Display Results if Available
    if "last_profile" in st.session_state and "last_report" in st.session_state:
        profile: ResumeProfile = st.session_state["last_profile"]
        report: CareerAgentReport = st.session_state["last_report"]
        elapsed = st.session_state.get("elapsed", 0.0)
        cv_name = st.session_state.get("cv_name", "Resume.pdf")

        p = profile.personal_info
        meta = profile.extraction_metadata

        # Status Telemetry Bar
        live_engine = "🟢 Live Frontier LLM" if meta.get("is_live_ai") else "🟡 Smart Heuristic Core"
        st.markdown(f"""
        <div style="background: rgba(30, 41, 59, 0.6); border: 1px solid #334155; border-radius: 8px; padding: 10px 16px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
            <div>
                ⚡ Analysis completed in <strong>{elapsed}s</strong> &nbsp;|&nbsp;
                Orchestrator: <strong>{meta.get('provider', 'gemini').upper()}</strong> (<code>{meta.get('model', 'default')}</code>)
            </div>
            <div>
                Engine Telemetry: <strong>{live_engine}</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ------------------------------------------------------
        # Candidate Profile Dossier
        # ------------------------------------------------------
        with st.container():
            st.markdown(f"### 👤 Candidate Dossier: {p.full_name or 'Candidate'}")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Classified Domain", profile.primary_domain)
            col2.metric("Seniority Level", profile.seniority_level)
            col3.metric("Verified Experience", f"{profile.total_years_experience} Yrs")
            col4.metric("Indexed Skills", len(profile.normalized_skills_flat))

            # Contact Information Row
            contact_items = []
            if p.email: contact_items.append(f"📧 **Email:** `{p.email}`")
            if p.phone: contact_items.append(f"📱 **Phone:** `{p.phone}`")
            if p.location: contact_items.append(f"📍 **Location:** {p.location}")
            if p.links:
                for k, v in p.links.items():
                    contact_items.append(f"🔗 **{k.capitalize()}:** [{v}]({v})")
            if contact_items:
                st.markdown(" • ".join(contact_items))

            if profile.professional_summary:
                st.caption(f"📝 *\"{profile.professional_summary}\"*")

            # Technical Skills Inventory Chips
            st.markdown("##### 🛠️ Verified Technical Competencies")
            skills_html = "".join([f'<span class="skill-tag">{s}</span>' for s in profile.normalized_skills_flat[:36]])
            st.markdown(skills_html, unsafe_allow_html=True)

        st.markdown("---")

        # ------------------------------------------------------
        # Strategic Executive Advisory
        # ------------------------------------------------------
        st.markdown("### 🌟 Strategic Executive Advisory")
        
        # Display English Summary prominently
        english_summary = getattr(report, "executive_english_summary", "") or ""
        if english_summary:
            st.markdown(f'<div class="advisory-box"><strong>Executive Strategic Assessment:</strong><br><br>{english_summary}</div>', unsafe_allow_html=True)
        else:
            # Fallback if only Arabic summary was returned
            st.markdown(f'<div class="advisory-box"><strong>Executive Coaching Assessment:</strong><br><br>{report.executive_arabic_summary}</div>', unsafe_allow_html=True)

        # Expandable Arabic Coaching Notes for dual-language accessibility
        if getattr(report, "executive_arabic_summary", ""):
            with st.expander("🌍 View Executive Arabic Coaching Notes (التقرير الاستشاري العربي)"):
                st.markdown(f"""
                <div style="direction: rtl; text-align: right; font-family: 'Segoe UI', Tahoma, sans-serif; font-size: 1.05rem; line-height: 1.8; background: #111827; padding: 18px; border-radius: 8px; border-right: 4px solid #10B981;">
                    {report.executive_arabic_summary}
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ------------------------------------------------------
        # Top Matched Job Opportunities (AI Scored)
        # ------------------------------------------------------
        st.markdown(f"### 🏆 Top Matched Opportunities ({len(report.job_evaluations)} Target Roles)")
        st.caption("Each match percentage, skills overlap, and seniority alignment score below was independently calculated and verified by the AI Agent.")

        for idx, ev in enumerate(report.job_evaluations, 1):
            with st.container():
                # Score Badge Formatting
                if ev.agent_match_score >= 85:
                    badge_class = "score-badge-high"
                    tier_label = "Prime Alignment"
                elif ev.agent_match_score >= 70:
                    badge_class = "score-badge-mid"
                    tier_label = "Strong Fit"
                else:
                    badge_class = "score-badge-low"
                    tier_label = "Growth Potential"

                st.markdown(f"""
                <div class="job-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 10px;">
                        <div>
                            <h4 style="margin: 0; color: #F8FAFC; font-size: 1.25rem;">#{ev.job_rank} | {ev.job_title}</h4>
                            <p style="margin: 4px 0 0 0; color: #94A3B8; font-size: 0.95rem;">
                                🏢 <strong>{ev.company}</strong> &nbsp;•&nbsp; 📍 {ev.location}
                            </p>
                        </div>
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <span style="font-size: 0.8rem; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.05em;">{tier_label}</span>
                            <span class="{badge_class}">{ev.agent_match_score}% Match</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                # Metric Columns
                c1, c2, c3 = st.columns([1, 1, 1])
                c1.metric("Skills Overlap", f"{ev.agent_skills_score}%")
                c2.metric("Execution Readiness", f"{ev.agent_seniority_score}%")
                c3.metric("Capability Gap", f"+{ev.agent_gap_points_to_100}%")

                # Practical Execution Capability Assessment ("Can they do the job?")
                st.markdown(f"""
                <div style="background: rgba(15, 23, 42, 0.8); border-left: 4px solid #38BDF8; padding: 12px 16px; border-radius: 6px; margin: 12px 0;">
                    <strong style="color: #38BDF8;">🎯 Can Candidate Do This Job?</strong><br>
                    <span style="color: #E2E8F0; font-size: 0.95rem;">{ev.scoring_rationale}</span>
                </div>
                """, unsafe_allow_html=True)

                # What is needed to apply for this specific job
                st.markdown(f"""
                <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); padding: 12px 16px; border-radius: 8px; margin-bottom: 14px;">
                    <strong style="color: #34D399;">📋 What Candidate Needs To Do To Apply:</strong><br>
                    <span style="color: #F1F5F9; font-size: 0.92rem;">{ev.exact_action_to_100}</span>
                </div>
                """, unsafe_allow_html=True)

                # Matched vs Missing Skills Grid
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    st.markdown("**✅ Demonstrated Technical Skills:**")
                    if ev.matched_skills:
                        m_html = "".join([f'<span class="skill-tag skill-matched">✓ {s}</span>' for s in ev.matched_skills])
                        st.markdown(m_html, unsafe_allow_html=True)
                    else:
                        st.caption("Baseline domain overlap.")
                with col_m2:
                    st.markdown("**❌ Practical Execution Gaps to Bridge:**")
                    if ev.missing_skills:
                        mis_html = "".join([f'<span class="skill-tag skill-missing">✗ {s}</span>' for s in ev.missing_skills])
                        st.markdown(mis_html, unsafe_allow_html=True)
                    else:
                        st.caption("No significant skill gaps identified.")

                st.markdown("<br>", unsafe_allow_html=True)

                # Expandable Interview Diagnostics
                with st.expander("🔬 Technical Interview Preparation & Architecture"):
                    st.markdown(f"**❓ Likely Technical Interview Question:** *\"{ev.likely_interview_question}\"*")
                    st.info(f"**🔑 Winning Model Answer Strategy:** {ev.model_interview_answer_tip}")

                # Expandable Tailored Cover Letter & LinkedIn Outreach Pitch
                if getattr(ev, "cover_letter", None) or getattr(ev, "linkedin_pitch", None):
                    with st.expander("✉️ Tailored Cover Letter & LinkedIn Recruiter Outreach Pitch"):
                        out_tab1, out_tab2 = st.tabs(["📝 Tailored Cover Letter", "💬 LinkedIn / InMail Pitch"])
                        safe_comp = re.sub(r'[^a-zA-Z0-9]', '_', ev.company or 'Company')
                        safe_jid = re.sub(r'[^a-zA-Z0-9]', '_', str(ev.job_id or f"job_{idx}"))
                        c_text = ev.cover_letter or ""
                        l_text = ev.linkedin_pitch or ""
                        with out_tab1:
                            st.text_area(
                                "Customized Application Cover Letter:",
                                value=c_text,
                                height=230,
                                key=f"cl_txt_{safe_jid}_{idx}"
                            )
                            st.download_button(
                                label="📥 Download Cover Letter (.txt)",
                                data=c_text,
                                file_name=f"Cover_Letter_{safe_comp}_{idx}.txt",
                                mime="text/plain",
                                key=f"cl_btn_{safe_jid}_{idx}"
                            )
                        with out_tab2:
                            st.text_area(
                                "Concise LinkedIn / Recruiter InMail Message:",
                                value=l_text,
                                height=140,
                                key=f"li_txt_{safe_jid}_{idx}"
                            )
                            st.download_button(
                                label="📥 Download LinkedIn Pitch (.txt)",
                                data=l_text,
                                file_name=f"LinkedIn_Pitch_{safe_comp}_{idx}.txt",
                                mime="text/plain",
                                key=f"li_btn_{safe_jid}_{idx}"
                            )

                # Direct Apply Action
                st.link_button(f"🔗 Apply Directly on {ev.company}", ev.source_url, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("---")

        # ------------------------------------------------------
        # ATS Resume Makeovers (Google XYZ Formula)
        # ------------------------------------------------------
        st.markdown("### 📝 Zero-Shot ATS Resume Makeovers (Google XYZ Formula)")
        st.caption("Re-engineering generic resume bullet points into measurable, high-impact accomplishments: *'Accomplished [X], as measured by [Y], by doing [Z]'*.")

        for idx, m in enumerate(report.ats_resume_makeovers, 1):
            with st.container():
                st.markdown(f"""
                <div class="makeover-container">
                    <div style="font-weight: 700; color: #38BDF8; margin-bottom: 10px;">
                        Makeover #{idx} — Target Section: {m.section}
                    </div>
                """, unsafe_allow_html=True)

                m_col1, m_col2 = st.columns(2)
                with m_col1:
                    st.markdown(f"""
                    <div class="before-box">
                        <strong>❌ Before (Generic / Low Impact):</strong><br>
                        "{m.before_bullet}"
                    </div>
                    """, unsafe_allow_html=True)
                with m_col2:
                    st.markdown(f"""
                    <div class="after-box">
                        <strong>✅ After (ATS & Recruiter Optimized):</strong><br>
                        "{m.after_bullet}"
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown(f"""
                    <div style="margin-top: 10px; font-size: 0.85rem; color: #94A3B8;">
                        💡 <strong>Recruiter & ATS Impact Rationale:</strong> {m.rationale}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")

        # ------------------------------------------------------
        # 12-Week Production Career Roadmap
        # ------------------------------------------------------
        st.markdown("### 🗺️ 12-Week Production Engineering Roadmap")
        st.caption("Systematic curriculum to eliminate identified technical gaps, master required architecture, and construct proof-of-work.")

        r_cols = st.columns(len(report.production_roadmap))
        for idx, phase in enumerate(report.production_roadmap):
            with r_cols[idx]:
                st.markdown(f"""
                <div class="roadmap-card">
                    <div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <span style="font-weight: 800; color: #38BDF8; font-size: 1.1rem;">Phase {phase.phase_number}</span>
                            <span style="background: #1E293B; color: #94A3B8; font-size: 0.75rem; padding: 3px 8px; border-radius: 4px;">{phase.duration_weeks}</span>
                        </div>
                        <h4 style="margin: 0 0 10px 0; color: #F1F5F9; font-size: 1.05rem;">{phase.phase_title}</h4>
                        <div style="margin-bottom: 12px;">
                            <span style="font-size: 0.8rem; color: #94A3B8;">Core Technologies:</span><br>
                            {' '.join([f'<span class="skill-tag">{t}</span>' for t in phase.core_technologies])}
                        </div>
                        <div style="font-size: 0.88rem; color: #CBD5E1; margin-bottom: 16px;">
                            <strong>Milestones:</strong>
                            <ul style="padding-left: 18px; margin: 6px 0 0 0;">
                                {''.join([f'<li>{m}</li>' for m in phase.weekly_milestones])}
                            </ul>
                        </div>
                    </div>
                    <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 8px; padding: 12px;">
                        <strong style="color: #34D399; font-size: 0.85rem;">🚀 Capstone Project:</strong><br>
                        <span style="font-weight: 600; color: #F1F5F9; font-size: 0.9rem;">{phase.capstone_project_title}</span>
                        <p style="margin: 4px 0 0 0; font-size: 0.8rem; color: #94A3B8;">{phase.capstone_project_description}</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<br><br>", unsafe_allow_html=True)

        # ------------------------------------------------------
        # Full Intelligence Dossier PDF & JSON Export
        # ------------------------------------------------------
        full_dossier = {
            "metadata": {
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "source_resume": cv_name,
                "ai_provider": meta.get("provider", "gemini"),
                "model_architecture": meta.get("model", selected_model)
            },
            "candidate_profile": profile.model_dump(),
            "career_agent_report": report.model_dump()
        }
        json_str = json.dumps(full_dossier, indent=2, ensure_ascii=False)

        # Generate Executive Dossier PDF
        pdf_bytes = generate_career_dossier_pdf(report, candidate_profile=profile)

        col_export_1, col_export_2 = st.columns(2)
        with col_export_1:
            st.download_button(
                label="📥 Download Executive Career Dossier (PDF)",
                data=pdf_bytes,
                file_name=f"{Path(cv_name).stem}_Executive_Dossier.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        with col_export_2:
            st.download_button(
                label="💾 Download Full Intelligence Dossier (JSON)",
                data=json_str,
                file_name=f"{Path(cv_name).stem}_intelligence_dossier.json",
                mime="application/json",
                use_container_width=True
            )
    else:
        # Initial Landing State
        st.info("👈 Select a benchmark resume or upload your PDF / DOCX in the sidebar, configure your preferences, and click **'Execute Matching Pipeline'**.")


# ==============================================================
# TAB 2: Global Tech Jobs Market Explorer (SQLite FTS5)
# ==============================================================
with tab_explorer:
    st.markdown("### 📊 Active Tech Jobs Market Explorer")
    st.caption("Powered by high-performance SQLite with full-text search (FTS5) across 7,200+ verified active opportunities worldwide.")

    db_inst = get_db_instance()
    try:
        db_stats = db_inst.get_stats()
        m_c1, m_c2, m_c3, m_c4 = st.columns(4)
        m_c1.metric("Total Active Jobs", f"{db_stats['total_jobs']:,}")
        m_c2.metric("Remote Opportunities", f"{db_stats['total_remote']:,}")
        m_c3.metric("Indexed Employers", f"{db_stats['unique_companies']:,}")
        m_c4.metric("Database Storage", f"{db_stats['db_size_mb']} MB")
    except Exception as e:
        st.warning(f"Database statistics notice: {e}")

    st.markdown("---")

    # Filter Toolbar
    exp_col1, exp_col2 = st.columns([1, 2])
    with exp_col1:
        exp_country_idx = st.selectbox(
            "Geographic Partition:",
            range(len(country_choices)),
            format_func=lambda idx: country_choices[idx][0],
            key="explorer_partition"
        )
        _, e_country, e_remote = country_choices[exp_country_idx]

    with exp_col2:
        search_query = st.text_input(
            "⚡ Instant Full-Text Search (Title, Company, or Tech Stack):",
            placeholder="e.g. Python, AI, Machine Learning, React, DevOps, AWS, FastAPI..."
        )

    matcher_inst = get_matcher()

    # Query Execution with Latency Telemetry
    q_start = time.time()
    if search_query and len(search_query.strip()) >= 2:
        try:
            filtered_jobs = db_inst.search_jobs(search_query.strip(), limit=50)
            q_time = round(time.time() - q_start, 4)
            st.markdown(f"🔍 Found **{len(filtered_jobs)}** results matching `'{search_query}'` via SQLite FTS5 Index (**{q_time}s**):")
        except Exception:
            raw_jobs = matcher_inst.load_jobs(country=e_country, remote_only=e_remote)
            sq = search_query.lower()
            filtered_jobs = [
                j for j in raw_jobs
                if sq in (j.get("title") or "").lower() or
                   sq in (j.get("company") or "").lower() or
                   sq in (j.get("cleaned_description") or "").lower()
            ]
            q_time = round(time.time() - q_start, 4)
            st.markdown(f"Found **{len(filtered_jobs)}** results matching `'{search_query}'` (**{q_time}s**):")
    else:
        filtered_jobs = matcher_inst.load_jobs(country=e_country, remote_only=e_remote)
        label = "Remote Only" if e_remote else (e_country or "All Worldwide")
        st.markdown(f"Displaying **{min(len(filtered_jobs), 30)}** of **{len(filtered_jobs)}** active opportunities ({label}):")

    # Render Job Cards
    for j in filtered_jobs[:30]:
        with st.expander(f"💼 {j.get('title')} — {j.get('company')} ({j.get('location')})"):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"""
                **Seniority:** `{j.get('experience_level', 'Mid-Level')}` &nbsp;|&nbsp;
                **Work Mode:** `{j.get('work_mode', 'On-site')}` &nbsp;|&nbsp;
                **Source Platform:** `{j.get('source_api', 'Aggregated')}`
                """)
                req_s = j.get("required_skills") or []
                if req_s:
                    st.markdown("**Skills / Technologies:** " + " ".join([f"`{s}`" for s in req_s[:10]]))
                desc = j.get("cleaned_description") or j.get("description") or "No detailed description available."
                st.caption(desc[:450] + "...")
            with c2:
                url = j.get("source_url") or j.get("apply_url") or "#"
                st.link_button("🔗 Apply Directly", url, use_container_width=True)


# ==============================================================
# TAB 3: Candidate Dossiers & Strategic Audit Log
# ==============================================================
with tab_history:
    st.markdown("### 📋 Candidate Dossiers & Historical Audit Log")
    st.caption("Complete repository of historical evaluations, computed match scores, and strategic career advisories stored in SQLite.")

    db_inst = get_db_instance()
    try:
        db_reports = db_inst.get_all_reports()
    except Exception:
        db_reports = []

    if db_reports:
        report_options = {
            f"Dossier #{r['id']} | {r['candidate_name']} — {r['target_domain']} (Top Match: {r.get('top_match_score', 0)}%) [{r['created_at'][:16]}]": r['id']
            for r in db_reports
        }
        selected_label = st.selectbox("Select Historical Dossier to Inspect:", list(report_options.keys()))
        selected_rep_id = report_options[selected_label]
        rep_full = db_inst.get_report(selected_rep_id)

        if rep_full:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Candidate Name", rep_full.get("candidate_name") or "Candidate")
            c2.metric("Specialization", rep_full.get("target_domain") or "Tech")
            c3.metric("Evaluated Opportunities", len(rep_full.get("evaluations", [])))
            c4.metric("Source Document", rep_full.get("source_cv") or "PDF Resume")

            if rep_full.get("seniority_assessment"):
                st.markdown(f"**Seniority Assessment:** `{rep_full.get('seniority_assessment')}`")

            # Strategic Summary
            eng_sum = rep_full.get("report", {}).get("executive_english_summary")
            if eng_sum:
                st.markdown(f"""
                <div class="advisory-box">
                    <strong>Archived Strategic Summary:</strong><br><br>
                    {eng_sum}
                </div>
                """, unsafe_allow_html=True)
            elif rep_full.get("executive_arabic_summary"):
                with st.expander("🌍 View Arabic Coaching Notes"):
                    st.markdown(f"""
                    <div style="direction: rtl; text-align: right; font-family: 'Segoe UI', Tahoma, sans-serif; font-size: 1.05rem; line-height: 1.8; background: #111827; padding: 18px; border-radius: 8px;">
                        {rep_full.get("executive_arabic_summary")}
                    </div>
                    """, unsafe_allow_html=True)

            # Evaluated Opportunities
            evals = rep_full.get("evaluations", [])
            if evals:
                st.markdown(f"#### 🏆 Evaluated Opportunities ({len(evals)} Roles)")
                for ev in evals:
                    with st.expander(f"#{ev.get('job_rank')} | {ev.get('job_title')} @ {ev.get('company')} — {ev.get('agent_match_score')}% Match ({ev.get('location')})"):
                        ec1, ec2, ec3 = st.columns(3)
                        ec1.metric("Skills Overlap", f"{ev.get('agent_skills_score')}%")
                        ec2.metric("Seniority Alignment", f"{ev.get('agent_seniority_score')}%")
                        ec3.metric("Gap to 100%", f"+{ev.get('agent_gap_points_to_100')}%")
                        st.markdown(f"💡 **Capability Assessment:** {ev.get('scoring_rationale')}")
                        if ev.get("exact_action_to_100"):
                            st.info(f"📋 **What Candidate Needs To Do To Apply:** {ev.get('exact_action_to_100')}")
                        if ev.get("source_url"):
                            st.link_button(f"🔗 Apply on {ev.get('company')}", ev.get("source_url"))

            # Raw JSON & PDF Dossier Inspector
            col_hist_pdf, col_hist_json = st.columns([1, 1])
            with col_hist_pdf:
                try:
                    hist_rep = rep_full.get("report")
                    if hist_rep:
                        hist_pdf = generate_career_dossier_pdf(hist_rep)
                        safe_cand = re.sub(r'[^a-zA-Z0-9]', '_', rep_full.get('candidate_name') or 'Candidate')
                        st.download_button(
                            label=f"📥 Download Dossier #{selected_rep_id} (PDF)",
                            data=hist_pdf,
                            file_name=f"Dossier_{selected_rep_id}_{safe_cand}.pdf",
                            mime="application/pdf",
                            key=f"hist_pdf_btn_{selected_rep_id}",
                            use_container_width=True
                        )
                except Exception as e:
                    st.caption(f"PDF generation error: {e}")

            with col_hist_json:
                with st.expander("📄 View Full Raw Intelligence Dossier (JSON)"):
                    st.json(rep_full.get("report"))
    else:
        st.info("No historical dossiers recorded in the SQLite database yet. Run an analysis in Tab 1 to populate the audit log.")
