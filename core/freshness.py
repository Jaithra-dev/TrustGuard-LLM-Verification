"""Evidence freshness. Dates come only from the documents themselves; unknown stays unknown."""
from dataclasses import dataclass
from datetime import date
from typing import List, Optional
from core.retrieval import Evidence

CURRENT, OUTDATED, UNKNOWN = "CURRENT", "POTENTIALLY OUTDATED", "UNKNOWN"
DEFAULT_MAX_AGE_DAYS = 365


@dataclass
class FreshnessResult:
    source: str
    last_updated: Optional[str]
    age_days: Optional[int]
    status: str


def assess_source(source: str, last_updated: Optional[str], today: Optional[date] = None,
                  max_age_days: int = DEFAULT_MAX_AGE_DAYS) -> FreshnessResult:
    today = today or date.today()
    try:
        d = date.fromisoformat(last_updated) if last_updated else None
    except ValueError:
        d = None
    if d is None:
        return FreshnessResult(source, last_updated, None, UNKNOWN)
    age = max((today - d).days, 0)
    return FreshnessResult(source, last_updated, age, CURRENT if age <= max_age_days else OUTDATED)


def assess_evidence(evidence: List[Evidence], today: Optional[date] = None,
                    max_age_days: int = DEFAULT_MAX_AGE_DAYS) -> List[FreshnessResult]:
    seen, out = set(), []
    for e in evidence:
        if e.source not in seen:
            seen.add(e.source)
            out.append(assess_source(e.source, e.last_updated, today, max_age_days))
    return out