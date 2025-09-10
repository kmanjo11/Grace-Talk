import json
import os
import re
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

from src.utils.pdf_parser import parse_pdf_text

INDEX_DIR = Path("./workspace/cache/pdf_index")
INDEX_DIR.mkdir(parents=True, exist_ok=True)
FAISS_PATH = INDEX_DIR / "pdf_sections.faiss"
IDS_PATH = INDEX_DIR / "pdf_sections_ids.json"
SECTIONS_PATH = INDEX_DIR / "pdf_sections.json"
SIG_PATH = INDEX_DIR / "pdf_index.sig"
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


def _make_signature(paths: List[str]) -> str:
    stats = []
    for p in sorted(paths):
        try:
            st = os.stat(p)
            stats.append(f"{p}:{int(st.st_mtime)}:{st.st_size}")
        except Exception:
            stats.append(f"{p}:0:0")
    raw = "|".join(stats).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:32]


def _split_markdown_sections(md: str) -> List[Tuple[str, str]]:
    """Split markdown text into (title, body) sections using heading markers.
    Includes a 'Document' section if no headings found.
    """
    lines = md.splitlines()
    sections: List[Tuple[str, str]] = []
    current_title = ""
    current_body: List[str] = []
    for line in lines:
        if re.match(r"^#{1,6}\s+", line):
            if current_body:
                sections.append((current_title or "Untitled", "\n".join(current_body).strip()))
                current_body = []
            current_title = re.sub(r"^#{1,6}\s+", "", line).strip()
        else:
            current_body.append(line)
    if current_body:
        sections.append((current_title or "Untitled", "\n".join(current_body).strip()))
    if not sections:
        sections = [("Document", md)]
    return sections


def build_pdf_index(pdf_paths: List[str], *, max_chars_per_doc: int = 150_000) -> int:
    """Build a FAISS index of sections from the given PDFs.
    Returns number of sections indexed.
    """
    pdf_paths = [str(p) for p in pdf_paths if str(p).lower().endswith('.pdf')]
    if not pdf_paths:
        # Clear existing
        for f in [FAISS_PATH, IDS_PATH, SECTIONS_PATH, SIG_PATH]:
            try:
                if f.exists():
                    f.unlink()
            except Exception:
                pass
        return 0

    signature = _make_signature(pdf_paths)
    try:
        if SIG_PATH.exists() and SIG_PATH.read_text() == signature and FAISS_PATH.exists() and IDS_PATH.exists() and SECTIONS_PATH.exists():
            # already current
            with open(SECTIONS_PATH, 'r', encoding='utf-8') as f:
                sections = json.load(f)
            return len(sections)
    except Exception:
        pass

    # Parse PDFs and split into sections
    all_sections: List[Dict] = []
    for p in pdf_paths:
        text, engine = parse_pdf_text(p, max_chars=max_chars_per_doc, result_type="markdown", ocr=True)
        if not text:
            continue
        for i, (title, body) in enumerate(_split_markdown_sections(text)):
            if not body.strip():
                continue
            snippet = "\n".join(body.splitlines()[:80])
            all_sections.append({
                "id": f"{p}::sec{i}",
                "path": p,
                "title": title,
                "body": snippet,
            })

    # Build embeddings
    ids = [s["id"] for s in all_sections]
    texts = [f"{s['title']}\n{s['body']}" for s in all_sections]
    if not texts:
        # Clear
        for f in [FAISS_PATH, IDS_PATH, SECTIONS_PATH, SIG_PATH]:
            try:
                if f.exists():
                    f.unlink()
            except Exception:
                pass
        return 0

    model = _load_embedder()
    embs = model.encode(texts, batch_size=64, show_progress_bar=False, normalize_embeddings=True)
    embs = np.asarray(embs, dtype=np.float32)

    faiss = _try_import_faiss()
    if faiss is not None:
        index = faiss.IndexFlatIP(embs.shape[1])
        index.add(embs)
        faiss.write_index(index, str(FAISS_PATH))
    else:
        np.save(str(FAISS_PATH).replace('.faiss', '.npy'), embs)

    with open(IDS_PATH, 'w', encoding='utf-8') as f:
        json.dump(ids, f)
    with open(SECTIONS_PATH, 'w', encoding='utf-8') as f:
        json.dump(all_sections, f)
    SIG_PATH.write_text(signature, encoding='utf-8')
    return len(all_sections)


def ensure_pdf_index_built(pdf_paths: List[str]) -> int:
    try:
        return build_pdf_index(pdf_paths)
    except Exception:
        return 0


def retrieve_pdf_sections(query: str, top_k: int = 3) -> List[Dict]:
    """Retrieve top-k relevant PDF sections for the query.
    Returns list of dicts with keys: id, path, title, body
    """
    # Load artifacts
    try:
        with open(IDS_PATH, 'r', encoding='utf-8') as f:
            ids = json.load(f)
        with open(SECTIONS_PATH, 'r', encoding='utf-8') as f:
            sections = json.load(f)
    except Exception:
        return []

    if not ids or not sections:
        return []

    faiss = _try_import_faiss()
    if faiss is not None and FAISS_PATH.exists():
        index = faiss.read_index(str(FAISS_PATH))
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(MODEL_NAME)
        q = model.encode([query], normalize_embeddings=True)
        q = np.asarray(q, dtype=np.float32)
        D, I = index.search(q, k=min(top_k * 3, len(ids)))
        cand_ids = [ids[i] for i in I[0] if i < len(ids)]
    else:
        # Fallback: load numpy array if present
        npy_path = str(FAISS_PATH).replace('.faiss', '.npy')
        if not os.path.exists(npy_path):
            return []
        embs = np.load(npy_path)
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(MODEL_NAME)
        q = model.encode([query], normalize_embeddings=True)
        q = np.asarray(q, dtype=np.float32)
        sims = (embs @ q[0])
        order = np.argsort(-sims)[: top_k * 3]
        cand_ids = [ids[i] for i in order]

    # Map ids to section dicts
    lookup = {s['id']: s for s in sections}
    results = []
    for cid in cand_ids:
        s = lookup.get(cid)
        if s:
            results.append(s)
        if len(results) >= top_k:
            break
    return results
