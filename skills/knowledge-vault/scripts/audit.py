#!/usr/bin/env python3
"""Knowledge Vault 巡检脚本（v1.9.0 工程化）。

Audit 9 项检查中 8 项确定性检查脚本化（第 3 项"一致性"需语义判断，由 Agent 完成）。
对照 references/audit-rules.md。Agent 基于本脚本输出 + 第 3 项人工判断生成 audit-report。

token 收益：Audit 全流程 Agent 侧从 ~390k 降至 ~30-50k（v1.9.0 目标），
self-check D7 调用 --check-cross-refs 后从 ~64k 降至 ~1-2k。

用法:
  py audit.py --vault /path/to/vault              # 跑全部确定性检查
  py audit.py --vault /path --check-naming        # 仅跑命名规范
  py audit.py --vault /path --check-cross-refs    # 链接有效性（self-check D7 用）
  py audit.py --vault /path --json                # JSON 输出（供 Agent 解析）
"""
import argparse
import json
import re
import sys
from pathlib import Path

from lintlib import (
    build_file_index,
    check_link_target_exists,
    detect_duplicate_sections,
    extract_wikilinks,
    has_unsafe_filename_chars,
    normalize_filename,
    strip_frontmatter,
    validate_wikilink_slug,
)

KNOWLEDGE_DIR = "knowledge"

# summary frontmatter required fields & body sections (audit-rules section 2)
REQUIRED_SUMMARY_FIELDS = ["source", "title", "date", "author", "tags"]
REQUIRED_SUMMARY_SECTIONS = ["一句话摘要", "核心要点", "关键概念", "原文金句"]
SOURCE_FIELD_RE = re.compile(r"^source:\s*\[?\[?(.*?)\]?\]?\s*$", re.M)
INDEX_STAT_RE = re.compile(r"原始文件数：(\d+)\s*\|\s*摘要数：(\d+)\s*\|\s*主题页数：(\d+)\s*\|\s*概念卡数：(\d+)")

# 注册的检查项：audit-rules 9 项中 8 项确定性检查 + cross_refs（link_validity 的概念卡
# 子集，供 self-check D7 单独调用）+ duplicate_sections（重复板块 lint，非 9 项之一）。
ALL_CHECKS = [
    "coverage", "completeness", "link_validity", "naming",
    "index_accuracy", "link_format", "source_optimization", "orphan",
    "cross_refs", "duplicate_sections",
]


# ── 检查项实现 ──

def check_naming(vault_root: Path) -> dict:
    """检查 5 命名规范：summaries/concepts/topics 后缀 + 无不安全字符。

    规范（audit-rules.md 第 53-58 行）：
      summaries: {title}-摘要-{YYYY-MM-DD}.md
      concepts:  {name}-概念.md
      topics:    {name}-主题.md
      禁用字符:  \\ / : * ? " < > | # % ^ & $ ! ` ' = ~
    """
    problems = []
    counts = {"summaries": 0, "concepts": 0, "topics": 0}
    # naming spec (audit-rules.md section 5):
    #   summaries: {title}-摘要-{YYYY-MM-DD}.md -> stem CONTAINS "-摘要-"
    #   concepts:  {name}-概念.md              -> stem ENDSWITH "-概念"
    #   topics:    {name}-主题.md              -> stem ENDSWITH "-主题"
    spec = [("summaries", "-摘要-", "contain"), ("concepts", "-概念", "endswith"), ("topics", "-主题", "endswith")]
    for sub, suffix, mode in spec:
        d = vault_root / KNOWLEDGE_DIR / sub
        if not d.exists():
            continue
        for f in sorted(d.glob("*.md")):
            counts[sub] += 1
            rel = str(f.relative_to(vault_root))
            # unsafe chars
            bad = has_unsafe_filename_chars(f.name)
            if bad:
                problems.append({"file": rel, "issue": f"含不安全字符 {''.join(sorted(bad))}"})
            # suffix spec
            compliant = (suffix in f.stem) if mode == "contain" else f.stem.endswith(suffix)
            if not compliant:
                problems.append({"file": rel, "issue": f"命名缺 {suffix} 标记（规范见 audit-rules.md）"})
    return {
        "check": "naming",
        "status": "pass" if not problems else "fail",
        "problems": problems,
        "summary": f"扫描 summaries/concepts/topics：{counts}",
    }


