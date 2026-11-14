"""
=============================================================================
src/classifier.py - Context-Aware Precision Seniority Classifier
=============================================================================

Purpose:
- Classifies job titles, descriptions, and required experience into standardized tiers:
  1. Entry-Level / Intern (0 - 1 years)
  2. Junior (1 - 2.5 years)
  3. Mid-Level (2.5 - 5 years)
  4. Senior (5 - 8 years)
  5. Lead / Principal / Architect (8+ years)

Key Capabilities:
- Negative Context Filter: Prevents false positives from company founding dates
  or commercial metrics (e.g. "Founded 20 years ago in Germany").
- Context-Aware Extraction: Focuses on candidate experience requirements rather than company tenure.
- Tiered evaluation: Title patterns take priority, followed by parsed requirement years.

Dependencies:
- Imported in: scripts/collect_jobs.py, src/matcher.py, src/database.py
=============================================================================
"""

import re
from typing import Optional


class SeniorityClassifier:
    """Classifies job titles and descriptions into standardized seniority levels with context awareness."""

    # Patterns indicating company marketing / history rather than candidate requirements
    COMPANY_HISTORY_PATTERNS = [
        re.compile(r'\b(?:founded|established|in business|operating|serving|experience in the market)\s+(?:for\s+)?(?:over\s+)?\d+\s*(?:years?|yrs?)', re.IGNORECASE),
        re.compile(r'\b(?:over|more than|past)\s+\d+\s*(?:years?|yrs?)\s+(?:of\s+)?(?:company|industry|business|market|history|success)', re.IGNORECASE),
        re.compile(r'\bwith\s+\d+\s*(?:years?|yrs?)\s+of\s+(?:innovation|legacy|growth)\b', re.IGNORECASE)
    ]

    # Explicit candidate requirement patterns
    CANDIDATE_EXP_PATTERNS = [
        # "3+ years of experience", "5-7 years experience", "at least 3 years"
        re.compile(r'\b(?:minimum|at least|requir(?:e|ed|es|ing)|must have|with)\s+(\d+)(?:\s*[-–to]\s*\d+)?\+?\s*(?:years?|yrs?)\b', re.IGNORECASE),
        re.compile(r'\b(\d+)(?:\s*[-–to]\s*\d+)?\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:relevant\s+|hands[- ]on\s+|work\s+|professional\s+|proven\s+)?(?:experience|exp|track record)\b', re.IGNORECASE),
        re.compile(r'\bexperience:\s*(\d+)\+?\s*(?:years?|yrs?)\b', re.IGNORECASE)
    ]

    @classmethod
    def extract_required_years(cls, text: str) -> Optional[float]:
        """
        Extracts the required years of candidate experience from job text while
        strictly filtering out company-level marketing statements.
        """
        if not text:
            return None

        # Clean out known company history sentences
        clean_text = text
        for pat in cls.COMPANY_HISTORY_PATTERNS:
            clean_text = pat.sub(" ", clean_text)

        # Focus preferentially on requirements/qualifications section if identifiable
        req_section_match = re.search(
            r'(?:requirements|qualifications|what we(?:\'re| are) looking for|skills required|profile)[:\n](.*?)(?:benefits|what we offer|about us|$)',
            clean_text,
            re.IGNORECASE | re.DOTALL
        )
        search_target = req_section_match.group(1) if req_section_match else clean_text

        # Search candidate experience patterns
        found_years = []
        for pat in cls.CANDIDATE_EXP_PATTERNS:
            for match in pat.finditer(search_target):
                try:
                    yrs = float(match.group(1))
                    # Sanity check: Realistic individual experience requirement is between 0 and 20 years
                    if 0.5 <= yrs <= 20.0:
                        found_years.append(yrs)
                except (ValueError, IndexError):
                    continue

        if found_years:
            # Return the minimum stated requirement (e.g. if both 3 and 5 are mentioned)
            return min(found_years)

        return None

    @classmethod
    def classify_job_level(cls, title: str, description: str = "", hint: str = "") -> str:
        """
        Standardizes seniority classification with multi-tiered resolution:
        1. Explicit Title Analysis (Highest Confidence).
        2. Platform Hint Mapping.
        3. Context-Filtered Candidate Experience Years.
        4. Sensible Defaults (Mid-Level).
        """
        title_lower = (title or "").lower().strip()
        hint_lower = (hint or "").lower().strip()

        # -------------------------------------------------------------
        # 1. Lead / Principal / Executive (Title First)
        # -------------------------------------------------------------
        lead_kw = ["lead", "principal", "architect", "head of", "director", "staff", "vp", "chief", "manager"]
        if any(re.search(r'\b' + re.escape(w) + r'\b', title_lower) for w in lead_kw):
            return "Lead / Principal"

        # -------------------------------------------------------------
        # 2. Senior (Title First)
        # -------------------------------------------------------------
        sr_kw = ["senior", "sr.", "sr", "expert", "specialist"]
        if any(re.search(r'\b' + re.escape(w) + r'\b', title_lower) for w in sr_kw):
            return "Senior"

        # -------------------------------------------------------------
        # 3. Junior / Entry-Level / Intern (Title First)
        # -------------------------------------------------------------
        jr_kw = ["junior", "jr.", "jr", "entry level", "entry-level", "intern", "internship", "trainee", "associate", "fresh graduate"]
        if any(re.search(r'\b' + re.escape(w) + r'\b', title_lower) for w in jr_kw):
            return "Junior / Entry-Level"

        # -------------------------------------------------------------
        # 4. Check hint from job portal if provided
        # -------------------------------------------------------------
        if any(k in hint_lower for k in ["entry", "junior", "intern", "trainee"]):
            return "Junior / Entry-Level"
        if any(k in hint_lower for k in ["lead", "principal", "director"]):
            return "Lead / Principal"
        if any(k in hint_lower for k in ["senior", "expert"]):
            return "Senior"
        if any(k in hint_lower for k in ["experienced", "mid", "associate"]):
            return "Mid-Level"

        # -------------------------------------------------------------
        # 5. Extract Years of Experience with Anti-False-Positive Filter
        # -------------------------------------------------------------
        years = cls.extract_required_years(description)
        if years is not None:
            if years >= 7.0:
                return "Lead / Principal"
            if years >= 4.0:
                return "Senior"
            if years <= 2.0:
                return "Junior / Entry-Level"
            return "Mid-Level"

        return "Mid-Level"
