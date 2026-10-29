"""
=============================================================================
src/pdf_reader.py - قارئ ومفكك ملفات السير الذاتية (Universal Document Extractor)
=============================================================================

الغرض (Purpose):
- استخراج نصوص السير الذاتية بدقة عالية من ملفات PDF وملفات Word (DOCX).
- معالجة الحروف المتشابكة (Ligatures)، الجداول، والرموز لإنتاج نص خام نقي.
- يدعم استخراج بايتس الملفات (Binary bytes) للذكاء الاصطناعي متعدد الوسائط (Multimodal).

المدخلات والمخرجات (Inputs / Outputs):
- المدخل: مسار ملف PDF أو DOCX.
- المخرج: قاموس يحتوي على (النص المنقى، مسار الملف، عدد الصفحات، عدد الكلمات والحروف).

الاتصالات والتبعيات (Dependencies & Connections):
- يُستورد في: src/ai_extractor.py, app.py
=============================================================================
"""

import os
import re
import sys
from typing import Dict, Any

try:
    import pymupdf  # PyMuPDF
except ImportError:
    pymupdf = None

try:
    import docx
except ImportError:
    docx = None


class PDFReader:
    """High-performance document parser for PDF and DOCX with text normalization."""

    @staticmethod
    def extract_text_and_meta(file_path: str) -> Dict[str, Any]:
        """
        Reads a PDF or DOCX file and returns normalized text along with document metadata.
        Seamlessly handles both file types.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Document file not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        if ext in [".docx", ".doc"]:
            return PDFReader.extract_docx_and_meta(file_path)

        if pymupdf is None:
            raise ImportError("PyMuPDF (pymupdf) is required for reading PDF files.")

        doc = pymupdf.open(file_path)
        pages_text = []
        
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            text = page.get_text("text") or ""
            pages_text.append(text)

        raw_text = "\n\n".join(pages_text)
        cleaned_text = PDFReader.clean_resume_text(raw_text)

        word_count = len(cleaned_text.split())
        char_count = len(cleaned_text)

        return {
            "pdf_path": file_path,
            "file_path": file_path,
            "filename": os.path.basename(file_path),
            "num_pages": len(doc),
            "word_count": word_count,
            "char_count": char_count,
            "raw_text": raw_text,
            "cleaned_text": cleaned_text
        }

    @staticmethod
    def extract_docx_and_meta(docx_path: str) -> Dict[str, Any]:
        """
        Reads a DOCX file, extracting paragraphs and structured tables.
        """
        if docx is None:
            raise ImportError("python-docx is required for reading DOCX files.")

        if not os.path.exists(docx_path):
            raise FileNotFoundError(f"DOCX file not found: {docx_path}")

        doc = docx.Document(docx_path)
        chunks = []

        # Extract regular paragraphs
        for p in doc.paragraphs:
            text = p.text.strip()
            if text:
                chunks.append(text)

        # Extract structured data inside tables (often used for education/skills in CVs)
        for table in doc.tables:
            for row in table.rows:
                cells = [c.text.strip() for c in row.cells if c.text.strip()]
                # Deduplicate identical adjacent cells (often created by merged cells)
                unique_cells = []
                for cell in cells:
                    if not unique_cells or cell != unique_cells[-1]:
                        unique_cells.append(cell)
                if unique_cells:
                    chunks.append(" | ".join(unique_cells))

        raw_text = "\n\n".join(chunks)
        cleaned_text = PDFReader.clean_resume_text(raw_text)

        word_count = len(cleaned_text.split())
        char_count = len(cleaned_text)
        # Approximate page count (avg 350 words per page in CVs)
        est_pages = max(1, (word_count + 349) // 350)

        return {
            "pdf_path": docx_path,
            "file_path": docx_path,
            "filename": os.path.basename(docx_path),
            "num_pages": est_pages,
            "word_count": word_count,
            "char_count": char_count,
            "raw_text": raw_text,
            "cleaned_text": cleaned_text
        }

    @staticmethod
    def get_pdf_bytes(pdf_path: str) -> bytes:
        """Reads raw binary content of the file."""
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"File not found: {pdf_path}")
        with open(pdf_path, "rb") as f:
            return f.read()

    @staticmethod
    def clean_resume_text(raw_text: str) -> str:
        """
        Standardizes bullets, line breaks, and ligatures commonly found in CVs.
        """
        if not raw_text:
            return ""

        # Normalize line endings
        text = raw_text.replace("\r\n", "\n").replace("\r", "\n")

        # Replace varied unicode bullet points with standard markdown dash
        bullet_pattern = r'[\u2022\u2023\u25E6\u2043\u2219\uf0a7\u25cf\u25cb\u25aa\u25ab\u27a4\u25b8\u25ba]'
        text = re.sub(bullet_pattern, "\n- ", text)

        # Fix ligature artifacts commonly produced by PDF renderers (e.g. fi, fl, ffi)
        ligatures = {
            "\ufb00": "ff",
            "\ufb01": "fi",
            "\ufb02": "fl",
            "\ufb03": "ffi",
            "\ufb04": "ffl",
            "\ufb05": "ft",
            "\ufb06": "st"
        }
        for lig, repl in ligatures.items():
            text = text.replace(lig, repl)

        # Collapse horizontal spacing
        text = re.sub(r'[ \t]+', ' ', text)

        # Collapse excessive blank lines
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()


# Universal Alias
DocumentReader = PDFReader
