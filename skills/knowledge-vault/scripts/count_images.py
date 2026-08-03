#!/usr/bin/env python3
"""Knowledge Vault 图片引用统计脚本（v1.10.0 消耗控制 gate）。

扫描 NEW 文件（或 raw/ 全部）的图片引用，输出本地 / 远程 / 格式违规 / 缺失统计，
供 Digest 预检第 4 步消耗控制 gate 使用。只做正则统计 —— 不做 A/B/C/D/E 启发式
分类、不做裸引用语义判断、不做真识图（真识图校验在 v1.12.0+）。

扫描对象：raw/ 源文件（预检阶段摘要还没生成，扫的是消化输入，不是产出）。

4 步掩码去重管线（杜绝双计）：
  1. strip_frontmatter → 剥 YAML（source 字段不是内容引用）
  2. strip_fenced_code → 剥 ``` 代码块（复用 lintlib）
  3. backtick 违规检测 + 掩码 → inline code 内含图片引用记为违规，整段掩码
  4. RE_REMOTE 匹配 + 掩码 → 远程图（防止 RE_MARKDOWN 误匹配 https + /images/）
  5. 4 个 LOCAL_REGEXES 匹配 → 本地图，跨 regex 用 consumed 集合去重
  6. missing 检测（仅本地图）→ stem 查 build_file_index，找不到记为缺失

用法:
  py count_images.py --vault /path                    # 统计 NEW 文件
  py count_images.py --vault /path --scope all        # 统计 raw/ 全部
  py count_images.py --vault /path --files a.md b.md  # 显式文件列表
  py count_images.py --vault /path --json             # JSON 输出
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from lintlib import (
    build_file_index,
    check_link_target_exists,
    strip_fenced_code,
    strip_frontmatter,
)
from fix_image_paths import (
    RE_WIKILINK,
    RE_MARKDOWN,
    RE_WIKILINK_RELATIVE,
    RE_MARKDOWN_RELATIVE,
)
from check_undigested import collect_raw_files

# 远程图片（https/http）— fix_image_paths 的 4 个正则强制 /images/ 片段，不匹配远程
RE_REMOTE = re.compile(r'!\[([^\]]*)\]\((https?://[^)]+)\)')
# 行内代码区间 — 检测 backtick 包裹的图片违规（在 Obsidian 中渲染不出来）
RE_INLINE_CODE = re.compile(r'`([^`\n]+)`')
# 判断 inline code 内是否含图片引用（![[ 或 ![...]( ）)
RE_IMAGE_HINT = re.compile(r'!\[\[|!\[.*?\]\(')

# 本地图正则：wikilink 类 path=group(1)，markdown 类 path=group(2)
LOCAL_REGEXES = [
    (RE_WIKILINK, 1),
    (RE_WIKILINK_RELATIVE, 1),
    (RE_MARKDOWN, 2),
    (RE_MARKDOWN_RELATIVE, 2),
]

SCRIPT_DIR = Path(__file__).resolve().parent


def _mask_spans(text: str, spans: list[tuple[int, int]]) -> str:
    """将已匹配的字符区间替换为等长空格，保持后续 regex 字符位置稳定。"""
    if not spans:
        return text
    chars = list(text)
    for start, end in spans:
        for i in range(start, end):
            if i < len(chars):
                chars[i] = " "
    return "".join(chars)


def count_images_in_text(text: str, file_index: dict) -> dict:
    """扫描单个文本的图片引用。返回原始列表（计数由上层 len() 算）。"""
    text = strip_frontmatter(text)
    text = strip_fenced_code(text)

    # Step 1: backtick 违规 + 掩码（这些图被反引号包裹，渲染不出来）
    violations = []
    backtick_spans = []
    for m in RE_INLINE_CODE.finditer(text):
        if RE_IMAGE_HINT.search(m.group(1)):
            violations.append({"ref": m.group(0), "type": "backtick"})
            backtick_spans.append(m.span())
    text = _mask_spans(text, backtick_spans)

    # Step 2: 远程图 + 掩码（防止 RE_MARKDOWN 误匹配含 /images/ 的远程 URL）
    remote = []
    remote_spans = []
    for m in RE_REMOTE.finditer(text):
        remote.append({"ref": m.group(0), "url": m.group(2)})
        remote_spans.append(m.span())
    text = _mask_spans(text, remote_spans)

    # Step 3: 本地图（4 regex，跨 regex 用 consumed 集合去重）
    local = []
    consumed = set()
    for regex, path_group in LOCAL_REGEXES:
        for m in regex.finditer(text):
            # 跳过已被前一个 regex 消费的区间
            if any(i in consumed for i in range(m.start(), m.end())):
                continue
            local.append({"ref": m.group(0), "path": m.group(path_group)})
            for i in range(m.start(), m.end()):
                consumed.add(i)

    # Step 4: missing 检测（仅本地图；远程图是独立类别，不算 missing）
    valid_local = []
    missing = []
    for img in local:
        exists, _ = check_link_target_exists(img["path"], file_index)
        if exists:
            valid_local.append(img)
        else:
            missing.append({"ref": img["ref"], "path": img["path"]})

    return {
        "local_imgs": valid_local,   # 存在于磁盘的本地图
        "remote_imgs": remote,
        "violations": violations,
        "missing": missing,          # 引用了但磁盘找不到（独立于 local 计数）
    }


def count_images_in_file(md_path: Path, vault_root: Path, file_index: dict) -> dict:
    """读单个文件 + 扫描，返回单文件结果（含相对路径）。"""
    rel = str(md_path.relative_to(vault_root))
    try:
        text = md_path.read_text(encoding="utf-8")
    except Exception as e:
        return {
            "file": rel, "error": f"读取失败: {e}",
            "total": 0, "local": 0, "remote": 0,
            "violations": [], "missing": [],
        }
    r = count_images_in_text(text, file_index)
    local_n = len(r["local_imgs"])      # 存在的本地
    remote_n = len(r["remote_imgs"])
    viol_n = len(r["violations"])
    missing_n = len(r["missing"])
    return {
        "file": rel,
        "total": local_n + remote_n + viol_n + missing_n,
        "local": local_n,
        "remote": remote_n,
        "violations": r["violations"],   # detail 列表
        "missing": r["missing"],          # detail 列表
    }


def collect_target_files(
    vault_root: Path, scope: str, explicit_files: list[str] | None
) -> list[Path]:
    """收集待统计的 raw .md 文件。"""
    if explicit_files:
        files = []
        for f in explicit_files:
            p = Path(f)
            if not p.is_absolute():
                p = vault_root / f
            if p.exists() and p.suffix == ".md":
                files.append(p)
        return sorted(set(files))

    if scope == "all":
        raw_dir = vault_root / "raw"
        return collect_raw_files(raw_dir) if raw_dir.exists() else []

    # scope == "new"：subprocess 调 check_undigested 拿 NEW 列表
    # （check_undigested 有 save_hash_cache 副作用，与预检步骤 3 一致，可接受；
    #  SKILL.md 推荐 --files 路径避免重复跑。）
    result = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "check_undigested.py"),
         "--vault", str(vault_root), "--json"],
        capture_output=True, text=True, encoding="utf-8",
    )
    if result.returncode != 0:
        print(f"[错误] 调用 check_undigested 失败：{result.stderr.strip()}",
              file=sys.stderr)
        sys.exit(1)
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("[错误] 无法解析 check_undigested 的 JSON 输出", file=sys.stderr)
        sys.exit(1)
    return sorted((vault_root / item["file"]) for item in data.get("new", []))


def run_count(
    vault_root: Path, scope: str, explicit_files: list[str] | None
) -> dict:
    """聚合所有文件结果 + summary。"""
    files = collect_target_files(vault_root, scope, explicit_files)
    file_index = build_file_index(vault_root)
    file_results = [count_images_in_file(f, vault_root, file_index) for f in files]

    summary = {
        "total": sum(r["total"] for r in file_results),
        "local": sum(r["local"] for r in file_results),
        "remote": sum(r["remote"] for r in file_results),
        "violations": sum(len(r["violations"]) for r in file_results),
        "missing": sum(len(r["missing"]) for r in file_results),
        "scope": "files" if explicit_files else scope,
        "file_count": len(file_results),
    }
    return {"summary": summary, "files": file_results}


def print_report(results: dict, vault_root: Path) -> None:
    """人类可读报告（对齐 check_undigested / audit 的 === 60 + ── section 约定）。"""
    s = results["summary"]
    print("=" * 60)
    print("图片引用统计报告")
    print(f"Vault: {vault_root}")
    print(f"范围: {s['scope']}（{s['file_count']} 篇文件）")
    print("=" * 60)
    has_any = False
    for f in results["files"]:
        if f["total"] == 0:
            continue
        has_any = True
        print(f"── {f['file']}（{f['total']}图: {f['local']}本地 "
              f"{f['remote']}远程 {len(f['violations'])}违规）──")
        for m in f["missing"]:
            print(f"  ⚠ 缺失: {m['ref']}")
        for v in f["violations"]:
            print(f"  ⚠ 违规({v['type']}): {v['ref']}")
    if not has_any:
        print("（本次涉及文件无图片引用）")
    print("=" * 60)
    print(f"合计: {s['total']} 图引用（{s['local']} 本地 / {s['remote']} 远程 / "
          f"{s['violations']} 格式违规 / {s['missing']} 缺失）")
    if s["remote"] > 0:
        print("注：远程图片当前无法本地识图（远程下载在后续版本）。")
    if s["violations"] > 0:
        print("注：格式违规图片（backtick 包裹）在 Obsidian 中不会显示。")
    print("=" * 60)


def main():
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Knowledge Vault 图片引用统计（消耗控制 gate）")
    parser.add_argument("--vault", required=True, help="知识库根目录路径")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出结果")
    parser.add_argument("--scope", choices=["new", "all"], default="new",
                        help="统计范围：new=仅未消化文件, all=raw/ 全部文件")
    parser.add_argument("--files", nargs="*", default=None,
                        help="显式文件列表（从预检步骤 3 的 NEW 传入，避免重复跑 check_undigested）")
    args = parser.parse_args()

    vault_root = Path(args.vault).resolve()
    if not vault_root.exists():
        print(f"[错误] 知识库路径不存在: {vault_root}", file=sys.stderr)
        sys.exit(1)

    results = run_count(vault_root, args.scope, args.files)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print_report(results, vault_root)


if __name__ == "__main__":
    main()
