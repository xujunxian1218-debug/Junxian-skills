#!/usr/bin/env python3
"""Knowledge Vault manifest 生成脚本（v1.12.0 Analysis token 优化）。

预生成 .llm-wiki-cache/manifest.json，Analysis 读 manifest 替代 index.md 全文
做概念查找/判重（index.md ~10-13k tokens → manifest ~4-5k）。manifest 含概念
（name + 一句话定义 + 反引数）+ 主题（name + 摘要数 + 概述），砍掉 index.md 的
时间线索引（占 53%，对 Analysis 价值最低）。

数据源（source of truth，不依赖 index.md 格式）：
- concepts/*.md 的 `## 一句话定义` 板块
- topics/*.md 的 frontmatter `related_summaries` 数 + `## 概述` 段
- lintlib.compute_inbound_counts（反引数）

命名彩蛋：.llm-wiki-cache/manifest.json 的 stem 含 "manifest" → 被 ingest.py /
check_undigested.py 的 SKIP_KEYWORDS 自动 SKIP（不当 raw 摄入、不标 NEW），
有益副作用——改名将失效（如 concept-manifest.json 不被 SKIP）。

用法:
  py build_manifest.py --vault /path              # 生成 .llm-wiki-cache/manifest.json
  py build_manifest.py --vault /path --json       # 输出 JSON 到 stdout（不写文件）
"""
import argparse
import json
import re
import sys
from pathlib import Path

from lintlib import compute_inbound_counts, strip_fenced_code

DEF_RE = re.compile(r"^## 一句话定义\s*\n(.+?)(?=\n## |\Z)", re.M | re.S)
OVERVIEW_RE = re.compile(r"^## 概述\s*\n(.+?)(?=\n## |\Z)", re.M | re.S)


def _extract_section(text: str, regex) -> str:
    """提取一个 ## 板块的第一段内容（去代码块干扰，单行化）。"""
    text = strip_fenced_code(text)
    m = regex.search(text)
    if not m:
        return ""
    block = m.group(1).strip()
    first_para = block.split("\n\n")[0].strip()
    return first_para.replace("\n", " ")


def _parse_related_summaries_count(frontmatter: str) -> int:
    """从 topic frontmatter 数 related_summaries 条目（block list 或 inline list）。"""
    # block list: related_summaries:\n  - xxx\n  - yyy
    block = re.search(r"^related_summaries:\s*\n((?:\s+-\s+.+\n?)+)", frontmatter, re.M)
    if block:
        return block.group(1).count("- ")
    # inline list: related_summaries: [a, b]
    inline = re.search(r"^related_summaries:\s*\[(.*?)\]", frontmatter, re.M)
    if inline:
        items = [x for x in inline.group(1).split(",") if x.strip()]
        return len(items)
    return 0


def _split_frontmatter(text: str) -> str:
    """返回 frontmatter 内容（不含 --- 包裹）；无 frontmatter 返回空串。"""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[3:end]
    return ""


def build_manifest(vault_root: Path) -> dict:
    """构建 manifest dict：concepts（name+def+inbound）+ topics（name+n_summaries+intro）。"""
    knowledge = vault_root / "knowledge"
    concepts_dir = knowledge / "concepts"
    topics_dir = knowledge / "topics"
    inbound = compute_inbound_counts(vault_root)

    def rel(p: Path) -> str:
        return str(p.relative_to(vault_root)).replace("\\", "/")

    concepts = []
    if concepts_dir.exists():
        for f in sorted(concepts_dir.glob("*.md")):
            stem = f.stem
            try:
                text = f.read_text(encoding="utf-8")
            except Exception:
                continue
            defn = _extract_section(text, DEF_RE)
            concepts.append({
                "name": stem.removesuffix("-概念"),
                "file": rel(f),
                "def": defn[:80] + ("…" if len(defn) > 80 else ""),
                "inbound": inbound.get(stem, 0),
            })

    topics = []
    if topics_dir.exists():
        for f in sorted(topics_dir.glob("*.md")):
            stem = f.stem
            try:
                text = f.read_text(encoding="utf-8")
            except Exception:
                continue
            intro = _extract_section(text, OVERVIEW_RE)
            topics.append({
                "name": stem.removesuffix("-主题"),
                "file": rel(f),
                "n_summaries": _parse_related_summaries_count(_split_frontmatter(text)),
                "intro": intro[:80] + ("…" if len(intro) > 80 else ""),
            })

    return {
        "stats": {"concepts": len(concepts), "topics": len(topics)},
        "concepts": concepts,
        "topics": topics,
    }


def main():
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Knowledge Vault manifest 生成（Analysis token 优化）")
    parser.add_argument("--vault", required=True, help="知识库根目录路径")
    parser.add_argument("--json", action="store_true",
                        help="输出 JSON 到 stdout（不写 .llm-wiki-cache/manifest.json）")
    args = parser.parse_args()

    vault_root = Path(args.vault).resolve()
    if not vault_root.exists():
        print(f"[错误] 知识库路径不存在: {vault_root}", file=sys.stderr)
        sys.exit(1)

    manifest = build_manifest(vault_root)

    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        cache_dir = vault_root / ".llm-wiki-cache"
        cache_dir.mkdir(exist_ok=True)
        out = cache_dir / "manifest.json"
        out.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        print(f"manifest 已生成: {out}")
        print(f"  概念: {manifest['stats']['concepts']}，主题: {manifest['stats']['topics']}")


if __name__ == "__main__":
    main()
