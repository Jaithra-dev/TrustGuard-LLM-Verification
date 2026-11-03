import json
from core.pipeline import run_pipeline, revise_and_reverify
from core.meta_client import MetaAPIError
from core.answer_revision import build_revision_prompt, INSUFFICIENT
from tests.test_pipeline import retriever, Scripted, Q, QUOTE, verdict


def contradicted_run():
    c = Scripted("The refund period is 60 days.", '["The refund period is 60 days."]', verdict("CONTRADICTED"))
    return run_pipeline(c, retriever(), Q)


def test_revision_is_reverified_and_allowed():
    res = contradicted_run()
    assert res.decision.label in ("BLOCK", "REVISE")
    c = Scripted("The refund period is 30 days [refund_policy.md].", '["The refund period is 30 days."]', verdict("SUPPORTED"))
    rev = revise_and_reverify(c, res)
    assert "30 days" in rev.answer and rev.decision.label == "ALLOW" and rev.results[0].label == "SUPPORTED"
    assert res.answer == "The refund period is 60 days."  # original untouched


def test_revision_that_adds_unsupported_claim_is_not_allowed():
    res = contradicted_run()
    unv = json.dumps([{"claim_id": 1, "label": "UNVERIFIED", "evidence_id": None, "quote": "", "explanation": "no"}])
    c = Scripted("Refunds take 1 day.", '["Refunds take 1 day."]', unv)
    assert revise_and_reverify(c, res).decision.label in ("FLAG", "BLOCK")


def test_revision_to_insufficient_is_flagged_honestly():
    res = contradicted_run()
    c = Scripted(INSUFFICIENT, "[]")
    rev = revise_and_reverify(c, res)
    assert rev.decision.label == "FLAG" and rev.results == []


def test_revision_api_failure_raises():
    res = contradicted_run()
    try:
        revise_and_reverify(Scripted(MetaAPIError("rate_limited", "x", 429)), res)
        assert False
    except MetaAPIError:
        pass


def test_prompt_contains_verdicts_and_quote():
    res = contradicted_run()
    p = build_revision_prompt(res.question, res.answer, res.results, res.evidence)
    assert "[CONTRADICTED]" in p and QUOTE in p