def check_coverage(vault_root: Path) -> dict:
    """检查 1 覆盖率：raw vs summary 比对。报 orphan raw（无摘要）+ orphan summary（source 指向不存在）。"""
    raw_dir = vault_root / "raw"
    summaries_dir = vault_root / KNOWLEDGE_DIR / "summaries"
    raw_norm: dict[str, Path] = {}
    if raw_dir.exists():
        for f in raw_dir.rglob("*.md"):
            if "images" in f.parts:
                continue
            raw_norm[normalize_filename(f.stem)] = f
    src_norm: dict[str, Path] = {}
    if summaries_dir.exists():
        for f in summaries_dir.glob("*.md"):
            try:
                text = f.read_text(encoding="utf-8")
            except Exception:
                continue
            m = SOURCE_FIELD_RE.search(text)
            if not m:
                continue
            src = m.group(1).strip()
            name = Path(src).stem if ("/" in src or "\\" in src) else src
            name = re.sub(r"\.md$", "", name)
            src_norm[normalize_filename(name)] = f
    matched = set(raw_norm) & set(src_norm)
    orphan_raw = [raw_norm[k] for k in (set(raw_norm) - set(src_norm))]
    orphan_summary = [src_norm[k] for k in (set(src_norm) - set(raw_norm))]
    problems = []
    for p in orphan_raw[:50]:
        problems.append({"file": str(p.relative_to(vault_root)), "issue": "orphan raw：无对应摘要", "severity": "warning"})
    for p in orphan_summary[:50]:
        problems.append({"file": str(p.relative_to(vault_root)), "issue": "orphan summary：source 指向的 raw 不存在或未匹配", "severity": "warning"})
    return {"check": "coverage",
            "status": "pass" if not orphan_raw and not orphan_summary else "fail",
            "problems": problems,
            "summary": f"raw {len(raw_norm)}，摘要 {len(src_norm)}，匹配 {len(matched)}，orphan raw {len(orphan_raw)}，orphan summary {len(orphan_summary)}"}


def check_completeness(vault_root: Path) -> dict:
    """检查 2 完整性：summary frontmatter 必填字段 + 必填板块标题精确匹配。"""
    summaries = vault_root / KNOWLEDGE_DIR / "summaries"
    problems = []
    checked = 0
    for f in _iter_md(summaries):
        checked += 1
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            continue
        rel = str(f.relative_to(vault_root))
        for field in REQUIRED_SUMMARY_FIELDS:
            if not re.search(rf"^{re.escape(field)}:\s*\S", text, re.M):
                problems.append({"file": rel, "issue": f"frontmatter 缺字段或为空: {field}", "severity": "warning"})
        for sec in REQUIRED_SUMMARY_SECTIONS:
            if not re.search(rf"^##\s*{re.escape(sec)}", text, re.M):
                problems.append({"file": rel, "issue": f"缺板块「{sec}」（标题须精确匹配，不允许同义词）", "severity": "warning"})
    return {"check": "completeness",
            "status": "pass" if not problems else "fail",
            "problems": problems,
            "summary": f"扫描 {checked} 篇摘要，{len(problems)} 处缺失"}


def _iter_md(directory: Path):
    """Yield sorted .md files in directory (empty iterator if directory missing)."""
    if directory.exists():
        yield from sorted(directory.glob("*.md"))


def check_link_validity(vault_root: Path) -> dict:
    """检查 4 链接有效性：topics/concepts/summaries 所有 wikilink 指向真实存在的文件。"""
    problems = []
    idx = build_file_index(vault_root)
    knowledge = vault_root / KNOWLEDGE_DIR
    checked = 0
    for sub in ("topics", "concepts", "summaries"):
        for f in _iter_md(knowledge / sub):
            checked += 1
            try:
                text = f.read_text(encoding="utf-8")
            except Exception:
                continue
            for target in extract_wikilinks(strip_frontmatter(text)):
                ok, reason = validate_wikilink_slug(target)
                if not ok:
                    problems.append({"file": str(f.relative_to(vault_root)), "issue": reason, "severity": "minor"})
                    continue
                exists, _ = check_link_target_exists(target, idx)
                if not exists:
                    problems.append({"file": str(f.relative_to(vault_root)),
                                     "issue": f"断链: [[{target}]] 目标文件不存在", "severity": "warning"})
    return {"check": "link_validity",
            "status": "pass" if not problems else "fail",
            "problems": problems,
            "summary": f"扫描 {checked} 个文件，{len(problems)} 处断链/格式问题"}


