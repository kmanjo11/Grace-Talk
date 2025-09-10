import os
import hashlib
from pathlib import Path
from typing import Optional, Tuple, List
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed


def parse_pdf_text(path: str, max_chars: int = 200_000, *, result_type: str = "markdown", ocr: bool = True, want_tables_json: bool = False) -> Tuple[str, str]:
    """Parse a PDF file using LlamaParse if available; fallback to a basic extractor.
    Returns (text, engine_used).
    - Set LLAMA_CLOUD_API_KEY env var to use LlamaParse.
    - result_type: "markdown" (default) or "text". If service errors, we fallback to text.
    - ocr: enable OCR for scanned PDFs when using LlamaParse.
    - want_tables_json: if True, try to request structured tables (best-effort; concatenated to markdown).
    """
    path = str(path)
    api_key = os.environ.get("LLAMA_CLOUD_API_KEY") or os.environ.get("LLAMA_PARSE_API_KEY")

    # Cache file path based on name + mtime
    p = Path(path)
    cache_dir = Path("./workspace/cache/pdf")
    cache_dir.mkdir(parents=True, exist_ok=True)
    sig_raw = f"{p.name}:{p.stat().st_mtime if p.exists() else 0}".encode("utf-8")
    sig = hashlib.sha256(sig_raw).hexdigest()[:24]
    cache_file = cache_dir / f"{sig}.txt"

    # Serve from cache if available
    try:
        if cache_file.exists():
            text = cache_file.read_text(encoding="utf-8")
            if text:
                return text[:max_chars], "cache"
    except Exception:
        pass

    # Try LlamaParse first if key present
    if api_key:
        try:
            from llama_parse import LlamaParse  # type: ignore
            # Prefer markdown; allow fallback to text on failure
            rt = result_type if result_type in ("markdown", "text") else "markdown"
            parser = LlamaParse(api_key=api_key, result_type=rt, ocr=ocr)

            # retry with exponential backoff on transient errors
            last_exc = None
            for attempt in range(4):
                try:
                    docs = parser.load_data(path)
                    break
                except Exception as e:
                    last_exc = e
                    # transient backoff
                    time.sleep(0.5 * (2 ** attempt) + random.uniform(0, 0.2))
            else:
                raise last_exc or RuntimeError("LlamaParse load failed")

            text_parts: List[str] = []
            text_parts.append("\n".join(getattr(d, "text", str(d)) for d in docs))

            # Optional: request tables as JSON if desired (best-effort)
            if want_tables_json:
                try:
                    parser_json = LlamaParse(api_key=api_key, result_type="json", ocr=ocr)
                    # small delay to avoid burst
                    time.sleep(0.1)
                    docs_json = parser_json.load_data(path)
                    text_parts.append("\n\n[TABLES as JSON]\n" + "\n".join(str(getattr(d, "json", getattr(d, "text", str(d)))) for d in docs_json))
                except Exception:
                    pass

            text = "\n".join(tp for tp in text_parts if tp)
            out = text[:max_chars]
            try:
                cache_file.write_text(out, encoding="utf-8")
            except Exception:
                pass
            return out, "llama-parse"
        except Exception:
            pass

    # Fallback: pypdf basic text extraction
    try:
        import pypdf  # type: ignore
        reader = pypdf.PdfReader(path)
        chunks = []
        for page in reader.pages:
            try:
                chunks.append(page.extract_text() or "")
            except Exception:
                continue
        text = "\n".join(chunks)
        out = text[:max_chars]
        try:
            cache_file.write_text(out, encoding="utf-8")
        except Exception:
            pass
        return out, "pypdf"
    except Exception:
        return "", "none"


def parse_pdfs_concurrently(paths: List[str], *, max_chars_per_doc: int = 200_000) -> List[Tuple[str, str, str]]:
    """Parse multiple PDFs concurrently.
    Returns a list of tuples: (path, text, engine).
    """
    results: List[Tuple[str, str, str]] = []
    with ThreadPoolExecutor(max_workers=min(4, max(1, len(paths)))) as ex:
        futures = {ex.submit(parse_pdf_text, p, max_chars_per_doc): p for p in paths}
        for fut in as_completed(futures):
            p = futures[fut]
            try:
                text, engine = fut.result()
            except Exception:
                text, engine = "", "none"
            results.append((p, text, engine))
    return results
