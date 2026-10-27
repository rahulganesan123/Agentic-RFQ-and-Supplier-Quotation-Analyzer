"""
Ingest Agent: Detects file types and routes documents to appropriate parsers:
- PDF: pypdf / text extraction
- Excel / CSV: pandas / openpyxl table parsing
- Images / Scans: OCR or Vision API route
- Text / JSON: direct text parsing
"""

import os
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
import pypdf


class DocumentParser:
    """Multi-format parser for supplier quotations and RFQs."""

    @staticmethod
    def detect_file_type(file_path: str) -> str:
        ext = Path(file_path).suffix.lower()
        if ext == ".pdf":
            return "pdf"
        elif ext in [".xlsx", ".xls", ".xlsm"]:
            return "excel"
        elif ext in [".csv", ".tsv"]:
            return "csv"
        elif ext in [".png", ".jpg", ".jpeg", ".tiff", ".bmp"]:
            return "image"
        elif ext in [".txt", ".json", ".md"]:
            return "text"
        else:
            return "unknown"

    @classmethod
    def parse_pdf(cls, file_path: str) -> Dict[str, Any]:
        """Extracts text content and metadata from PDF files."""
        reader = pypdf.PdfReader(file_path)
        pages_text = []
        for idx, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            pages_text.append(f"--- Page {idx + 1} ---\n{text}")

        full_text = "\n\n".join(pages_text)
        return {
            "file_name": Path(file_path).name,
            "file_type": "pdf",
            "page_count": len(reader.pages),
            "content": full_text,
            "tables": [],
        }

    @classmethod
    def parse_excel(cls, file_path: str) -> Dict[str, Any]:
        """Extracts structured tables and text representation from Excel workbooks."""
        excel_file = pd.ExcelFile(file_path)
        sheet_summaries = []
        all_tables = []

        for sheet_name in excel_file.sheet_names:
            df = excel_file.parse(sheet_name)
            # Drop entirely empty rows/columns
            df = df.dropna(how="all").dropna(axis=1, how="all")
            sheet_text = f"=== Sheet: {sheet_name} ===\n"
            sheet_text += df.to_string(index=False)
            sheet_summaries.append(sheet_text)
            all_tables.append({
                "sheet": sheet_name,
                "rows": df.to_dict(orient="records"),
            })

        return {
            "file_name": Path(file_path).name,
            "file_type": "excel",
            "page_count": len(excel_file.sheet_names),
            "content": "\n\n".join(sheet_summaries),
            "tables": all_tables,
        }

    @classmethod
    def parse_csv(cls, file_path: str) -> Dict[str, Any]:
        """Extracts structured table and text representation from CSV files."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                raw_text = f.read()
            df = pd.read_csv(file_path, comment="#")
            df = df.dropna(how="all").dropna(axis=1, how="all")
            return {
                "file_name": Path(file_path).name,
                "file_type": "csv",
                "page_count": 1,
                "content": raw_text,
                "tables": [{"sheet": "default", "rows": df.to_dict(orient="records")}],
            }
        except Exception:
            return cls.parse_text(file_path)

    @classmethod
    def parse_text(cls, file_path: str) -> Dict[str, Any]:
        """Reads plain text, JSON, or markdown files."""
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        return {
            "file_name": Path(file_path).name,
            "file_type": "text",
            "page_count": 1,
            "content": text,
            "tables": [],
        }

    @classmethod
    def parse_image(cls, file_path: str) -> Dict[str, Any]:
        """
        Processes scanned or photographed quotes.
        If a vision LLM or OCR is not configured, provides clear metadata header.
        """
        # When integrating with multimodal API (Gemini or OpenAI), the image bytes can be forwarded
        return {
            "file_name": Path(file_path).name,
            "file_type": "image",
            "page_count": 1,
            "content": f"[Scanned/Image Document: {Path(file_path).name} - Processed via Vision Route]",
            "image_path": str(Path(file_path).resolve()),
            "tables": [],
        }

    @classmethod
    def parse_file(cls, file_path: str) -> Dict[str, Any]:
        """Unified entry point to parse any supported file format."""
        ftype = cls.detect_file_type(file_path)
        if ftype == "pdf":
            return cls.parse_pdf(file_path)
        elif ftype == "excel":
            return cls.parse_excel(file_path)
        elif ftype == "csv":
            return cls.parse_csv(file_path)
        elif ftype == "image":
            return cls.parse_image(file_path)
        else:
            return cls.parse_text(file_path)


def ingest_documents(file_paths: List[str]) -> List[Dict[str, Any]]:
    """Ingest agent entry point: processes a list of files into standard raw document dictionaries."""
    parsed_docs = []
    for path in file_paths:
        if os.path.exists(path):
            doc = DocumentParser.parse_file(path)
            parsed_docs.append(doc)
    return parsed_docs
