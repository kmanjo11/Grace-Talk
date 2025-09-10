import os
import re
from pathlib import Path
from typing import Optional
import streamlit as st


DEFAULT_ROOT = Path('.')
SKIP_DIRS = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.mypy_cache', '.pytest_cache', '.ruff_cache'}
TEXT_EXTS = {
    '.py', '.js', '.jsx', '.ts', '.tsx', '.json', '.yml', '.yaml', '.toml', '.md', '.txt', '.css', '.scss', '.html', '.tsx', '.ini', '.cfg', '.sh'
}


def _is_text_file(path: Path) -> bool:
    if path.suffix.lower() in TEXT_EXTS:
        return True
    # Fallback: small files without NULs
    try:
        with open(path, 'rb') as f:
            chunk = f.read(2048)
            return b'\x00' not in chunk
    except Exception:
        return False


def _iter_files(root: Path, include_glob: Optional[str] = None):
    for dirpath, dirnames, filenames in os.walk(root):
        base = os.path.basename(dirpath)
        if base in SKIP_DIRS:
            dirnames[:] = []
            continue
        for fn in filenames:
            p = Path(dirpath) / fn
            if include_glob and not p.match(include_glob):
                # allow **/*.py style
                try:
                    if not Path(str(p)).match(include_glob):
                        continue
                except Exception:
                    continue
            if _is_text_file(p):
                yield p


def _search_file(path: Path, pattern: str, regex: bool, ignore_case: bool, max_matches: int = 50):
    flags = re.IGNORECASE if ignore_case else 0
    if not regex:
        # Escape pattern for literal search
        pat = re.escape(pattern)
    else:
        pat = pattern
    try:
        rx = re.compile(pat, flags)
    except re.error as e:
        return [(path, -1, f"[regex error] {e}")]

    results = []
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f, start=1):
                if rx.search(line):
                    results.append((path, i, line.rstrip('\n')))
                    if len(results) >= max_matches:
                        break
    except Exception as e:
        results.append((path, -1, f"[read error] {e}"))
    return results


def grep_panel():
    st.subheader("Code Search (grep)")
    st.caption("Search across this workspace. Supports regex, case options, and simple glob includes like **/*.py")

    q = st.text_input("Search for", value="")
    col1, col2, col3 = st.columns(3)
    with col1:
        regex = st.checkbox("Regex", value=False)
    with col2:
        ignore_case = st.checkbox("Ignore case", value=True)
    with col3:
        include_glob = st.text_input("Include (glob)", value="", placeholder="e.g., **/*.py")

    max_hits = st.slider("Max results", 10, 500, 200, step=10)
    run = st.button("Search", type="primary")

    if run and q.strip():
        root = DEFAULT_ROOT
        results_total = 0
        with st.spinner("Searching..."):
            for p in _iter_files(root, include_glob or None):
                hits = _search_file(p, q, regex, ignore_case, max_matches=max_hits)
                # Filter out files with no hits
                hits = [h for h in hits if h and h[1] != 0 and not (h[1] == -1 and h[2].startswith('[regex error]'))]
                if not hits:
                    continue
                with st.expander(f"{p} ({len(hits)} matches)"):
                    for _, ln, content in hits:
                        st.code(f"{ln:>5}: {content}", language="text")
                        results_total += 1
                        if results_total >= max_hits:
                            st.info("Result cap reached. Refine your query or increase Max results.")
                            return
