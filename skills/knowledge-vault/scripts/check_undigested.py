#!/usr/bin/env python3
"""
Knowledge Vault 未消化文件检测脚本

扫描 raw/ 和 knowledge/summaries/，通过三层递进匹配 + SHA256 内容哈希识别真正未消化的文件。
输出分 5 类：NEW（新内容）、UPDATED（内容已变更）、DUPE（双格式已覆盖）、SKIP（不可消化）、MANUAL（需人工确认）。

用法:
  python check_undigested.py --vault /path/to/vault
  python check_undigested.py --vault /path/to/vault --json
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from lintlib import normalize_filename


# ── 不应消化的元数据文件名关键词 ──
SKIP_KEYWORDS = ["manifest", "metadata", "index", ".git", "__pycache__"]

# ── 来源标识映射（预处理格式 ↔ raw 转写格式共用同一来源标识） ──
# 键为文件名中能识别的来源标记，值为统一来源 ID
SOURCE_PATTERNS = [
    (re.compile(r"科技前哨|keji[_-]?qianshao", re.I), "keji-qianshao"),
]

# ── 日期提取正则 ──
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")

# 文件名规范化（normalize_filename）已抽取到 lintlib.py，
# 供 check_undigested / audit / self-check 共用，避免规则不一致。


# ── SHA256 哈希缓存 ──
HASH_CACHE_DIR = ".llm-wiki-cache"
HASH_CACHE_FILE = "hashes.json"


def compute_file_hash(filepath: Path) -> str:
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def load_hash_cache(vault_root: Path) -> dict[str, str]:
    """Load cached hashes from .llm-wiki-cache/hashes.json. Returns {relative_path: sha256}."""
    cache_path = vault_root / HASH_CACHE_DIR / HASH_CACHE_FILE
    if not cache_path.exists():
        return {}
    try:
        text = cache_path.read_text(encoding="utf-8")
        return json.loads(text)
    except (json.JSONDecodeError, OSError):
        return {}


def save_hash_cache(vault_root: Path, hashes: dict[str, str]) -> None:
    """Save hash cache to .llm-wiki-cache/hashes.json."""
    cache_dir = vault_root / HASH_CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / HASH_CACHE_FILE
    cache_path.write_text(
        json.dumps(hashes, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def is_skippable(filename: str) -> bool:
    """Check if file should be marked as SKIP (metadata, manifest, etc.)."""
    stem = Path(filename).stem.lower()
    return any(kw in stem for kw in SKIP_KEYWORDS)


def extract_source_id(filename: str) -> str | None:
    """Extract a normalized source identifier from filename."""
    for pattern, source_id in SOURCE_PATTERNS:
        if pattern.search(filename):
            return source_id
    return None


def extract_date(filename: str) -> str | None:
    """Extract first YYYY-MM-DD date from filename."""
    m = DATE_RE.search(filename)
    return m.group(1) if m else None


def extract_date_from_path(filepath: Path) -> str | None:
    """Extract YYYY-MM-DD date from a parent directory name.

    the vault 的 raw 按日期目录组织（raw/2026-06-28/xxx.md），文件名本身常无日期。
    此函数向上遍历父目录，从首个形如 YYYY-MM-DD 的目录名提取日期作为 fallback。
    """
    for parent in filepath.parents:
        m = DATE_RE.search(parent.name)
        if m:
            return m.group(1)
    return None


def read_summary_sources(summaries_dir: Path) -> dict[str, str]:
    """Read source field from all summary files. Returns {normalized_source_name: source_path}."""
    sources = {}
    if not summaries_dir.exists():
        return sources

    for f in summaries_dir.glob("*.md"):
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            continue

        # Extract source from frontmatter
        m = re.search(r"^source:\s*\[?\[?(.*?)\]?\]?\s*$", text, re.M)
        if m:
            raw_source = m.group(1).strip()
            # Extract filename part from path-like source
            source_name = Path(raw_source).stem if "/" in raw_source or "\\" in raw_source else raw_source
            # Remove .md extension if present
            source_name = re.sub(r"\.md$", "", source_name)
            norm = normalize_filename(source_name)
            if norm:
                sources[norm] = raw_source

    return sources


def read_summary_source_details(summaries_dir: Path) -> list[dict]:
    """Read detailed source info from summaries for cross-matching.
    Returns list of {source_path, source_date, source_id, normalized_name}.
    """
    details = []
    if not summaries_dir.exists():
        return details

    for f in summaries_dir.glob("*.md"):
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            continue

        m = re.search(r"^source:\s*\[?\[?(.*?)\]?\]?\s*$", text, re.M)
        if not m:
            continue

        raw_source = m.group(1).strip()
        source_name = Path(raw_source).stem if "/" in raw_source or "\\" in raw_source else raw_source
        source_name = re.sub(r"\.md$", "", source_name)

        details.append({
            "source_path": raw_source,
            "source_name": source_name,
            "normalized": normalize_filename(source_name),
            "source_date": extract_date(source_name),
            "source_id": extract_source_id(source_name),
        })

    return details


def collect_raw_files(raw_dir: Path) -> list[Path]:
    """Collect all .md files in raw/ excluding raw/images/ and audio cache."""
    files = []
    for f in sorted(raw_dir.rglob("*.md")):
        # Skip images directory
        if "images" in f.parts:
            continue
        # Skip audio cache
        if ".audio_cache" in f.parts:
            continue
        files.append(f)
    return files


def check_undigested(vault_root: Path) -> dict:
    """Main dedup logic with SHA256 hash change detection. Returns categorized results."""

    raw_dir = vault_root / "raw"
    summaries_dir = vault_root / "knowledge" / "summaries"

    raw_files = collect_raw_files(raw_dir)
    summary_sources = read_summary_sources(summaries_dir)
    summary_details = read_summary_source_details(summaries_dir)

    # Load hash cache
    hash_cache = load_hash_cache(vault_root)
    current_hashes: dict[str, str] = {}

    # Build date+source index from summaries for cross-matching
    digested_date_source = set()
    for d in summary_details:
        if d["source_date"] and d["source_id"]:
            digested_date_source.add((d["source_date"], d["source_id"]))

    results = {
        "new": [],       # Truly undigested
        "updated": [],   # Previously digested but content changed
        "dupe": [],      # Already covered by another format
        "skip": [],      # Metadata / non-content files
        "manual": [],    # Needs human confirmation
    }

    for raw_file in raw_files:
        rel_path = str(raw_file.relative_to(vault_root))
        stem = raw_file.stem

        # Compute current hash
        current_hash = compute_file_hash(raw_file)
        current_hashes[rel_path] = current_hash

        # Check SKIP first
        if is_skippable(stem):
            results["skip"].append({
                "file": rel_path,
                "name": stem,
                "reason": "元数据/索引文件，不属于知识内容",
            })
            continue

        norm_stem = normalize_filename(stem)

        # Layer 1: Exact match against summary sources
        if norm_stem in summary_sources:
            # Previously digested — check if content changed
            cached_hash = hash_cache.get(rel_path)
            if cached_hash and cached_hash != current_hash:
                results["updated"].append({
                    "file": rel_path,
                    "name": stem,
                    "reason": "文件内容已变更，重新消化会覆盖已有摘要",
                })
            # If hash matches or no cache: unchanged, skip silently
            continue

        # Layer 2: Date + source cross-match (for multi-format content)
        raw_date = extract_date(stem)
        raw_source_id = extract_source_id(stem)
        if raw_date and raw_source_id and (raw_date, raw_source_id) in digested_date_source:
            results["dupe"].append({
                "file": rel_path,
                "name": stem,
                "reason": f"同日期 {raw_date} 的 {raw_source_id} 内容已有摘要",
            })
            continue

        # Layer 3: Fuzzy match — compare first N chars
        fuzzy_matched = False
        matched_source = None
        for norm_source, raw_src in summary_sources.items():
            # Try prefix match (min 10 chars to avoid false positives)
            min_len = min(len(norm_stem), len(norm_source))
            if min_len >= 10:
                prefix_len = min(20, min_len)
                if norm_stem[:prefix_len] == norm_source[:prefix_len]:
                    fuzzy_matched = True
                    matched_source = raw_src
                    break

        if fuzzy_matched:
            results["dupe"].append({
                "file": rel_path,
                "name": stem,
                "reason": f"模糊匹配到已有摘要来源: {matched_source}",
            })
            continue

        # Also check if any summary source fuzzy-matches this raw file
        # (handles the reverse direction)
        reverse_matched = False
        for d in summary_details:
            ns = d["normalized"]
            min_len = min(len(norm_stem), len(ns))
            if min_len >= 10:
                prefix_len = min(20, min_len)
                if norm_stem[:prefix_len] == ns[:prefix_len]:
                    reverse_matched = True
                    break

        if reverse_matched:
            results["dupe"].append({
                "file": rel_path,
                "name": stem,
                "reason": "与已有摘要来源模糊匹配",
            })
            continue

        # 未匹配任何已有 summary = 真正的新增内容。
        # 注意：不能因"文件名无日期"就判 MANUAL —— the vault 的 raw 按日期目录
        # 组织（raw/YYYY-MM-DD/xxx.md），文件名本身常无日期，但只要未匹配任何
        # summary 就是新内容。（修复日志 2026-06-28/07-06/07-10 三次复现的误判：
        # 真正根因是"无日期→MANUAL"分类逻辑，而非全角标点。）
        # 日期：优先文件名，fallback 父目录名（raw/YYYY-MM-DD/）。
        raw_date = raw_date or extract_date_from_path(raw_file)

        results["new"].append({
            "file": rel_path,
            "name": stem,
            "date": raw_date,
            "source_id": raw_source_id,
        })

    # Save updated hash cache
    save_hash_cache(vault_root, current_hashes)

    return results


def print_report(results: dict, vault_root: Path):
    """Print human-readable report."""
    new = results["new"]
    updated = results["updated"]
    dupe = results["dupe"]
    skip = results["skip"]
    manual = results["manual"]

    total = len(new) + len(updated) + len(dupe) + len(skip) + len(manual)
    raw_count = len(list((vault_root / "raw").rglob("*.md")))
    # Exclude images and cache
    raw_count = len(collect_raw_files(vault_root / "raw"))
    summary_count = len(list((vault_root / "knowledge" / "summaries").glob("*.md")))

    print("=" * 60)
    print("知识库消化状态检测报告")
    print("=" * 60)
    print(f"Vault: {vault_root}")
    print(f"Raw 文件数: {raw_count}")
    print(f"摘要数: {summary_count}")
    print(f"本次检测文件数: {total}")
    print()

    if updated:
        print(f"── UPDATED（内容已变更）: {len(updated)} 篇 ──")
        for item in updated:
            print(f"  {item['file']}")
            print(f"    原因: {item['reason']}")
        print()

    if skip:
        print(f"── SKIP（不可消化）: {len(skip)} 篇 ──")
        for item in skip:
            print(f"  {item['file']}")
            print(f"    原因: {item['reason']}")
        print()

    if dupe:
        print(f"── DUPE（双格式已覆盖）: {len(dupe)} 篇 ──")
        for item in dupe:
            print(f"  {item['file']}")
            print(f"    原因: {item['reason']}")
        print()

    if manual:
        print(f"── MANUAL（需人工确认）: {len(manual)} 篇 ──")
        for item in manual:
            print(f"  {item['file']}")
            print(f"    原因: {item['reason']}")
        print()

    print(f"── NEW（真正未消化）: {len(new)} 篇 ──")
    if new:
        for item in new:
            date_str = f" ({item['date']})" if item.get("date") else ""
            print(f"  - {item['file']}{date_str}")
    else:
        print("  （无）")

    print()
    print("=" * 60)
    parts = []
    if new:
        parts.append(f"{len(new)} 篇新内容")
    if updated:
        parts.append(f"{len(updated)} 篇内容已变更")
    if parts:
        print(f"结论: 本次需要处理 {'，'.join(parts)}")
    elif manual:
        # NEW=0 但有 MANUAL 时，不应误导为"所有内容已消化完毕"
        print(f"结论: 无新内容，但有 {len(manual)} 篇待人工确认（可能是新增内容，建议核验）")
    else:
        print("结论: 所有内容已消化完毕")
    print("=" * 60)


def main():
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Knowledge Vault 未消化文件检测工具"
    )
    parser.add_argument(
        "--vault",
        required=True,
        help="知识库根目录路径",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出结果",
    )
    args = parser.parse_args()

    vault_root = Path(args.vault).resolve()
    if not vault_root.exists():
        print(f"[错误] Vault 目录不存在: {vault_root}", file=sys.stderr)
        sys.exit(1)

    results = check_undigested(vault_root)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print_report(results, vault_root)


if __name__ == "__main__":
    main()