def check_index_accuracy(vault_root: Path) -> dict:
    """检查 6 索引准确性：index.md 头部统计 vs 实际文件数。"""
    index = vault_root / KNOWLEDGE_DIR / "index.md"
    if not index.exists():
        return {"check": "index_accuracy", "status": "pass", "problems": [], "summary": "无 index.md"}
    try:
        text = index.read_text(encoding="utf-8")
    except Exception:
        return {"check": "index_accuracy", "status": "pass", "problems": [], "summary": "index.md 读取失败"}
    m = INDEX_STAT_RE.search(text)
    if not m:
        return {"check": "index_accuracy", "status": "fail",
                "problems": [{"file": "knowledge/index.md", "issue": "未找到统计行（原始文件数/摘要数/...）", "severity": "warning"}],
                "summary": "统计行缺失"}
    stated = {"raw": int(m.group(1)), "summaries": int(m.group(2)),
              "topics": int(m.group(3)), "concepts": int(m.group(4))}
    actual = {
        "summaries": sum(1 for _ in _iter_md(vault_root / KNOWLEDGE_DIR / "summaries")),
        "topics": sum(1 for _ in _iter_md(vault_root / KNOWLEDGE_DIR / "topics")),
        "concepts": sum(1 for _ in _iter_md(vault_root / KNOWLEDGE_DIR / "concepts")),
    }
    raw_dir = vault_root / "raw"
    actual["raw"] = sum(1 for f in raw_dir.rglob("*.md") if "images" not in f.parts) if raw_dir.exists() else 0
    problems = []
    for key in ("raw", "summaries", "topics", "concepts"):
        if stated.get(key) != actual.get(key):
            problems.append({"file": "knowledge/index.md",
                             "issue": f"{key}: 统计 {stated.get(key)} != 实际 {actual.get(key)}",
                             "severity": "warning"})
    return {"check": "index_accuracy",
            "status": "pass" if not problems else "fail",
            "problems": problems,
            "summary": f"统计 {stated}，实际 {actual}"}


def check_link_format(vault_root: Path) -> dict:
    """检查 7 链接格式：index.md 表格 wikilink 纯 slug（禁 .md/路径字符/纯文本/markdown link）。"""
    index = vault_root / KNOWLEDGE_DIR / "index.md"
    if not index.exists():
        return {"check": "link_format", "status": "pass", "problems": [], "summary": "无 index.md"}
    try:
        text = index.read_text(encoding="utf-8")
    except Exception:
        return {"check": "link_format", "status": "pass", "problems": [], "summary": "index.md 读取失败"}
    problems = []
    for target in extract_wikilinks(strip_frontmatter(text)):
        ok, reason = validate_wikilink_slug(target)
        if not ok:
            problems.append({"file": "knowledge/index.md", "issue": reason, "severity": "minor"})
    return {"check": "link_format",
            "status": "pass" if not problems else "fail",
            "problems": problems,
            "summary": f"index.md {len(problems)} 处 wikilink 格式问题"}


def check_source_optimization(vault_root: Path) -> dict:
    """检查 8 Source 优化（optional, Minor）：summary source 指向 ASR 转写时提示优化为预处理版本。"""
    summaries = vault_root / KNOWLEDGE_DIR / "summaries"
    problems = []
    for f in _iter_md(summaries):
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            continue
        m = SOURCE_FIELD_RE.search(text)
        if not m:
            continue
        src = m.group(1).strip()
        if ("转写" in src) or ("raw_transcripts" in src):
            problems.append({"file": str(f.relative_to(vault_root)),
                             "issue": f"source 指向 ASR 转写，建议优化为预处理版本: {src[:60]}",
                             "severity": "minor"})
    return {"check": "source_optimization",
            "status": "pass" if not problems else "fail",
            "problems": problems,
            "summary": f"{len(problems)} 篇 source 指向转写（优化建议）"}


def check_orphan(vault_root: Path) -> dict:
    """检查 9 孤儿检测：concept/topic 入链数。0=孤儿(Warning)，1=弱连接(Minor)。"""
    knowledge = vault_root / KNOWLEDGE_DIR
    inbound: dict[str, set[str]] = {}
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
    problems = []
    n_orphan = n_weak = 0
    for sub in ("concepts", "topics"):
        for f in _iter_md(knowledge / sub):
            stem = f.stem
            cnt = len(inbound.get(stem, set()))
            rel = str(f.relative_to(vault_root))
            if cnt == 0:
                problems.append({"file": rel, "issue": "孤儿（0 入链，无任何页面引用）", "severity": "warning"})
                n_orphan += 1
            elif cnt == 1:
                problems.append({"file": rel, "issue": "弱连接（仅 1 入链，有孤立风险）", "severity": "minor"})
                n_weak += 1
    return {"check": "orphan",
            "status": "pass" if n_orphan == 0 else "fail",
            "problems": problems,
            "summary": f"{n_orphan} 孤儿，{n_weak} 弱连接"}


