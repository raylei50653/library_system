# chat/services/rag_store.py
from __future__ import annotations
from typing import List, Dict, Tuple
from math import sqrt
from django.db import transaction
from ..models import KnowledgeDoc, KnowledgeChunk
from .ollama_client import embed_texts

def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b): return 0.0
    dot = sum(x*y for x, y in zip(a, b))
    na = sqrt(sum(x*x for x in a)); nb = sqrt(sum(y*y for y in b))
    if na == 0 or nb == 0: return 0.0
    return dot / (na * nb)

def _chunk(text: str, max_len: int = 500) -> List[str]:
    text = (text or "").strip()
    if not text: return []
    out, buf, count = [], [], 0
    for ch in text:
        buf.append(ch); count += 1
        if count >= max_len and ch in "。！？\n\r":
            out.append("".join(buf).strip()); buf, count = [], 0
    if buf: out.append("".join(buf).strip())
    return out

@transaction.atomic
def upsert_document(title: str, content: str, source: str = "", meta: Dict | None = None) -> int:
    doc = KnowledgeDoc.objects.create(title=title, source=source, meta=meta or {})
    chunks = _chunk(content)
    vecs = embed_texts(chunks) if chunks else []
    for i, (txt, vec) in enumerate(zip(chunks, vecs)):
        KnowledgeChunk.objects.create(doc=doc, text=txt, vec=vec, order=i,
                                      meta={"title": title, "source": source})
    return doc.id

def search_topk(query: str, k: int = 4) -> List[Dict]:
    qs = KnowledgeChunk.objects.all().select_related("doc")
    if not qs.exists(): return []
    qvec = embed_texts([query])[0]
    scored: List[Tuple[float, KnowledgeChunk]] = []
    for ch in qs.iterator():
        s = _cosine(qvec, ch.vec or [])
        if s > 0: scored.append((s, ch))
    scored.sort(key=lambda x: x[0], reverse=True)
    out: List[Dict] = []
    for score, ch in scored[:k]:
        out.append({"text": ch.text,
                    "meta": {"title": ch.meta.get("title") or ch.doc.title,
                             "score": round(score, 3), "doc": ch.doc_id}})
    return out
