"""Evidence retrieval. TF-IDF today; swap in embeddings later by implementing BaseRetriever."""
import re
from dataclasses import dataclass
from typing import List, Optional
from core.document_processor import Chunk


def _stem(w: str) -> str:
    """Tiny suffix stripper so 'ship', 'ships', 'shipping', 'shipped' all match."""
    if len(w) <= 3 or w.isdigit():
        return w
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    for suf in ("ing", "ed"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            w = w[:-len(suf)]
            if len(w) >= 3 and w[-1] == w[-2] and w[-1] not in "aeiouls":
                w = w[:-1]  # shipp -> ship
            break
    else:
        if w.endswith(("sses", "shes", "ches", "xes", "zes")):
            w = w[:-2]
        elif w.endswith("s") and not w.endswith(("ss", "us", "is")):
            w = w[:-1]
    if w.endswith("e") and len(w) > 4:
        w = w[:-1]  # purchase / purchased -> purchas
    return w


def analyze(text: str) -> List[str]:
    """Lowercase, drop stop words, stem, and add stem bigrams."""
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
    words = [_stem(w) for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in ENGLISH_STOP_WORDS]
    return words + [f"{a} {b}" for a, b in zip(words, words[1:])]


@dataclass
class Evidence:
    source: str
    text: str
    score: float
    chunk_id: int
    last_updated: Optional[str] = None


class BaseRetriever:
    def search(self, query: str, top_k: int = 4) -> List[Evidence]:
        raise NotImplementedError


class TfidfRetriever(BaseRetriever):
    def __init__(self, chunks: List[Chunk], min_score: float = 0.08):
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.chunks = chunks
        self.min_score = min_score
        self._vec = None
        self._matrix = None
        if chunks:
            try:
                self._vec = TfidfVectorizer(analyzer=analyze, sublinear_tf=True)
                self._matrix = self._vec.fit_transform([c.text for c in chunks])
            except ValueError:  # empty vocabulary
                self._vec = None

    def search(self, query: str, top_k: int = 4) -> List[Evidence]:
        if self._vec is None or not query.strip():
            return []
        try:
            q = self._vec.transform([query])
        except ValueError:
            return []
        if q.nnz == 0:  # no query term appears in any document
            return []
        scores = (self._matrix @ q.T).toarray().ravel()
        order = scores.argsort()[::-1][:top_k]
        return [
            Evidence(self.chunks[i].source, self.chunks[i].text, float(scores[i]),
                     self.chunks[i].chunk_id, self.chunks[i].last_updated)
            for i in order if scores[i] >= self.min_score
        ]