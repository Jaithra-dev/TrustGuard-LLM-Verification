from datetime import date
from core.retrieval import Evidence
from core.verifier import ClaimResult, SUPPORTED, CONTRADICTED, UNVERIFIED
from core.freshness import assess_source, assess_evidence, CURRENT, OUTDATED, UNKNOWN
from core.decision_engine import decide, ALLOW, FLAG, BLOCK, REVISE

TODAY = date(2026, 11, 3)


def R(label, src="refund_policy.md"):
    return ClaimResult("c", label, "e", src if label != UNVERIFIED else None)


FRESH = [assess_source("refund_policy.md", "2026-09-15", TODAY)]


def test_freshness_labels():
    assert assess_source("a", "2026-09-15", TODAY).status == CURRENT
    assert assess_source("a", "2024-01-10", TODAY).status == OUTDATED
    assert assess_source("a", None, TODAY).status == UNKNOWN
    assert assess_source("a", "garbage", TODAY).status == UNKNOWN


def test_freshness_dedupes_sources():
    ev = [Evidence("a.md", "x", 1, 0, None), Evidence("a.md", "y", 1, 1, None)]
    assert len(assess_evidence(ev, TODAY)) == 1


def test_allow_when_all_supported_and_current():
    assert decide([R(SUPPORTED)] * 2, FRESH, 1).label == ALLOW


def test_flag_when_some_unverified():
    assert decide([R(SUPPORTED), R(SUPPORTED), R(UNVERIFIED)], FRESH, 1).label == FLAG


def test_block_when_mostly_unverified():
    assert decide([R(UNVERIFIED), R(UNVERIFIED), R(SUPPORTED)], FRESH, 1).label == BLOCK


def test_revise_when_minority_contradicted():
    assert decide([R(SUPPORTED), R(SUPPORTED), R(CONTRADICTED)], FRESH, 1).label == REVISE


def test_block_when_majority_contradicted():
    assert decide([R(CONTRADICTED), R(SUPPORTED)], FRESH, 1).label == BLOCK


def test_no_evidence_blocks():
    assert decide([], [], 0).label == BLOCK


def test_abstention_is_flagged():
    assert decide([], FRESH, 2, abstained=True).label == FLAG


def test_outdated_evidence_flags_supported_answer():
    old = [assess_source("shipping_policy.md", "2024-01-10", TODAY)]
    d = decide([R(SUPPORTED, "shipping_policy.md")], old, 1)
    assert d.label == FLAG and "outdated" in d.reasons[0]


def test_unknown_freshness_allows_with_note():
    unk = [assess_source("warranty_policy.md", None, TODAY)]
    d = decide([R(SUPPORTED, "warranty_policy.md")], unk, 1)
    assert d.label == ALLOW and d.notes