def check_cross_refs(vault_root: Path) -> dict:
    """D7 交叉引用有效性：所有概念卡正文 wikilink 目标存在。self-check D7 调用。

    与 check_link_validity 区别：本检查只扫概念卡（D7 的范围），用于 Digest 后
    self-check 即时校验本次生成 + 全库概念卡的交叉引用。
    """
    problems = []
    idx = build_file_index(vault_root)
    concepts = vault_root / KNOWLEDGE_DIR / "concepts"
    checked = 0
    for f in _iter_md(concepts):
        checked += 1
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            continue
        for target in extract_wikilinks(strip_frontmatter(text)):
            ok, reason = validate_wikilink_slug(target)
            if not ok:
                problems.append({"file": str(f.relative_to(vault_root)), "issue": reason})
                continue
            exists, _ = check_link_target_exists(target, idx)
            if not exists:
                problems.append({"file": str(f.relative_to(vault_root)),
                                 "issue": f"断链: [[{target}]] 目标不存在", "severity": "warning"})
    return {"check": "cross_refs",
            "status": "pass" if not problems else "fail",
            "problems": problems,
            "summary": f"扫描 {checked} 张概念卡，{len(problems)} 处断链/格式问题"}


def check_duplicate_sections(vault_root: Path) -> dict:
    """额外 lint：同一 .md 内同名 ## 板块出现 ≥2 次（消化合并 bug，usage-log 2026-07-07）。

    非 audit-rules 9 项检查之一，是 self-check / lint 的补充：消化合并时若未检测同名
    板块，会产生重复的「与其他概念的关系」等段落。扫 concepts/topics/summaries。
    """
    problems = []
    checked = 0
    knowledge = vault_root / KNOWLEDGE_DIR
    for sub in ("concepts", "topics", "summaries"):
        for f in _iter_md(knowledge / sub):
            checked += 1
            dup = detect_duplicate_sections(f)
            if dup:
                rel = str(f.relative_to(vault_root))
                detail = "、".join(f"{t}×{c}" for t, c in dup.items())
                problems.append({"file": rel, "issue": f"重复板块：{detail}", "severity": "warning"})
    return {"check": "duplicate_sections",
            "status": "pass" if not problems else "fail",
            "problems": problems,
            "summary": f"扫描 {checked} 个文件，{len(problems)} 个含重复板块"}


CHECKS = {
    "coverage": check_coverage,
    "completeness": check_completeness,
    "link_validity": check_link_validity,
    "naming": check_naming,
    "index_accuracy": check_index_accuracy,
    "link_format": check_link_format,
    "source_optimization": check_source_optimization,
    "orphan": check_orphan,
    "cross_refs": check_cross_refs,
    "duplicate_sections": check_duplicate_sections,
}


def run_checks(vault_root: Path, selected: list[str]) -> dict:
    return {name: CHECKS[name](vault_root) for name in selected if name in CHECKS}


def print_human_report(results: dict, vault_root: Path) -> None:
    print("=" * 60)
    print("Knowledge Vault 巡检报告（确定性检查）")
    print("=" * 60)
    print(f"Vault: {vault_root}")
    print()
    icons = {"pass": "✓", "fail": "✗", "not_implemented": "⋯"}
    for name, r in results.items():
        status = r.get("status", "?")
        n = len(r.get("problems", []))
        print(f"{icons.get(status, '?')} [{name}] {status}  ({n} 个问题)")
        for p in r.get("problems", [])[:20]:
            msg = p.get("issue") or p.get("reason") or ""
            print(f"    - {p.get('file', '')}: {msg}")
        if n > 20:
            print(f"    ... 还有 {n - 20} 个")
    print()
    print("注：第 3 项「一致性」需语义判断，由 Agent 完成，不在本脚本范围。")
    print("=" * 60)


def main() -> None:
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Knowledge Vault 巡检工具 — 9 项中 8 项确定性检查脚本化"
    )
    parser.add_argument("--vault", required=True, help="知识库根目录路径")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出结果")
    for c in ALL_CHECKS:
        parser.add_argument(
            f"--check-{c.replace('_', '-')}",
            action="store_true",
            help=f"仅跑 {c}",
        )
    args = parser.parse_args()

    vault_root = Path(args.vault).resolve()
    if not vault_root.exists():
        print(f"[错误] Vault 目录不存在: {vault_root}", file=sys.stderr)
        sys.exit(1)

    selected = [c for c in ALL_CHECKS if getattr(args, f"check_{c}")]
    if not selected:
        selected = ALL_CHECKS  # 默认全部

    results = run_checks(vault_root, selected)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print_human_report(results, vault_root)


if __name__ == "__main__":
    main()
