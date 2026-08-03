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

    Only checks format. Flags a TRAILING .md on a pure slug (e.g. `[[xxx-概念.md]]`)
    but NOT .md inside a name (`AGENTS.md-概念`) or a path wikilink (`raw/foo.md`) --
    those are valid. Also flags path-sensitive chars / \\ :. Does NOT check whether
    the target file exists -- use check_link_target_exists. A bare concept name
    (missing -concept suffix) surfaces indirectly via a non-existent target.

    v1.9.3: previously any `.md` anywhere was flagged, wrongly rejecting concept
    names that legitimately contain .md (AGENTS.md, SOUL.md) -- per Ajknowledge
    audit-real-issues-2026-07-24.
    """
    if not target:
        return False, "empty slug"
    if target.endswith(".md") and "/" not in target:
        return False, f"trailing .md suffix on a pure slug (a name like 'AGENTS.md-概念' or a path like 'raw/foo.md' is fine): [[{target}]]"
    # \\ : * ? " < > | are illegal in filenames (Windows + Obsidian) and break linking.
    # NOTE: / is a LEGAL Obsidian path separator (e.g. [[summaries/xxx]]), so it is NOT
    # flagged here. A concept name containing / that doesn't resolve to a file is caught
    # by check_link_target_exists (target missing) -- per usage-log 2026-07-10.
    bad = set(target) & set('\\:*?"<>|')
    if bad:
        return False, f"contains illegal filename char(s) {''.join(sorted(bad))} (breaks linking; use compact name or alias): [[{target}]]"
    return True, None


def build_file_index(vault_root: Path, subdir: str | None = None) -> dict[str, Path]:
    """Walk the vault and build {name-or-stem: path} index for link target lookup.

    Indexes BOTH f.name (with extension) and f.stem so wikilinks resolve whether
    they carry an extension/path (`[[raw/images/xxx.jpg]]`, `[[raw/foo.md]]`) or
    are a pure slug (`[[xxx-概念]]` -- Obsidian addresses files by stem).

    v1.9.3: previously walked only vault_root/knowledge/*.md, missing every link
    into raw/ (source files, images) and causing mass false "broken link" reports
    (per Ajknowledge audit-real-issues-2026-07-24: ~219 false positives). subdir
    is kept optional for callers that still scope to a subdirectory.
    """
    index: dict[str, Path] = {}
    base = vault_root if subdir is None else vault_root / subdir
    if not base.exists():
        return index
    for f in base.rglob("*"):
        if f.is_file():
            index[f.name] = f
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


def strip_frontmatter(text: str) -> str:
    """Strip YAML frontmatter. Image/wikilink scans should ignore frontmatter fields
    like `source: [[raw/.../x.md]]` and `related_summaries:` -- those are file-path
    links, not content references, and would be false positives.

    Shared by audit (link_validity) and count_images (image scan). Extracted from
    audit._body_only in v1.10.0 to avoid duplication (one implementation, per the
    lintlib DRY philosophy).
    """
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:]
    return text


def strip_fenced_code(text: str) -> str:
    """Strip fenced code block content (``` / ~~~) so lint scans ignore markdown
    shown inside code blocks.

    Knowledge concept cards often display template/example markdown inside fenced
    blocks (e.g. a sample AGENTS.md with its own `## 开发命令` heading, or a
    `[[xxx-概念]]` wikilink example). Those are illustrative — not real document
    structure or links — and must be excluded from duplicate-section / wikilink
    scans. Fixes AGENTS.md-概念.md false positive (v1.9.2): its 3x `## 开发命令`
    and 3x `## 代码风格` all live inside ```markdown example blocks.
    """
    out = []
    in_fence = False
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append(line)
    return "".join(out)


def detect_duplicate_sections(md_path: Path) -> dict[str, int]:
    """Detect same-named ## sections appearing >= 2 times in one .md. Returns {title: count}.

    Fixes usage-log 2026-07-07: concept cards with duplicate "related concepts"
    sections (15 systematic). Root cause: digestion merge didn't detect same-name
    sections, neither did self-check.

    Code blocks are stripped first (strip_fenced_code) so `##` headings shown as
    examples inside ``` blocks are not counted (v1.9.2: AGENTS.md-概念.md fix).
    """
    try:
        text = md_path.read_text(encoding="utf-8")
    except Exception:
        return {}
    text = strip_fenced_code(text)
    headers = re.findall(r"^##\s+(.+?)\s*$", text, re.M)
    counts = Counter(h.strip() for h in headers)
    return {h: c for h, c in counts.items() if c > 1}


def compute_inbound_counts(vault_root: Path) -> dict[str, int]:
    """Count inbound wikilinks for each concept/topic stem across knowledge/.

    Returns {stem: inbound_count} — how many other pages reference each stem
    (self-references excluded, frontmatter excluded). Shared by check_orphan
    (audit #9) and build_manifest (concept/topic inbound for Analysis).

    Extracted from audit.check_orphan in v1.12.0 (DRY: one implementation).
    """
    knowledge = vault_root / "knowledge"
    inbound: dict[str, set[str]] = {}
    if not knowledge.exists():
        return {}
    for f in knowledge.rglob("*.md"):
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            continue
        self_stem = f.stem
        for target in extract_wikilinks(strip_frontmatter(text)):
            if target == self_stem:
                continue  # 排除自引用
            inbound.setdefault(target, set()).add(self_stem)
    return {stem: len(refs) for stem, refs in inbound.items()}


def detect_definition_overlap(concepts_dir: Path, threshold: float = 0.5) -> list[dict]:
    """检测概念卡定义重叠（bigram Jaccard ≥ threshold）。返回候选对 [{a,b,def_a,def_b,score}]。

    语义判断仍由 Agent（audit-rules 第 3 项一致性）。本函数输出候选对供复核。
    bigram（2-gram）无需分词，适合中文。v1.12.0 新增。
    """
    defs: list[tuple[str, str]] = []  # (name, def)
    if not concepts_dir.exists():
        return []
    for f in sorted(concepts_dir.glob("*.md")):
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            continue
        text = strip_fenced_code(text)
        m = re.search(r"^## 一句话定义\s*\n(.+?)(?=\n## |\Z)", text, re.M | re.S)
        if not m:
            continue
        defn = m.group(1).strip().split("\n")[0].strip()
        if defn:
            defs.append((f.stem.removesuffix("-概念"), defn))

    def bigrams(s: str) -> set:
        s = re.sub(r"\s+", "", s)
        return {s[i:i + 2] for i in range(len(s) - 1)} if len(s) > 1 else {s}

    pairs = []
    for i in range(len(defs)):
        bi_i = bigrams(defs[i][1])
        if not bi_i:
            continue
        for j in range(i + 1, len(defs)):
            bi_j = bigrams(defs[j][1])
            if not bi_j:
                continue
            score = len(bi_i & bi_j) / len(bi_i | bi_j)
            if score >= threshold:
                pairs.append({"a": defs[i][0], "b": defs[j][0],
                              "def_a": defs[i][1], "def_b": defs[j][1],
                              "score": round(score, 2)})
    pairs.sort(key=lambda x: x["score"], reverse=True)
    return pairs
