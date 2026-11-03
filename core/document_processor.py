"""Load PDF / TXT / Markdown files, extract text, find a real last-updated date, chunk into passages."""
import io
import re
from dataclasses import dataclass
from typing import List, Optional

SUPPORTED = (".pdf", ".txt", ".md", ".markdown")
_DATE_RE = re.compile(r"(?i)last\s+(?:updated|modified|reviewed)\s*[:\-]\s*(\d{4}-\d{2}-\d{2})")


@dataclass
class Document:
    name: str
    text: str = ""
    last_updated: Optional[str] = None   # ISO date string, only if found in the file. Never invented.
    error: Optional[str] = None          # set when the file could not be used

    @property
    def ok(self) -> bool:
        return self.error is None and bool(self.text.strip())


@dataclass
class Chunk:
    source: str
    text: str
    chunk_id: int
    last_updated: Optional[str] = None


def _pdf_text_and_date(data: bytes):
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        raise ValueError("PDF is password-protected.")
    text = "\n\n".join((p.extract_text() or "") for p in reader.pages)
    date = None
    try:
        md = reader.metadata.modification_date if reader.metadata else None
        if md:
            date = md.date().isoformat()
    except Exception:
        date = None
    return text, date


def load_document(name: str, data: bytes) -> Document:
    """Never raises: problems are reported in Document.error."""
    lower = name.lower()
    if not lower.endswith(SUPPORTED):
        return Document(name, error="Unsupported file type (use PDF, TXT or Markdown).")
    if not data:
        return Document(name, error="File is empty.")
    try:
        meta_date = None
        if lower.endswith(".pdf"):
            text, meta_date = _pdf_text_and_date(data)
        else:
            text = data.decode("utf-8", errors="replace")
    except Exception as e:
        return Document(name, error=f"Could not read file: {e}")
    if not text.strip():
        return Document(name, error="No readable text found (scanned PDF or empty file).")
    m = _DATE_RE.search(text)
    date = m.group(1) if m else meta_date
    return Document(name, text=text, last_updated=date)


def chunk_document(doc: Document, min_chars: int = 200, max_chars: int = 700) -> List[Chunk]:
    """Paragraph-based chunking. Short paragraphs (e.g. headings) are merged with the next one."""
    if not doc.ok:
        return []
    paras = [p.strip() for p in re.split(r"\n\s*\n", doc.text) if p.strip()]
    pieces: List[str] = []
    for p in paras:  # split oversized paragraphs on sentence boundaries
        if len(p) <= max_chars:
            pieces.append(p)
            continue
        cur = ""
        for s in re.split(r"(?<=[.!?])\s+", p):
            if cur and len(cur) + len(s) + 1 > max_chars:
                pieces.append(cur)
                cur = s
            else:
                cur = f"{cur} {s}".strip()
        if cur:
            pieces.append(cur)
    chunks: List[str] = []
    buf = ""
    for p in pieces:
        if buf and len(buf) + len(p) + 2 > max_chars:
            chunks.append(buf)
            buf = p
        else:
            buf = f"{buf}\n\n{p}".strip()
        if len(buf) >= min_chars:
            chunks.append(buf)
            buf = ""
    if buf:
        chunks.append(buf)
    return [Chunk(doc.name, t, i, doc.last_updated) for i, t in enumerate(chunks)]