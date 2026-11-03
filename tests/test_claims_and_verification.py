import json
from core.meta_client import MetaAPIError
from core.retrieval import Evidence
from core.claim_extractor import extract_claims, extract_claims_rules, is_abstention
from core.verifier import verify_claims, SUPPORTED, CONTRADICTED, UNVERIFIED

EV = [Evidence("refund_policy.md",
               "Customers may request a refund within 30 days of purchase. Refund requests must be submitted by email.",
               0.5, 0, "2026-09-15")]


class Fake:
    def __init__(self, reply=None, error=None):
        self.reply, self.error = reply, error

    def generate(self, prompt, instructions=None):
        if self.error:
            raise self.error
        return self.reply


def test_rule_extraction_strips_citations_and_abstention():
    ans = "The refund period is 30 days [refund_policy.md]. Refunds go by email.\nThe available documents do not contain enough information to answer this question."
    assert extract_claims_rules(ans) == ["The refund period is 30 days.", "Refunds go by email."]
    assert is_abstention(ans)


def test_llm_extraction_parses_fenced_json():
    c = extract_claims(Fake('```json\n["A is 1.", "B is 2."]\n```'), "A is 1. B is 2.")
    assert c.claims == ["A is 1.", "B is 2."] and c.method == "llm"


def test_extraction_falls_back_on_api_error():
    c = extract_claims(Fake(error=MetaAPIError("network", "x")), "The refund period is 30 days.")
    assert c.method == "rules" and c.claims


def v(**kw):
    return json.dumps([dict({"claim_id": 1, "label": "SUPPORTED", "evidence_id": 1,
                             "quote": "request a refund within 30 days of purchase", "explanation": "ok"}, **kw)])


def test_supported_claim():
    r, m = verify_claims(Fake(v()), ["The refund period is 30 days."], EV)
    assert m == "llm" and r[0].label == SUPPORTED and r[0].source == "refund_policy.md"


def test_contradicted_claim_keeps_evidence():
    r, _ = verify_claims(Fake(v(label="CONTRADICTED")), ["The refund period is 60 days."], EV)
    assert r[0].label == CONTRADICTED and "30 days" in r[0].evidence_text


def test_fabricated_quote_is_downgraded():
    r, _ = verify_claims(Fake(v(quote="refunds are always instant and free for everyone")), ["Refunds are instant."], EV)
    assert r[0].label == UNVERIFIED


def test_supported_with_wrong_number_is_downgraded():
    r, _ = verify_claims(Fake(v()), ["The refund period is 90 days."], EV)
    assert r[0].label == UNVERIFIED


def test_invalid_evidence_id_is_downgraded():
    r, _ = verify_claims(Fake(v(evidence_id=7)), ["The refund period is 30 days."], EV)
    assert r[0].label == UNVERIFIED


def test_garbage_reply_falls_back_to_lexical():
    r, m = verify_claims(Fake("sorry I cannot"), ["Customers may request a refund within 30 days."], EV)
    assert m == "lexical-fallback" and r[0].label == SUPPORTED


def test_api_error_falls_back_and_never_says_contradicted():
    r, m = verify_claims(Fake(error=MetaAPIError("rate_limited", "x")), ["The refund period is 60 days."], EV)
    assert m == "lexical-fallback" and r[0].label == UNVERIFIED


def test_no_evidence_means_unverified_not_false():
    r, _ = verify_claims(Fake(v()), ["Anything."], [])
    assert r[0].label == UNVERIFIED