import uuid
from typing import List, Optional, Tuple
from urllib.parse import urlparse
from pydriller import Repository

from src.data.database import save_lesson


def _normalize_github_url(url: str) -> Tuple[str, Optional[str]]:
    """If given a GitHub commits URL, return (repo_url, branch). Otherwise (url, None)."""
    try:
        parsed = urlparse(url)
        if parsed.netloc != 'github.com':
            return url, None
        parts = [p for p in parsed.path.split('/') if p]
        # Patterns: owner/repo, owner/repo/commits/<branch>
        if len(parts) >= 2 and (len(parts) == 2 or parts[2] != 'commits'):
            return f"https://github.com/{parts[0]}/{parts[1]}", None
        if len(parts) >= 4 and parts[2] == 'commits':
            repo_url = f"https://github.com/{parts[0]}/{parts[1]}"
            branch = parts[3]
            return repo_url, branch
        return url, None
    except Exception:
        return url, None


def mine_repo(repo_url: str, branch: Optional[str] = None, max_commits: int = 200,
              keywords: Optional[List[str]] = None):
    """
    Mine a repository for bug-fix style commits and store lessons.

    - Filters by commit message keywords if provided (e.g., ["fix", "bug", "error", "ssr"]).
    - Stores only simple single-file modifications with a text diff (before/after).
    """
    # Normalize GitHub commits URLs to repo + branch (e.g., .../commits/main)
    norm_repo_url, norm_branch = _normalize_github_url(repo_url)
    branch = branch or norm_branch

    count = 0
    for commit in Repository(norm_repo_url, only_in_branch=branch).traverse_commits():
        if max_commits and count >= max_commits:
            break

        msg_lower = (commit.msg or "").lower()
        if keywords:
            if not any(k in msg_lower for k in keywords):
                continue

        # Focus on small, single-file changes
        if len(commit.modified_files) != 1:
            continue
        mf = commit.modified_files[0]

        # Skip binary or very large changes
        if mf.added_lines is None or mf.deleted_lines is None:
            continue

        before = mf.source_code_before or ""
        after = mf.source_code or ""
        if not before or not after:
            continue

        lesson = {
            'id': str(uuid.uuid4()),
            'repo': repo_url,
            'file_path': mf.new_path or mf.old_path or '',
            'commit_sha': commit.hash,
            'commit_message': commit.msg or '',
            'before_code': before,
            'after_code': after,
            'tags': ','.join(keywords or [])
        }
        try:
            save_lesson(lesson)
            count += 1
        except Exception:
            # Ignore storage errors and continue
            pass

    return count


DEFAULT_DATASETS = [
    # Heavy commit repos
    'https://github.com/vercel/next.js',
    'https://github.com/pallets/flask',
    'https://github.com/tiangolo/fastapi',
    # Ultraviolet proxy tutorial repo (learn proxy-related fix patterns)
    'https://github.com/crllect/How-to-make-an-ultraviolet-proxy',
]


def mine_default_datasets(limit_per_repo: int = 100):
    total = 0
    for repo in DEFAULT_DATASETS:
        total += mine_repo(
            repo,
            max_commits=limit_per_repo,
            keywords=[
                "fix", "bug", "error", "ssr", "import", "hydration",
                "proxy", "rewrite", "csp", "cors"
            ],
        )
    return total
