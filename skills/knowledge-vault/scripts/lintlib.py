#!/usr/bin/env python3
"""Knowledge Vault unified lint primitives.

Shared deterministic-check helpers for check_undigested.py, audit.py, self-check.
One implementation, three call sites -- avoids rule drift (per usage-log
2026-07-07/07-10: self-check vs audit mismatch, Windows backslash-path Grep misses).

Constraints (per .claude/rules/skill-compatibility.md):
- cross-platform: pathlib, no Unix-only commands
- read-only: lint funcs never mutate files (Agent decides fixes, human-in-the-loop)
- Windows CJK: caller reconfigures stdout (see each script's main())
"""
import re
from collections import Counter
from pathlib import Path


# CJK quote/punct cleanup table for filename normalization.
# Keys use \uXXXX escapes (pure ASCII) to avoid ambiguity: fullwidth quote chars
# can be normalized to ASCII during file write, and three ASCII quotes would form
# a triple-quoted string and break parsing. Shared by check_undigested dedup and
# audit naming.
CHAR_NORMALIZE_TABLE = str.maketrans(
    {
        "“": "",   # left double quote
        "”": "",   # right double quote
        "‘": "",   # left single quote
        "’": "",   # right single quote
        "、": "",   # ideographic comma
        "（": "(",  # fullwidth left paren
        "）": ")",  # fullwidth right paren
        "：": "",   # fullwidth colon
        "《": "",   # left double angle bracket
        "》": "",   # right double angle bracket
        "—": "",   # em dash
        "…": "",   # horizontal ellipsis
        "【": "",   # left black lenticular bracket
        "】": "",   # right black lenticular bracket
        "？": "",   # fullwidth question mark
        "，": "",   # fullwidth comma
        "！": "",   # fullwidth exclamation mark
    }
)

# Unsafe filename chars (audit-rules.md section 5, Naming Compliance)
UNSAFE_FILENAME_CHARS = set('\\/:*?"<>|#%^&$!`\'=~')


def normalize_filename(name: str) -> str:
    """Normalize filename for comparison: strip CJK/special chars, lowercase."""
    name = name.translate(CHAR_NORMALIZE_TABLE)
    name = re.sub(r'[\\/:*?"<>|#%^&$!`\'=~\s]', "", name)
    return name.lower().strip()


def has_unsafe_filename_chars(name: str) -> set:
    """Return the set of unsafe chars appearing in name (incl. extension). Empty = compliant."""
    return set(name) & UNSAFE_FILENAME_CHARS


# wikilink extraction & validation
# matches [[target]] or [[target|alias]], captures target (without alias)
WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")


def extract_wikilinks(text: str) -> list[str]:
    """Extract all [[target|alias]] / [[target]] targets from Markdown (alias stripped)."""
    return [m.group(1).strip() for m in WIKILINK_RE.finditer(text)]


def validate_wikilink_slug(target: str) -> tuple[bool, str | None]:
    """Validate wikilink slug format. Returns (ok, reason).

    Only checks format (pure slug: no .md suffix, no path-sensitive chars / \\ :).
    Does NOT check whether the target file exists -- use check_link_target_exists.
    A bare concept name (missing -concept suffix) is not flagged here; it surfaces
    indirectly via a non-existent target.
    """
    if not target:
        return False, "empty slug"
    if ".md" in target:
        return False, f"contains .md suffix (wikilink must be pure slug, unlike frontmatter source path): [[{target}]]"
    # \\ : * ? " < > | are illegal in filenames (Windows + Obsidian) and break linking.
    # NOTE: / is a LEGAL Obsidian path separator (e.g. [[summaries/xxx]]), so it is NOT
    # flagged here. A concept name containing / that doesn't resolve to a file is caught
    # by check_link_target_exists (target missing) -- per usage-log 2026-07-10.
    bad = set(target) & set('\\:*?"<>|')
    if bad:
        return False, f"contains illegal filename char(s) {''.join(sorted(bad))} (breaks linking; use compact name or alias): [[{target}]]"
    return True, None


def build_file_index(vault_root: Path, subdir: str = "knowledge") -> dict[str, Path]:
    """Walk vault_root/<subdir>/*.md and build {file_stem: path} index.

    Reused by check_link_target_exists / orphan detection so each wikilink does
    not trigger a full vault scan. file_stem is the wikilink target (Obsidian
    addresses by stem).
    """
    index: dict[str, Path] = {}
    base = vault_root / subdir
    if not base.exists():
        return index
    for f in base.rglob("*.md"):
        index[f.stem] = f
    return index


def check_link_target_exists(
    target: str, file_index: dict[str, Path]
) -> tuple[bool, Path | None]:
    """Check whether wikilink target maps to an actual file in file_index. Returns (exists, path).

    target may be a pure slug ([[xxx-概念]]) or carry a path prefix ([[summaries/xxx]]).
    We look up by the final path segment (Obsidian addresses files by stem), so both
    forms resolve. A concept name with an embedded / (e.g. [[What/Why/How-概念]] whose
    file is actually "WhatWhyHow-概念.md") won't match and is correctly flagged missing.
    """
    stem = target.rsplit("/", 1)[-1] if "/" in target else target
    p = file_index.get(stem)
    return (p is not None, p)


def detect_duplicate_sections(md_path: Path) -> dict[str, int]:
    """Detect same-named ## sections appearing >= 2 times in one .md. Returns {title: count}.

    Fixes usage-log 2026-07-07: concept cards with duplicate "related concepts"
    sections (15 systematic). Root cause: digestion merge didn't detect same-name
    sections, neither did self-check.
    """
    try:
        text = md_path.read_text(encoding="utf-8")
    except Exception:
        return {}
    headers = re.findall(r"^##\s+(.+?)\s*$", text, re.M)
    counts = Counter(h.strip() for h in headers)
    return {h: c for h, c in counts.items() if c > 1}
