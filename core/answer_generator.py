"""Builds the grounded prompt and asks the Meta model for an answer."""
from typing import List
from core.meta_client import MetaClient
from core.retrieval import Evidence

SYSTEM_INSTRUCTIONS = (
    "You are a careful assistant that answers questions using ONLY the evidence passages provided. "
    "Do not use outside knowledge and do not invent facts, numbers, dates or policies. "
    "Cite the source filename in square brackets after each fact, like [refund_policy.md]. "
    "If the evidence does not contain enough information to answer, say exactly: "
    "'The available documents do not contain enough information to answer this question.' "
    "Keep the answer short and factual."
)


def build_prompt(question: str, evidence: List[Evidence]) -> str:
    blocks = [f"[{i}] Source: {e.source}\n{e.text}" for i, e in enumerate(evidence, 1)]
    return f"Question: {question}\n\nEvidence passages:\n\n" + "\n\n".join(blocks)


def generate_answer(client: MetaClient, question: str, evidence: List[Evidence]) -> str:
    """Raises MetaAPIError on failure. Caller must not treat errors as answers."""
    return client.generate(build_prompt(question, evidence), instructions=SYSTEM_INSTRUCTIONS)