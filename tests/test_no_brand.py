"""Brand guard: no legacy brand string in tracked source (except sanctioned domain).

Project name is strictly "FII/DII Activity API". Ported from scripts/no-oriz.test.mjs.
The only permitted occurrence is the GitHub-Pages custom domain <repo>.oriz.in.
"""

import re
from pathlib import Path

_SKIP_DIRS = {"node_modules", ".git", "dist", ".wrangler", "__pycache__", ".pytest_cache", ".egg-info"}
_CHECK_EXT = re.compile(r"\.(md|py|mjs|js|json|yaml|yml|svg|css|html|txt|toml)$", re.I)

# These files must reference the banned word to test for it — skip them.
# AGENTS.md / CLAUDE.md are fleet meta-docs; they legitimately reference other sites.
_SELF = {"tests/test_no_brand.py", "tests/test_openapi.py", "AGENTS.md", "CLAUDE.md"}


def _walk(root: Path):
    for p in root.rglob("*"):
        if any(part in _SKIP_DIRS or part.endswith(".egg-info") for part in p.parts):
            continue
        if p.is_file() and _CHECK_EXT.search(p.name):
            yield p


def test_no_legacy_brand_string(root):
    needle = "or" + "iz"
    brand = re.compile(needle, re.I)
    # strip the sanctioned <repo>.oriz.in domain before scanning.
    domain = re.compile(r"[a-z0-9-]+\." + needle + r"\.in", re.I)
    offenders = []
    for f in _walk(root):
        rel = str(f.relative_to(root)).replace("\\", "/")
        if rel in _SELF:
            continue
        text = domain.sub("", f.read_text(encoding="utf-8", errors="ignore"))
        if brand.search(text):
            offenders.append(rel)
    assert offenders == [], f"legacy brand found in: {', '.join(offenders)}"
