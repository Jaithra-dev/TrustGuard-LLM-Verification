import os
from core.document_processor import load_document, chunk_document
from core.retrieval import TfidfRetriever

SAMPLES = os.path.join(os.path.dirname(__file__), "..", "sample_docs")


def _retriever():
    chunks = []
    for f in sorted(os.listdir(SAMPLES)):
        if f.endswith(".md"):
            with open(os.path.join(SAMPLES, f), "rb") as fh:
                chunks += chunk_document(load_document(f, fh.read()))
    return TfidfRetriever(chunks)


def test_finds_refund_passage():
    ev = _retriever().search("How many days do I have to request a refund?")
    assert ev and ev[0].source == "refund_policy.md"
    assert "30 days" in ev[0].text


def test_finds_shipping_passage():
    ev = _retriever().search("How long does standard shipping take?")
    assert ev and ev[0].source == "shipping_policy.md"


def test_no_evidence_for_unrelated_question():
    assert _retriever().search("Who won the cricket world cup?") == []


def test_empty_index_and_empty_query_are_safe():
    assert TfidfRetriever([]).search("refund") == []
    assert _retriever().search("   ") == []


def test_word_forms_match_ship_vs_shipping():
    ev = _retriever().search("Do you ship to Australia?")
    assert ev and ev[0].source == "shipping_policy.md"


def test_refunds_matches_refund():
    ev = _retriever().search("Are refunds possible?")
    assert ev and ev[0].source == "refund_policy.md"