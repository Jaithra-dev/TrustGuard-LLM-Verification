"""End-to-end workflow: question -> evidence -> answer -> claims -> verification -> freshness -> decision."""
from dataclasses import dataclass, field
from typing import List, Optional
from core.meta_client import MetaClient
from core.retrieval import BaseRetriever, Evidence
from core.answer_generator import generate_answer
from core.claim_extractor import extract_claims
from core.verifier import verify_claims, ClaimResult, CONTRADICTED, UNVERIFIED
from core.freshness import assess_evidence, FreshnessResult
from core.decision_engine import decide, Decision
from core.answer_revision import revise_answer


@dataclass
class RevisionResult:
    answer: str
    claims: List[str] = field(default_factory=list)
    results: List[ClaimResult] = field(default_factory=list)
    decision: Optional[Decision] = None
    extraction_method: str = ""
    verification_method: str = ""


@dataclass
class PipelineResult:
    question: str
    evidence: List[Evidence] = field(default_factory=list)
    answer: Optional[str] = None
    claims: List[str] = field(default_factory=list)
    results: List[ClaimResult] = field(default_factory=list)
    freshness: List[FreshnessResult] = field(default_factory=list)
    decision: Optional[Decision] = None
    extraction_method: str = ""
    verification_method: str = ""
    verified: bool = False
    revision: Optional[RevisionResult] = None
    answer_source: str = "model"   # "model" or "provided" (demo mode)


def run_pipeline(client: MetaClient, retriever: BaseRetriever, question: str, verify: bool = True) -> PipelineResult:
    """Raises MetaAPIError if the ANSWER call fails (so errors are never shown as answers).
    Later verification steps fall back to deterministic methods instead of failing."""
    res = PipelineResult(question)
    res.evidence = retriever.search(question)
    if not res.evidence:
        res.decision = decide([], [], 0)
        return res
    res.answer = generate_answer(client, question, res.evidence)
    res.freshness = assess_evidence(res.evidence)
    if not verify:
        return res
    _verify_into(client, res)
    return res


def _verify_into(client: MetaClient, res: PipelineResult) -> None:
    ex = extract_claims(client, res.answer)
    res.claims, res.extraction_method = ex.claims, ex.method
    res.results, res.verification_method = verify_claims(client, ex.claims, res.evidence)
    res.decision = decide(res.results, res.freshness, len(res.evidence), ex.abstained)
    res.verified = True


def verify_provided_answer(client: MetaClient, retriever: BaseRetriever, question: str, answer: str) -> PipelineResult:
    """Demo/test mode: check an answer someone else wrote (e.g. a deliberately wrong one)."""
    res = PipelineResult(question, answer_source="provided")
    res.evidence = retriever.search(f"{question} {answer}")
    if not res.evidence:
        res.decision = decide([], [], 0)
        return res
    res.answer = answer.strip()
    res.freshness = assess_evidence(res.evidence)
    _verify_into(client, res)
    return res


def needs_revision(res: PipelineResult) -> bool:
    """True only if some claim is contradicted or unverified (revision cannot fix outdated evidence)."""
    return any(r.label in (CONTRADICTED, UNVERIFIED) for r in res.results)


def revise_and_reverify(client: MetaClient, res: PipelineResult) -> RevisionResult:
    """Rewrite the answer from supported evidence, then run the SAME verification on the rewrite.
    Raises MetaAPIError if the revision call fails (the original answer stays untouched)."""
    revised = revise_answer(client, res.question, res.answer, res.results, res.evidence)
    ex = extract_claims(client, revised)
    results, method = verify_claims(client, ex.claims, res.evidence)
    decision = decide(results, res.freshness, len(res.evidence), ex.abstained)
    return RevisionResult(revised, ex.claims, results, decision, ex.method, method)