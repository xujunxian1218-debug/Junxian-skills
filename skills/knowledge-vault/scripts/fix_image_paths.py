#!/usr/bin/env python3
"""
图片路径修正工具 — 统一 markdown 文件中的图片引用路径。

将 Obsidian 双链或标准 markdown 中的图片路径前缀替换为目标前缀，
保留别名（如 |cover_image），并输出修正统计。

用法:
  # 指定源前缀和目标前缀
  python fix_image_paths.py raw/ --from "source_vault/images/" --to "raw/images/"

  # 自动检测 Obsidian vault 前缀（匹配 ![[xxx/images/]] 模式）
  python fix_image_paths.py raw/ --to "raw/images/" --auto

  # 预览模式，不实际修改文件
  python fix_image_paths.py raw/ --from "source_vault/images/" --to "raw/images/" --dry-run

  # 同时修正 Obsidian 双链和标准 markdown 格式
  python fix_image_paths.py raw/ --from "source_vault/images/" --to "raw/images/" --both
"""

import argparse
import re
import sys
from pathlib import Path


# ── 正则模式 ──

# Obsidian 双链图片: ![[prefix/images/name.jpg|alias]] 或 ![[prefix/images/name.jpg]]
RE_WIKILINK = re.compile(
    r'!\[\[([^|\]]+?/images/[^|\]]+?)((?:\|[^]]*?)?)\]\]'
)

# 标准 markdown 图片: ![alt](prefix/images/name.jpg)
RE_MARKDOWN = re.compile(
    r'!\[([^\]]*?)\]\(([^)]+?/images/[^)]+?)\)'
)

# 相对路径图片引用（不含目录前缀，仅文件名）
RE_WIKILINK_RELATIVE = re.compile(
    r'!\[\[(images/[^|\]]+?)((?:\|[^]]*?)?)\]\]'
)
RE_MARKDOWN_RELATIVE = re.compile(
    r'!\[([^\]]*?)\]\((images/[^)]+?)\)'
)


def detect_vault_prefix(directory: Path, exclude_prefix: str | None = None) -> str | None:
    """自动检测 Obsidian vault 图片路径前缀。

    扫描目录下的 md 文件，找到最常用的 ![[xxx/images/]] 前缀。
    排除 exclude_prefix（通常是目标前缀，避免把已修正的路径当作源前缀）。
    """
    prefix_counts: dict[str, int] = {}

    for md_file in directory.rglob("*.md"):
        try:
            text = md_file.read_text(encoding="utf-8")
        except Exception:
            continue

        for match in RE_WIKILINK.finditer(text):
            path_part = match.group(1)
            idx = path_part.find("/images/")
            if idx > 0:
                prefix = path_part[: idx + len("/images/")]
                if exclude_prefix and prefix == exclude_prefix:
                    continue
                prefix_counts[prefix] = prefix_counts.get(prefix, 0) + 1

    if not prefix_counts:
        return None

    return max(prefix_counts, key=prefix_counts.get)


def build_from_pattern(from_prefix: str) -> str:
    """构建路径前缀，确保以 / 结尾。"""
    if from_prefix and not from_prefix.endswith("/"):
        from_prefix += "/"
    return from_prefix


def build_to_pattern(to_prefix: str) -> str:
    """构建目标前缀，确保以 / 结尾。"""
    if to_prefix and not to_prefix.endswith("/"):
        to_prefix += "/"
    return to_prefix


def fix_file(
    md_file: Path,
    from_prefix: str,
    to_prefix: str,
    fix_wikilink: bool = True,
    fix_markdown: bool = False,
    dry_run: bool = False,
) -> tuple[int, int, list[str]]:
    """修正单个 md 文件的图片路径。

    返回: (修正数量, 图片总数, 修正详情列表)
    """
    try:
        text = md_file.read_text(encoding="utf-8")
    except Exception as e:
        return 0, 0, [f"[错误] 无法读取 {md_file}: {e}"]

    original = text
    changes: list[str] = []
    total_images = 0

    def replace_wikilink(match: re.Match) -> str:
        nonlocal total_images
        total_images += 1
        path_part = match.group(1)
        alias = match.group(2)

        if from_prefix and path_part.startswith(from_prefix):
            new_path = to_prefix + path_part[len(from_prefix):]
            changes.append(f"  ![[{path_part}{alias}]] → ![[{new_path}{alias}]]")
            return f"![[{new_path}{alias}]]"

        if not from_prefix or from_prefix == "images/":
            if path_part.startswith("images/"):
                new_path = to_prefix + path_part[len("images/"):]
                changes.append(f"  ![[{path_part}{alias}]] → ![[{new_path}{alias}]]")
                return f"![[{new_path}{alias}]]"

        return match.group(0)

    def replace_markdown(match: re.Match) -> str:
        nonlocal total_images
        total_images += 1
        alt_text = match.group(1)
        path_part = match.group(2)

        if from_prefix and path_part.startswith(from_prefix):
            new_path = to_prefix + path_part[len(from_prefix):]
            changes.append(f"  ![{alt_text}]({path_part}) → ![{alt_text}]({new_path})")
            return f"![{alt_text}]({new_path})"

        if not from_prefix or from_prefix == "images/":
            if path_part.startswith("images/"):
                new_path = to_prefix + path_part[len("images/"):]
                changes.append(f"  ![{alt_text}]({path_part}) → ![{alt_text}]({new_path})")
                return f"![{alt_text}]({new_path})"

        return match.group(0)

    if fix_wikilink:
        text = RE_WIKILINK.sub(replace_wikilink, text)
        text = RE_WIKILINK_RELATIVE.sub(replace_wikilink, text)

    if fix_markdown:
        text = RE_MARKDOWN.sub(replace_markdown, text)
        text = RE_MARKDOWN_RELATIVE.sub(replace_markdown, text)

    fixed = len(changes)

    if fixed > 0 and text != original and not dry_run:
        md_file.write_text(text, encoding="utf-8")

    return fixed, total_images, changes


