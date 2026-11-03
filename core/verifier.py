"""Claim-by-claim verification against retrieved evidence.

Primary method: an LLM judge returns a structured verdict per claim. Its verdicts are then CHECKED
deterministically: SUPPORTED/CONTRADICTED labels need a real evidence passage and a quote that
actually appears in it, and numbers in a SUPPORTED claim must appear in that passage. Otherwise the
claim is downgraded to UNVERIFIED. Missing evidence is never treated as proof a claim is false.
Fallback (API failure): a simple lexical matcher that can only say SUPPORTED or UNVERIFIED.
"""
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple
from core.meta_client import MetaClient, MetaAPIError
from core.llm_json import parse_json_array
from core.retrieval import Evidence

SUPPORTED, CONTRADICTED, UNVERIFIED = "SUPPORTED", "CONTRADICTED", "UNVERIFIED"
LABELS = (SUPPORTED, CONTRADICTED, UNVERIFIED)
_STOP = set("a an the is are was were be been of to in on at for and or by with from as it its this that "
            "can may will within after before their there they customers customer".split())

VERIFY_INSTRUCTIONS = (
    "You are a strict fact-checker. For each numbered claim, decide using ONLY the numbered evidence "
    "passages (no outside knowledge):\n"
    "SUPPORTED = a passage explicitly states the claim.\n"
    "CONTRADICTED = a passage states something that directly conflicts with the claim (different number, "
    "opposite rule, etc.).\n"
    "UNVERIFIED = the evidence does not establish whether the claim is true. Absence of information is "
    "UNVERIFIED, never CONTRADICTED.\n"
    "Return ONLY a JSON array with one object per claim: "
    '{"claim_id": 1, "label": "SUPPORTED|CONTRADICTED|UNVERIFIED", "evidence_id": 1 or null, '
    '"quote": "exact words copied from that passage, or empty", "explanation": "one short sentence"}.'
)


@dataclass
class ClaimResult:
    claim: str
    label: str
    explanation: str
    source: Optional[str] = None
    evidence_text: Optional[str] = None
    quote: Optional[str] = None


def _tokens(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _numbers(text: str) -> set:
    return set(re.findall(r"\d+(?:\.\d+)?", text.replace(",", "")))


def quote_in_text(quote: str, text: str) -> bool:
    qt = _tokens(quote)
    if len(qt) < 3:
        return False
    et = set(_tokens(text))
    return sum(t in et for t in qt) / len(qt) >= 0.85


def _build_prompt(claims: List[str], evidence: List[Evidence]) -> str:
    c = "\n".join(f"{i}. {t}" for i, t in enumerate(claims, 1))
    e = "\n\n".join(f"[{i}] (source: {x.source})\n{x.text}" for i, x in enumerate(evidence, 1))
    return f"Claims:\n{c}\n\nEvidence passages:\n\n{e}"


def _check_verdict(claim: str, v: dict, evidence: List[Evidence]) -> ClaimResult:
    label = str(v.get("label", "")).upper().strip()
    explanation = str(v.get("explanation", "")).strip() or "No explanation given."
    if label not in LABELS:
        return ClaimResult(claim, UNVERIFIED, "Judge returned an unusable verdict.")
    if label == UNVERIFIED:
        return ClaimResult(claim, UNVERIFIED, explanation)
    try:
        ev = evidence[int(v.get("evidence_id")) - 1]
    except (TypeError, ValueError, IndexError):
        return ClaimResult(claim, UNVERIFIED, f"Downgraded: judge gave {label} without a valid evidence passage.")
    quote = str(v.get("quote") or "").strip()
    if not quote_in_text(quote, ev.text):
        return ClaimResult(claim, UNVERIFIED, f"Downgraded: judge said {label} but its quote was not found in the evidence.")
    if label == SUPPORTED and not _numbers(claim) <= _numbers(ev.text):
        return ClaimResult(claim, UNVERIFIED, "Downgraded: a number in the claim does not appear in the cited evidence.")
    return ClaimResult(claim, label, explanation, ev.source, ev.text, quote)


def _verify_lexical(claims: List[str], evidence: List[Evidence]) -> List[ClaimResult]:
    out = []
    for claim in claims:
        ct = [t for t in _tokens(claim) if t not in _STOP]
        best, best_sent, best_ev = 0.0, "", None
        for ev in evidence:
            for s in re.split(r"(?<=[.!?])\s+|\n+", ev.text):
                st = set(_tokens(s))
                if ct and (r := sum(t in st for t in ct) / len(ct)) > best and _numbers(claim) <= _numbers(s):
                    best, best_sent, best_ev = r, s.strip(), ev
        if best >= 0.75 and best_ev:
            out.append(ClaimResult(claim, SUPPORTED, "Matched by word overlap (fallback checker).",
                                   best_ev.source, best_ev.text, best_sent))
        else:
            out.append(ClaimResult(claim, UNVERIFIED, "No matching passage found (fallback checker; it cannot detect contradictions)."))
    return out


def verify_claims(client: MetaClient, claims: List[str], evidence: List[Evidence]) -> Tuple[List[ClaimResult], str]:
    """Returns (results, method). method is 'llm', 'lexical-fallback' or 'none'."""
    if not claims:
        return [], "none"
    if not evidence:
        return [ClaimResult(c, UNVERIFIED, "No evidence was retrieved.") for c in claims], "none"
    try:
        raw = client.generate(_build_prompt(claims, evidence), instructions=VERIFY_INSTRUCTIONS)
        verdicts = {}
        for v in parse_json_array(raw):
            if isinstance(v, dict):
                try:
                    verdicts[int(v.get("claim_id"))] = v
                except (TypeError, ValueError):
                    pass
        results = [_check_verdict(c, verdicts[i], evidence) if i in verdicts
                   else ClaimResult(c, UNVERIFIED, "Judge returned no verdict for this claim.")
                   for i, c in enumerate(claims, 1)]
        return results, "llm"
    except (MetaAPIError, ValueError):
        return _verify_lexical(claims, evidence), "lexical-fallback"