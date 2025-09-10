import json
import os
import re
import hashlib
from pathlib import Path
from typing import Dict, List

import numpy as np

INDEX_DIR = Path("./workspace/cache/kb_index")
INDEX_DIR.mkdir(parents=True, exist_ok=True)
FAISS_PATH = INDEX_DIR / "kb_sections.faiss"
IDS_PATH = INDEX_DIR / "kb_sections_ids.json"
SECTIONS_PATH = INDEX_DIR / "kb_sections.json"
SIG_PATH = INDEX_DIR / "kb_index.sig"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

TEXT_EXTS = {".md", ".markdown", ".txt"}


def _load_embedder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODEL_NAME)


def _try_import_faiss():
    try:
        import faiss  # type: ignore
        return faiss
    except Exception:
        return None


def _discover_kb_files(extra_paths: List[str] | None = None) -> List[str]:
    # Search the repo root and ./knowledge for md/txt, plus any explicit extra paths
    root = Path('.')
    knowledge_dir = Path('./knowledge')
    files: List[str] = []
    for base in [root, knowledge_dir]:
        if not base.exists():
            continue
        for p in base.rglob('*'):
            if p.is_file() and p.suffix.lower() in TEXT_EXTS:
                # skip caches and heavy dirs
                parts = set(p.parts)
                if any(x in parts for x in ['.git', 'node_modules', '.venv', 'venv', '__pycache__', 'workspace', '.mypy_cache', '.pytest_cache', '.ruff_cache']):
                    continue
                files.append(str(p))
    if extra_paths:
        for ep in extra_paths:
            try:
                q = Path(ep)
                if q.exists() and q.is_file() and q.suffix.lower() in TEXT_EXTS:
                    files.append(str(q))
            except Exception:
                pass
    # De-duplicate
    uniq = sorted(set(files))
    return uniq


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


def _split_markdown_sections(text: str) -> List[dict]:
    # If markdown-like, split by headings; otherwise, chunk by ~200 lines
    lines = text.splitlines()
    sections: List[dict] = []
    current_title = ""
    current_body: List[str] = []
    found_heading = False

    for line in lines:
        if re.match(r"^#{1,6}\s+", line):
            found_heading = True
            if current_body:
                sections.append({"title": current_title or "Untitled", "body": "\n".join(current_body).strip()})
                current_body = []
            current_title = re.sub(r"^#{1,6}\s+", "", line).strip()
        else:
            current_body.append(line)
    if current_body:
        sections.append({"title": current_title or "Untitled", "body": "\n".join(current_body).strip()})

    if not found_heading:
        # Fallback chunking if no headings
        chunk: List[str] = []
        chunk_lines = 200
        sections = []
        for i, ln in enumerate(lines, start=1):
            chunk.append(ln)
            if len(chunk) >= chunk_lines:
                sections.append({"title": f"Chunk {len(sections)+1}", "body": "\n".join(chunk).strip()})
                chunk = []
        if chunk:
            sections.append({"title": f"Chunk {len(sections)+1}", "body": "\n".join(chunk).strip()})

    return sections


def build_kb_index(extra_paths: List[str] | None = None) -> int:
    """Build a FAISS index from Markdown/Text knowledge files.
    Returns number of sections indexed.
    """
    kb_files = _discover_kb_files(extra_paths)
    if not kb_files:
        # Clear existing index
        for f in [FAISS_PATH, IDS_PATH, SECTIONS_PATH, SIG_PATH]:
            try:
                if f.exists():
                    f.unlink()
            except Exception:
                pass
        return 0

    signature = _make_signature(kb_files)
    try:
        if SIG_PATH.exists() and SIG_PATH.read_text() == signature and FAISS_PATH.exists() and IDS_PATH.exists() and SECTIONS_PATH.exists():
            with open(SECTIONS_PATH, 'r', encoding='utf-8') as f:
                ex = json.load(f)
            return len(ex)
    except Exception:
        pass

    all_sections: List[dict] = []
    for fp in kb_files:
        try:
            text = Path(fp).read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        secs = _split_markdown_sections(text)
        for i, s in enumerate(secs):
            body = s.get('body', '').strip()
            if not body:
                continue
            snippet = "\n".join(body.splitlines()[:120])
            all_sections.append({
                "id": f"{fp}::sec{i}",
                "path": fp,
                "title": s.get('title') or 'Section',
                "body": snippet,
            })

    ids = [s['id'] for s in all_sections]
    texts = [f"{s['title']}\n{s['body']}" for s in all_sections]
    if not texts:
        for f in [FAISS_PATH, IDS_PATH, SECTIONS_PATH, SIG_PATH]:
            try:
                if f.exists():
                    f.unlink()
            except Exception:
                pass
        return 0

    from sentence_transformers import SentenceTransformer
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


def ensure_kb_index_built(extra_paths: List[str] | None = None) -> int:
    try:
        return build_kb_index(extra_paths)
    except Exception:
        return 0


def retrieve_kb_sections(query: str, top_k: int = 3) -> List[Dict]:
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
        model = _load_embedder()
        q = model.encode([query], normalize_embeddings=True)
        q = np.asarray(q, dtype=np.float32)
        D, I = index.search(q, k=min(top_k * 3, len(ids)))
        cand_ids = [ids[i] for i in I[0] if i < len(ids)]
    else:
        npy_path = str(FAISS_PATH).replace('.faiss', '.npy')
        if not os.path.exists(npy_path):
            return []
        embs = np.load(npy_path)
        model = _load_embedder()
        q = model.encode([query], normalize_embeddings=True)
        q = np.asarray(q, dtype=np.float32)
        sims = (embs @ q[0])
        order = np.argsort(-sims)[: top_k * 3]
        cand_ids = [ids[i] for i in order]

    lookup = {s['id']: s for s in sections}
    results: List[Dict] = []
    for cid in cand_ids:
        s = lookup.get(cid)
        if s:
            results.append(s)
        if len(results) >= top_k:
            break
    return results
