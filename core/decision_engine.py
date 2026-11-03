"""Runtime decision policy (evaluated top to bottom, first match wins):

 1. No evidence retrieved                          -> BLOCK
 2. Answer says documents lack the information     -> FLAG   (honest abstention, nothing to verify)
 3. No verifiable claims found                     -> FLAG
 4. Any CONTRADICTED claim                         -> BLOCK if >= 50% of claims are contradicted, else REVISE
 5. Any UNVERIFIED claim                           -> BLOCK if > 50% of claims are unverified, else FLAG
 6. All claims SUPPORTED, but a source behind them is POTENTIALLY OUTDATED -> FLAG
 7. All claims SUPPORTED                           -> ALLOW (sources with UNKNOWN date add a caution note)

ALLOW means "supported by the retrieved evidence", not "guaranteed true".
"""
from dataclasses import dataclass, field
from typing import List
from core.verifier import ClaimResult, SUPPORTED, CONTRADICTED, UNVERIFIED
from core.freshness import FreshnessResult, OUTDATED, UNKNOWN

ALLOW, FLAG, BLOCK, REVISE = "ALLOW", "FLAG", "BLOCK", "REVISE"
CONTRADICTION_BLOCK_SHARE = 0.5
UNVERIFIED_BLOCK_SHARE = 0.5


@dataclass
class Decision:
    label: str
    reasons: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    headline: str = ""   # one plain-English sentence for the UI banner


def decide(results: List[ClaimResult], freshness: List[FreshnessResult], n_evidence: int, abstained: bool = False) -> Decision:
    if n_evidence == 0:
        return Decision(BLOCK, ["No evidence was retrieved, so nothing can be verified."], headline="No evidence was found, so nothing can be verified.")
    total = len(results)
    if total == 0:
        if abstained:
            return Decision(FLAG, ["The answer states the documents do not contain enough information."], headline="The answer says the documents do not contain this information.")
        return Decision(FLAG, ["No verifiable factual claims were found in the answer."], headline="No checkable claims were found in the answer.")
    n_sup = sum(r.label == SUPPORTED for r in results)
    n_con = sum(r.label == CONTRADICTED for r in results)
    n_unv = sum(r.label == UNVERIFIED for r in results)
    counts = f"{n_sup} supported, {n_con} contradicted, {n_unv} unverified of {total} claims."
    if n_con:
        if n_con / total >= CONTRADICTION_BLOCK_SHARE:
            return Decision(BLOCK, [f"Most claims conflict with the evidence. {counts}"], headline="Most claims conflict with the evidence. The answer is withheld.")
        return Decision(REVISE, [f"Some claims conflict with the evidence and should be corrected. {counts}"], headline="Some claims conflict with the evidence and should be corrected.")
    if n_unv:
        if n_unv / total > UNVERIFIED_BLOCK_SHARE:
            return Decision(BLOCK, [f"Most claims cannot be verified from the evidence. {counts}"], headline="Most claims cannot be verified from the evidence. The answer is withheld.")
        return Decision(FLAG, [f"Some claims cannot be verified from the evidence. {counts}"], headline="Some claims cannot be verified. Review before relying on this answer.")
    by_source = {f.source: f for f in freshness}
    used = [by_source[src] for src in sorted({r.source for r in results if r.source in by_source})]
    notes = [f"{f.source} has no known last-updated date, so its freshness cannot be judged." for f in used if f.status == UNKNOWN]
    old = [f for f in used if f.status == OUTDATED]
    if old:
        names = ", ".join(f"{f.source} ({f.last_updated})" for f in old)
        return Decision(FLAG, [f"All claims are supported, but the evidence may be outdated: {names}. {counts}"], notes,
                        headline="The claims match the evidence, but the source document may be out of date.")
    return Decision(ALLOW, [f"Every claim is supported by the retrieved evidence. {counts}"], notes,
                    headline="Every claim is supported by the retrieved evidence.")