import json
import os
from core.document_processor import load_document, chunk_document
from core.retrieval import TfidfRetriever
from core.pipeline import run_pipeline
from core.meta_client import MetaAPIError

SAMPLES = os.path.join(os.path.dirname(__file__), "..", "sample_docs")


def retriever():
    chunks = []
    for f in sorted(os.listdir(SAMPLES)):
        if f.endswith(".md"):
            with open(os.path.join(SAMPLES, f), "rb") as fh:
                chunks += chunk_document(load_document(f, fh.read()))
    return TfidfRetriever(chunks)


class Scripted:
    """Returns replies in order: answer, claims, verdicts."""
    def __init__(self, *replies):
        self.replies = list(replies)

    def generate(self, prompt, instructions=None):
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


Q = "How many days do I have to request a refund?"
QUOTE = "request a refund within 30 days of purchase"


def verdict(label):
    return json.dumps([{"claim_id": 1, "label": label, "evidence_id": 1, "quote": QUOTE, "explanation": "x"}])


def test_supported_answer_is_allowed():
    c = Scripted("The refund period is 30 days [refund_policy.md].", '["The refund period is 30 days."]', verdict("SUPPORTED"))
    r = run_pipeline(c, retriever(), Q)
    assert r.decision.label == "ALLOW" and r.results[0].label == "SUPPORTED"


def test_contradicted_answer_is_blocked_or_revised():
    c = Scripted("The refund period is 60 days.", '["The refund period is 60 days."]', verdict("CONTRADICTED"))
    r = run_pipeline(c, retriever(), Q)
    assert r.decision.label in ("BLOCK", "REVISE") and "30 days" in r.results[0].evidence_text


def test_unsupported_answer_is_flagged_or_blocked():
    c = Scripted("Refunds are processed in 3 days.", '["Refunds are processed in 3 days."]',
                 json.dumps([{"claim_id": 1, "label": "UNVERIFIED", "evidence_id": None, "quote": "", "explanation": "not stated"}]))
    r = run_pipeline(c, retriever(), Q)
    assert r.decision.label in ("FLAG", "BLOCK") and r.results[0].label == "UNVERIFIED"


def test_no_evidence_makes_no_model_call():
    r = run_pipeline(Scripted(), retriever(), "Who won the cricket world cup?")
    assert r.answer is None and r.decision.label == "BLOCK"


def test_api_failure_raises_not_answers():
    try:
        run_pipeline(Scripted(MetaAPIError("invalid_api_key", "bad", 401)), retriever(), Q)
        assert False, "should have raised"
    except MetaAPIError as e:
        assert e.kind == "invalid_api_key"


def test_outdated_evidence_flags():
    q = "How long does standard shipping take?"
    quote = "Standard shipping takes 5 to 7 business days"
    c = Scripted("Standard shipping takes 5 to 7 business days.", '["Standard shipping takes 5 to 7 business days."]',
                 json.dumps([{"claim_id": 1, "label": "SUPPORTED", "evidence_id": 1, "quote": quote, "explanation": "x"}]))
    r = run_pipeline(c, retriever(), q)
    assert r.results[0].label == "SUPPORTED" and r.decision.label == "FLAG"