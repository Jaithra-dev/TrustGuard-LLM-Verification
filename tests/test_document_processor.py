from core.document_processor import load_document, chunk_document


def test_unsupported_empty_and_blank():
    assert load_document("a.docx", b"x").error
    assert load_document("a.txt", b"").error
    assert load_document("a.txt", b"   \n  ").error


def test_corrupt_pdf_does_not_crash():
    assert load_document("bad.pdf", b"not a pdf").error


def test_date_found_only_when_present():
    assert load_document("a.md", b"# T\n\nLast updated: 2026-01-02\n\nHello").last_updated == "2026-01-02"
    assert load_document("b.md", b"# T\n\nHello world").last_updated is None


def test_chunking_keeps_source_and_splits_long_text():
    text = "\n\n".join(f"Paragraph {i}. " + "word " * 80 for i in range(6))
    doc = load_document("long.txt", text.encode())
    chunks = chunk_document(doc)
    assert len(chunks) > 1
    assert all(c.source == "long.txt" and len(c.text) <= 800 for c in chunks)