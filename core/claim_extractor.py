"""Claim extraction: LLM-based (structured JSON) with a deterministic rule-based fallback."""
import re
from dataclasses import dataclass
from typing import List
from core.meta_client import MetaClient, MetaAPIError
from core.llm_json import parse_json_array

ABSTAIN_PHRASES = ("do not contain enough information", "does not contain enough information",
                   "not enough information", "insufficient information", "insufficient evidence")

EXTRACT_INSTRUCTIONS = (
    "You split an answer into atomic factual claims. Each claim must be a single, self-contained "
    "sentence that can be checked independently (replace pronouns with the thing they refer to). "
    "Remove source citations like [file.md]. Do not add any information that is not in the answer. "
    "Skip statements that only say information is unavailable. "
    "Return ONLY a JSON array of strings, nothing else. Return [] if there are no factual claims."
)


@dataclass
class ClaimExtraction:
    claims: List[str]
    method: str        # "llm" or "rules"
    abstained: bool    # answer said the documents lack the information


def is_abstention(text: str) -> bool:
    t = text.lower()
    return any(p in t for p in ABSTAIN_PHRASES)


def extract_claims_rules(answer: str) -> List[str]:
    text = re.sub(r"\[[^\]]*\.(?:md|txt|pdf)\]", "", answer, flags=re.I)
    text = re.sub(r"[ \t]+([.!?,;])", r"\1", text)  # tidy "days ." left behind by removed citations
    claims = []
    for line in text.splitlines():
        line = re.sub(r"^\s*(?:[-*\u2022]|\d+[.)])\s*", "", line).strip()
        for s in re.split(r"(?<=[.!?])\s+", line):
            s = s.strip()
            if len(s.split()) < 3 or s.endswith("?") or is_abstention(s):
                continue
            claims.append(s)
    return claims


def extract_claims(client: MetaClient, answer: str, use_llm: bool = True) -> ClaimExtraction:
    abstained = is_abstention(answer)
    if use_llm:
        try:
            raw = client.generate(f"Answer:\n{answer}", instructions=EXTRACT_INSTRUCTIONS)
            claims = [c.strip() for c in parse_json_array(raw) if isinstance(c, str) and c.strip()]
            if claims or abstained:
                return ClaimExtraction(claims, "llm", abstained)
        except (MetaAPIError, ValueError):
            pass  # fall through to deterministic extraction
    return ClaimExtraction(extract_claims_rules(answer), "rules", abstained)