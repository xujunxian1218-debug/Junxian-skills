#!/usr/bin/env python3
"""
Knowledge Vault 初始化脚本

创建知识库的目录结构、复制模板文件、生成初始索引。

用法:
  python init_vault.py /path/to/vault
  python init_vault.py .   # 当前目录作为 vault
"""

import argparse
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

# ── skill 目录（脚本所在目录的上级） ──
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATES_SRC = SKILL_DIR / "templates"

# 需要创建的目录
DIRS = [
    "raw/images",
    "knowledge/summaries",
    "knowledge/concepts",
    "knowledge/topics",
    "notes",
    "outputs",
    "templates",
]


def check_env() -> bool:
    """Check environment dependencies. Returns True if all core deps are present."""
    all_ok = True

    print("\n--- 环境检查 ---")

    # Core dependencies
    core_deps = [
        ("markitdown", "markitdown", 'pip install "markitdown[all]>=0.1.5"'),
        ("marker-pdf", "marker", 'pip install "marker-pdf>=1.10.0"'),
    ]
    for name, import_name, install_cmd in core_deps:
        try:
            __import__(import_name)
            print(f"  [OK] {name}")
        except ImportError:
            print(f"  [MISSING] {name}  ->  {install_cmd}")
            all_ok = False

    # Optional dependencies
    try:
        __import__("faster_whisper")
        print(f"  [OK] faster-whisper (optional)")
    except ImportError:
        print(f"  [--] faster-whisper (optional, 音视频转写)  ->  pip install \"faster-whisper>=1.0.0\"")

    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        print(f"  [OK] ffmpeg")
    else:
        print(f"  [--] ffmpeg (optional, 视频提取音轨)")
        print(f"       Install: https://ffmpeg.org/download.html")
        print(f"       Windows: choco install ffmpeg")

    if not all_ok:
        print("\n  核心依赖缺失，部分格式转换不可用。只需处理 Markdown 文件则可忽略。")

    return all_ok


# 初始 index.md
INDEX_MD = """\
# 知识系统总索引

> 最后更新：{date}
> 原始文件数：0 | 摘要数：0 | 主题页数：0 | 概念卡数：0

---

## 目录结构

```
knowledge/
├── index.md              ← 你在这里
├── summaries/            ← 每篇 raw 的结构化摘要
├── concepts/             ← 核心概念卡
└── topics/               ← 主题页
```

---

## 主题导航

> 尚无主题页。消化 raw 文件后将自动在此生成。

---

## 核心概念索引

| 概念 | 文件 | 一句话定义 |
|------|------|-----------|

> 尚无概念卡。消化 raw 文件后将自动在此生成。

---

## 按时间线的摘要索引

> 尚无摘要。摄取并消化 raw 文件后将自动在此生成。

---

## 使用指南

1. **快速查找**：先看主题导航，找到相关主题页，再追踪到具体摘要
2. **概念理解**：查阅概念卡获得跨文章的概念整合
3. **时间回溯**：按时间线索引定位特定日期的内容
4. **增量更新**：新增 raw 文件后，运行消化流程更新本索引
"""

# 初始 dashboard.md
DASHBOARD_MD = """\
# 知识系统面板

> 在 Obsidian 中安装 Dataview 插件后，以下查询会自动渲染为动态列表。
> **注意**：请确保在「阅读视图」中查看此文件（按 Ctrl+E 或点击右上角书本图标切换）。

---

## 系统统计

```dataview
TABLE WITHOUT ID
  length(rows) as "摘要数量"
FROM "knowledge/summaries"
GROUP BY true
```

---

## 最近添加的摘要（最新 15 篇）

```dataview
TABLE date AS "日期", tags AS "标签"
FROM "knowledge/summaries"
SORT date DESC
LIMIT 15
```

---

## 按标签浏览

```dataview
TABLE length(rows) AS "文章数"
FROM "knowledge/summaries"
FLATTEN tags AS tag
GROUP BY tag
SORT length(rows) DESC
```

---

## 所有概念卡

```dataview
TABLE name_en AS "英文名", length(file.outlinks) AS "关联数"
FROM "knowledge/concepts"
SORT name ASC
```

---

## 所有主题页

```dataview
TABLE length(related_summaries) AS "摘要数", updated AS "最后更新"
FROM "knowledge/topics"
SORT updated DESC
```

---

## 查找未消化的 raw 文件

```dataview
TABLE file.mtime AS "修改时间", file.size AS "文件大小"
FROM "raw"
WHERE !startswith(file.folder, "raw/images")
SORT file.mtime DESC
```

---

## 我的个人笔记

```dataview
TABLE file.mtime AS "修改时间", length(file.outlinks) AS "关联知识"
FROM "notes"
SORT file.mtime DESC
```
"""


