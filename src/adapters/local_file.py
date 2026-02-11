"""Local file adapter for PDF, Word, text files."""
import os
from .base import BaseAdapter, SourceContent


class LocalFileAdapter(BaseAdapter):
    name = "local_file"

    _EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md", ".rst", ".csv", ".xlsx"}

    def can_handle(self, source: str) -> bool:
        if source.startswith(("http://", "https://")):
            return False
        _, ext = os.path.splitext(source.lower())
        return ext in self._EXTENSIONS or os.path.isfile(source)

    async def extract(self, source: str) -> SourceContent:
        if not os.path.exists(source):
            raise FileNotFoundError(f"File not found: {source}")

        _, ext = os.path.splitext(source.lower())
        title = os.path.basename(source)

        if ext == ".pdf":
            text = self._read_pdf(source)
        elif ext in (".docx", ".doc"):
            text = self._read_docx(source)
        elif ext in (".xlsx", ".csv"):
            text = self._read_table(source, ext)
        else:
            with open(source, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()

        return SourceContent(
            text=text,
            title=title,
            source_url=f"file://{os.path.abspath(source)}",
            source_type="local_file",
        )

    def _read_pdf(self, path: str) -> str:
        try:
            import pymupdf
            doc = pymupdf.open(path)
            return "\n".join(page.get_text() for page in doc)
        except ImportError:
            try:
                from pypdf import PdfReader
                reader = PdfReader(path)
                return "\n".join(page.extract_text() or "" for page in reader.pages)
            except ImportError:
                raise ImportError("pip install pymupdf or pypdf")

    def _read_docx(self, path: str) -> str:
        try:
            from docx import Document
            doc = Document(path)
            return "\n".join(p.text for p in doc.paragraphs)
        except ImportError:
            raise ImportError("pip install python-docx")

    def _read_table(self, path: str, ext: str) -> str:
        try:
            import pandas as pd
            if ext == ".csv":
                df = pd.read_csv(path)
            else:
                df = pd.read_excel(path)
            return df.to_markdown(index=False)
        except ImportError:
            raise ImportError("pip install pandas openpyxl")
