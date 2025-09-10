import os
import json
from typing import List, Dict, Optional, Tuple

import numpy as np

from src.data.database import get_all_lessons


INDEX_PATH = "lessons_index.faiss"
IDS_PATH = "lessons_index_ids.json"
EMB_PATH = "lessons_embeddings.npy"  # fallback
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def _load_embedder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODEL_NAME)


def _try_import_faiss():
    try:
        import faiss  # type: ignore
        return faiss
    except Exception:
        return None


def _lesson_text(lesson: Dict) -> str:
    msg = lesson.get("commit_message", "")
    before = (lesson.get("before_code") or "")[:2000]
    after = (lesson.get("after_code") or "")[:2000]
    meta = []
    for k in ["file_path", "framework", "language", "change_type", "tags"]:
        v = lesson.get(k)
        if v:
            meta.append(f"{k}:{v}")
    meta_str = " | ".join(meta)
    return f"{msg}\nMETA: {meta_str}\nBEFORE:\n{before}\nAFTER:\n{after}"


def build_index() -> Tuple[int, int]:
    """Build and persist a semantic index over lessons. Returns (num_lessons, dim)."""
    lessons = get_all_lessons(limit=5000)
    if not lessons:
        # Create empty artifacts
        np.save(EMB_PATH, np.zeros((0, 384), dtype=np.float32))
        with open(IDS_PATH, "w") as f:
            json.dump([], f)
        return 0, 0

    texts = [_lesson_text(l) for l in lessons]
    ids = [l["id"] for l in lessons]

    model = _load_embedder()
    embs = model.encode(texts, batch_size=64, show_progress_bar=False, normalize_embeddings=True)
    embs = np.asarray(embs, dtype=np.float32)

    # Persist ids
    with open(IDS_PATH, "w") as f:
        json.dump(ids, f)

    # Try FAISS, else save numpy for fallback
    faiss = _try_import_faiss()
    if faiss is not None and embs.size > 0:
        dim = embs.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(embs)
        faiss.write_index(index, INDEX_PATH)
        return len(ids), dim
    else:
        np.save(EMB_PATH, embs)
        return len(ids), embs.shape[1] if embs.size > 0 else 0


def _load_ids() -> List[str]:
    if not os.path.exists(IDS_PATH):
        return []
    with open(IDS_PATH, "r") as f:
        return json.load(f)


def _load_index():
    faiss = _try_import_faiss()
    if faiss is not None and os.path.exists(INDEX_PATH):
        return faiss.read_index(INDEX_PATH), "faiss"
    if os.path.exists(EMB_PATH):
        embs = np.load(EMB_PATH)
        return embs, "numpy"
    return None, None


def ensure_index_built():
    if os.path.exists(INDEX_PATH) and os.path.exists(IDS_PATH):
        return
    if os.path.exists(EMB_PATH) and os.path.exists(IDS_PATH):
        return
    build_index()


def retrieve(query: str, top_k: int = 3, filters: Optional[Dict] = None) -> List[Dict]:
    """Retrieve top-k lessons similar to the query with optional metadata filters."""
    ensure_index_built()
    ids = _load_ids()
    index, kind = _load_index()
    if index is None or not ids:
        return []

    # Simple metadata filtering by reloading lessons and masking after similarity search
    lessons = {l["id"]: l for l in get_all_lessons(limit=5000)}

    model = _load_embedder()
    q = model.encode([query], normalize_embeddings=True)
    q = np.asarray(q, dtype=np.float32)

    if kind == "faiss":
        import faiss  # type: ignore
        D, I = index.search(q, k=min(top_k * 5, len(ids)))
        cand_ids = [ids[i] for i in I[0] if i < len(ids)]
    else:
        # Cosine sim via dot product since normalized
        embs = index  # numpy array
        sims = (embs @ q[0])
        order = np.argsort(-sims)[: top_k * 5]
        cand_ids = [ids[i] for i in order]

    results: List[Dict] = []
    for _id in cand_ids:
        l = lessons.get(_id)
        if not l:
            continue
        if filters:
            ok = True
            for k, v in filters.items():
                if v and (l.get(k) or "") != v:
                    ok = False
                    break
            if not ok:
                continue
        results.append(l)
        if len(results) >= top_k:
            break
    return results