def init_vault(vault_path: Path) -> None:
    """Initialize vault directory structure and files."""
    vault = vault_path.resolve()

    if not vault.exists():
        vault.mkdir(parents=True, exist_ok=True)
        print(f"创建 vault 目录: {vault}")
    else:
        print(f"Vault 目录已存在: {vault}")

    # 1. 创建目录结构
    print("\n--- 创建目录结构 ---")
    for d in DIRS:
        dir_path = vault / d
        if dir_path.exists():
            print(f"  [已存在] {d}/")
        else:
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"  [创建] {d}/")

    # 2. 复制模板文件
    print("\n--- 复制模板文件 ---")
    if TEMPLATES_SRC.exists():
        templates_dst = vault / "templates"
        for tpl in sorted(TEMPLATES_SRC.glob("*.md")):
            dst = templates_dst / tpl.name
            if dst.exists():
                print(f"  [已存在] {tpl.name}")
            else:
                shutil.copy2(tpl, dst)
                print(f"  [复制] {tpl.name}")
    else:
        print(f"  [警告] 模板源目录不存在: {TEMPLATES_SRC}")
        print(f"  请确保 skill 的 templates/ 目录完整")

    # 2.5 复制 purpose.md 到 vault 根目录
    purpose_src = TEMPLATES_SRC / "tpl-purpose.md"
    purpose_dst = vault / "purpose.md"
    if purpose_dst.exists():
        print("  [已存在] purpose.md（用户已填写，不覆盖）")
    elif purpose_src.exists():
        content = purpose_src.read_text(encoding="utf-8")
        content = content.replace("{{date:YYYY-MM-DD}}", date.today().isoformat())
        purpose_dst.write_text(content, encoding="utf-8")
        print("  [创建] purpose.md — 请编辑此文件定义知识库目标")
    else:
        print("  [跳过] tpl-purpose.md 模板不存在")

    # 3. 生成 index.md
    print("\n--- 生成索引文件 ---")
    index_path = vault / "knowledge" / "index.md"
    if index_path.exists():
        print("  [已存在] knowledge/index.md")
    else:
        index_path.write_text(
            INDEX_MD.format(date=date.today().isoformat()),
            encoding="utf-8",
        )
        print("  [创建] knowledge/index.md")

    # 4. 生成 dashboard.md
    dashboard_path = vault / "knowledge" / "dashboard.md"
    if dashboard_path.exists():
        print("  [已存在] knowledge/dashboard.md")
    else:
        dashboard_path.write_text(DASHBOARD_MD, encoding="utf-8")
        print("  [创建] knowledge/dashboard.md")

    # 4.5 创建空 overview.md
    overview_src = TEMPLATES_SRC / "tpl-overview.md"
    overview_dst = vault / "knowledge" / "overview.md"
    if overview_dst.exists():
        print("  [已存在] knowledge/overview.md")
    elif overview_src.exists():
        content = overview_src.read_text(encoding="utf-8")
        content = content.replace("{{date:YYYY-MM-DD}}", date.today().isoformat())
        overview_dst.write_text(content, encoding="utf-8")
        print("  [创建] knowledge/overview.md")
    else:
        print("  [跳过] tpl-overview.md 模板不存在")

    # 5. 环境检查
    check_env()

    print("\n" + "=" * 50)
    print("Vault 初始化完成！")
    print(f"\n下一步:")
    print(f"  1. 编辑 {vault}/purpose.md 定义知识库目标和研究范围")
    print(f"  2. 将文件放入 {vault}/raw/ 或指定文件摄取")
    print(f"  3. 运行摄取: python {SCRIPT_DIR / 'ingest.py'} --auto --vault {vault}")
    print(f"  4. 让 Claude 执行消化流程")


def main():
    # Windows 控制台 UTF-8 输出
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Knowledge Vault 初始化工具 — 创建知识库目录结构和模板"
    )
    parser.add_argument(
        "vault_path",
        nargs="?",
        help="知识库根目录路径（新目录或已有目录均可）",
    )
    parser.add_argument(
        "--check-env",
        action="store_true",
        help="仅检查环境依赖，不初始化 vault",
    )
    args = parser.parse_args()

    if args.check_env:
        check_env()
        return

    if not args.vault_path:
        parser.error("vault_path is required unless using --check-env")

    init_vault(Path(args.vault_path))


if __name__ == "__main__":
    main()
