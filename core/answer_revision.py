"""Answer revision: rewrite an answer so it keeps only what the evidence supports."""
from typing import List
from core.meta_client import MetaClient
from core.retrieval import Evidence
from core.verifier import ClaimResult, SUPPORTED, CONTRADICTED
from core.claim_extractor import ABSTAIN_PHRASES

INSUFFICIENT = "The available documents do not contain enough information to answer this question."

REVISE_INSTRUCTIONS = (
    "You revise an answer so that it is fully supported by the evidence passages. Rules:\n"
    "1. Keep every claim marked SUPPORTED.\n"
    "2. For every claim marked CONTRADICTED, replace it with what the evidence actually says.\n"
    "3. Delete every claim marked UNVERIFIED. Do not guess or fill gaps from outside knowledge.\n"
    "4. Add nothing that the evidence passages do not state.\n"
    "5. Cite the source filename in square brackets after each fact, like [refund_policy.md].\n"
    f"6. If nothing can be stated from the evidence, reply exactly: {INSUFFICIENT}\n"
    "Return only the revised answer, short and factual."
)


def build_revision_prompt(question: str, original: str, results: List[ClaimResult], evidence: List[Evidence]) -> str:
    lines = []
    for i, r in enumerate(results, 1):
        extra = ""
        if r.label in (SUPPORTED, CONTRADICTED) and r.quote:
            extra = f' | evidence ({r.source}): "{r.quote}"'
        lines.append(f"{i}. [{r.label}] {r.claim}{extra}")
    ev = "\n\n".join(f"[{i}] Source: {e.source}\n{e.text}" for i, e in enumerate(evidence, 1))
    return (f"Question: {question}\n\nOriginal answer:\n{original}\n\n"
            f"Verification report:\n" + "\n".join(lines) + f"\n\nEvidence passages:\n\n{ev}")


def revise_answer(client: MetaClient, question: str, original: str, results: List[ClaimResult], evidence: List[Evidence]) -> str:
    """Raises MetaAPIError on failure. The result is NOT trusted: the caller must verify it again."""
    return client.generate(build_revision_prompt(question, original, results, evidence), instructions=REVISE_INSTRUCTIONS)