import json
from core.pipeline import verify_provided_answer, needs_revision, run_pipeline
from tests.test_pipeline import retriever, Scripted, Q, verdict


def test_provided_wrong_answer_is_caught():
    c = Scripted('["You can request a refund within 60 days."]', verdict("CONTRADICTED"))
    r = verify_provided_answer(c, retriever(), Q, "You can request a refund within 60 days.")
    assert r.answer_source == "provided" and r.decision.label in ("BLOCK", "REVISE") and needs_revision(r)
    assert r.decision.headline


def test_provided_answer_without_evidence_is_blocked_and_makes_no_call():
    r = verify_provided_answer(Scripted(), retriever(), "Who won the cricket world cup?", "Australia won.")
    assert r.decision.label == "BLOCK" and r.answer is None


def test_outdated_only_does_not_need_revision():
    q = "How long does standard shipping take?"
    quote = "Standard shipping takes 5 to 7 business days"
    c = Scripted("Standard shipping takes 5 to 7 business days.", '["Standard shipping takes 5 to 7 business days."]',
                 json.dumps([{"claim_id": 1, "label": "SUPPORTED", "evidence_id": 1, "quote": quote, "explanation": "x"}]))
    r = run_pipeline(c, retriever(), q)
    assert r.decision.label == "FLAG" and not needs_revision(r)