def run_fix(
    directory: Path | str,
    to_prefix: str = "raw/images/",
    from_prefix: str | None = None,
    auto_detect: bool = True,
    fix_markdown: bool = False,
    quiet: bool = False,
) -> tuple[int, int]:
    """编程接口：修正目录下所有 md 文件的图片路径。

    Args:
        directory: 要扫描的目录
        to_prefix: 目标路径前缀
        from_prefix: 源路径前缀，为 None 时自动检测
        auto_detect: 是否自动检测 vault 前缀
        fix_markdown: 是否同时修正标准 markdown 格式
        quiet: 静默模式，不输出日志

    Returns:
        (修正文件数, 修正路径数)
    """
    target_dir = Path(directory).resolve()
    if not target_dir.is_dir():
        if not quiet:
            print(f"[跳过] 目录不存在: {target_dir}")
        return 0, 0

    to_prefix = build_to_pattern(to_prefix)

    if from_prefix is None and auto_detect:
        from_prefix = detect_vault_prefix(target_dir, exclude_prefix=to_prefix)

    if not from_prefix:
        if not quiet:
            print("[跳过] 未检测到需要修正的图片路径")
        return 0, 0

    from_prefix = build_from_pattern(from_prefix)

    if from_prefix == to_prefix:
        return 0, 0

    if not quiet:
        print(f"  图片路径修正: '{from_prefix}' -> '{to_prefix}'")

    md_files = sorted(target_dir.rglob("*.md"))
    total_fixed = 0
    files_changed = 0

    for md_file in md_files:
        if "images" in md_file.parts and md_file.suffix == ".md":
            continue

        fixed, _, _ = fix_file(
            md_file,
            from_prefix,
            to_prefix,
            fix_wikilink=True,
            fix_markdown=fix_markdown,
            dry_run=False,
        )

        if fixed > 0:
            files_changed += 1
            total_fixed += fixed

    if not quiet and total_fixed > 0:
        print(f"  已修正: {files_changed} 个文件, {total_fixed} 处路径")

    return files_changed, total_fixed


def main():
    # Windows 控制台 UTF-8 输出
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="图片路径修正工具 — 统一 markdown 中的图片引用路径",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "directory",
        help="要扫描的目录（通常为 vault/raw/）",
    )
    parser.add_argument(
        "--from",
        dest="from_prefix",
        default=None,
        help="源路径前缀（如 'source_vault/images/'）",
    )
    parser.add_argument(
        "--to",
        dest="to_prefix",
        required=True,
        help="目标路径前缀（如 'raw/images/'）",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="自动检测 Obsidian vault 图片路径前缀",
    )
    parser.add_argument(
        "--both",
        action="store_true",
        help="同时修正 Obsidian 双链和标准 markdown 格式（默认只修双链）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式：只显示将要修改的内容，不实际写入",
    )

    args = parser.parse_args()

    target_dir = Path(args.directory).resolve()
    if not target_dir.is_dir():
        print(f"[错误] 目录不存在: {target_dir}")
        sys.exit(1)

    from_prefix = args.from_prefix
    to_prefix = build_to_pattern(args.to_prefix)

    if args.auto and not from_prefix:
        print("正在自动检测 Obsidian vault 图片路径前缀...")
        detected = detect_vault_prefix(target_dir, exclude_prefix=to_prefix)
        if detected:
            from_prefix = detected
            print(f"  检测到: '{from_prefix}'")
        else:
            print("  未检测到 Obsidian 双链图片引用，请用 --from 手动指定")
            sys.exit(1)

    if not from_prefix:
        print("[错误] 请用 --from 指定源前缀，或用 --auto 自动检测")
        sys.exit(1)

    from_prefix = build_from_pattern(from_prefix)

    print(f"\n路径修正: '{from_prefix}' → '{to_prefix}'")
    if args.dry_run:
        print("[预览模式] 不会实际修改文件")
    print("=" * 50)

    fix_wikilink = True
    fix_markdown = args.both

    md_files = sorted(target_dir.rglob("*.md"))
    if not md_files:
        print("未找到 markdown 文件。")
        sys.exit(0)

    print(f"找到 {len(md_files)} 个 markdown 文件\n")

    total_fixed = 0
    total_images = 0
    files_changed = 0

    for md_file in md_files:
        if "images" in md_file.parts and md_file.suffix == ".md":
            continue

        fixed, images, changes = fix_file(
            md_file,
            from_prefix,
            to_prefix,
            fix_wikilink=fix_wikilink,
            fix_markdown=fix_markdown,
            dry_run=args.dry_run,
        )

        total_images += images

        if fixed > 0:
            files_changed += 1
            total_fixed += fixed
            rel_path = md_file.relative_to(target_dir)
            print(f"  {rel_path}  ({fixed} 处)")
            for change in changes:
                print(change)
            print()

    print("=" * 50)
    action = "将修正" if args.dry_run else "已修正"
    print(f"扫描: {len(md_files)} 个文件, {total_images} 处图片引用")
    print(f"{action}: {files_changed} 个文件, {total_fixed} 处路径")

    if args.dry_run and total_fixed > 0:
        print("\n确认无误后，去掉 --dry-run 执行实际修正。")


if __name__ == "__main__":
    main()
