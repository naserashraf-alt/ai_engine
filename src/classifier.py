"""
=============================================================================
src/classifier.py - مصنف المستويات الوظيفية (Seniority Level Classifier)
=============================================================================

الغرض (Purpose):
- تصنيف المسميات والوظائف وسنوات الخبرة إلى مستويات معيارية موحدة:
  1. Junior / Entry-Level (0 - 2 سنوات)
  2. Mid-Level (2.5 - 5 سنوات)
  3. Senior (5 - 8 سنوات)
  4. Lead / Principal / Architect (8+ سنوات)

المدخلات والمخرجات (Inputs / Outputs):
- المدخل: المسمى الوظيفي (Title)، وصف الوظيفة (Description)، أو تلميح المنصة (Hint).
- المخرج: نص المستوى المعياري (Standardized Seniority Level).

الاتصالات والتبعيات (Dependencies & Connections):
- يُستورد في: scripts/collect_jobs.py, src/matcher.py
=============================================================================
"""

import re
from typing import Optional


class SeniorityClassifier:
    """Classifies job titles and descriptions into standardized seniority levels."""

    @staticmethod
    def classify_job_level(title: str, description: str = "", hint: str = "") -> str:
        title_lower = (title or "").lower()
        hint_lower = (hint or "").lower()
        desc_sample = (description or "")[:500].lower()
        combined = f"{title_lower} {hint_lower} {desc_sample}"

        # 1. Lead / Principal / Executive
        lead_kw = ["lead", "principal", "architect", "head of", "director", "staff", "vp", "chief", "manager"]
        if any(re.search(r'\b' + re.escape(w) + r'\b', title_lower) for w in lead_kw):
            return "Lead / Principal"

        # 2. Senior
        sr_kw = ["senior", "sr.", "sr", "expert", "specialist"]
        if any(re.search(r'\b' + re.escape(w) + r'\b', title_lower) for w in sr_kw):
            return "Senior"

        # 3. Junior / Entry-Level / Intern
        jr_kw = ["junior", "jr.", "jr", "entry level", "entry-level", "intern", "internship", "trainee", "associate", "fresh graduate"]
        if any(re.search(r'\b' + re.escape(w) + r'\b', title_lower) for w in jr_kw):
            return "Junior / Entry-Level"

        # 4. Check hint from job portal if provided
        if "entry" in hint_lower or "junior" in hint_lower or "intern" in hint_lower:
            return "Junior / Entry-Level"
        if "senior" in hint_lower or "manager" in hint_lower:
            return "Senior"
        if "experienced" in hint_lower or "mid" in hint_lower:
            return "Mid-Level"

        # 5. Check years of experience mentioned in text
        exp_match = re.search(r'(\d+)\+?\s*(?:years?|yrs?)', combined)
        if exp_match:
            try:
                yrs = int(exp_match.group(1))
                if yrs >= 7:
                    return "Lead / Principal"
                if yrs >= 4:
                    return "Senior"
                if yrs <= 2:
                    return "Junior / Entry-Level"
            except Exception:
                pass

        return "Mid-Level"
