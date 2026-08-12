#!/usr/bin/env python3
"""
图片路径修正工具 — 统一 markdown 文件中的图片引用路径。

将 Obsidian 双链或标准 markdown 中的图片路径前缀替换为目标前缀，
保留别名（如 |cover_image），并输出修正统计。

用法:
  # 指定源前缀和目标前缀
  python fix_image_paths.py raw/ --from "笔记同步助手/images/" --to "raw/images/"

  # 自动检测 Obsidian vault 前缀（匹配 ![[xxx/images/]] 模式）
  python fix_image_paths.py raw/ --to "raw/images/" --auto

  # 预览模式，不实际修改文件
  python fix_image_paths.py raw/ --from "笔记同步助手/images/" --to "raw/images/" --dry-run

  # 同时修正 Obsidian 双链和标准 markdown 格式
  python fix_image_paths.py raw/ --from "笔记同步助手/images/" --to "raw/images/" --both

  # 补全裸文件名图片引用（PDF Marker 产出的 _page_X_Figure_Y.jpeg 等）
  python fix_image_paths.py raw/ --from "笔记同步助手/images/" --to "raw/images/" --bare
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

# 裸文件名图片引用（v1.13.0 T2.3）：纯文件名，无任何路径前缀（如 Marker PDF 产出的
# ![_page_0_Figure_1.jpeg]、手动导入 md 的 ![](img.jpg)）。[^|\]/] 排除 /，确保不
# 误匹配已带前缀的 ![[raw/images/xxx.jpg]]（幂等安全）。补全需 images_dir 存在性校验。
_IMG_EXT = r'\.(?:jpe?g|png|gif|webp|bmp|svg|avif|ico)'
RE_WIKILINK_BARE = re.compile(
    rf'!\[\[([^|\]/]+{ _IMG_EXT })((?:\|[^]]*?)?)\]\]',
    re.IGNORECASE,
)
RE_MARKDOWN_BARE = re.compile(
    rf'!\[([^\]]*?)\]\(([^)/]+{ _IMG_EXT })\)',
    re.IGNORECASE,
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


def count_wikilink_images(directory: Path) -> tuple[int, int]:
    """统计目录下所有 Obsidian 双链图片引用（不排除任何前缀）。

    返回 (匹配 RE_WIKILINK 的总数, 其中路径含 /images/ 的数量)。
    用于 detect_vault_prefix 返回 None 时的诊断——区分"无任何双链图"
    vs "有但前缀均已是目标（被 exclude 掉）"（usage-log 2026-07-23 [E]②）。
    """
    total = 0
    with_images = 0
    for md_file in directory.rglob("*.md"):
        try:
            text = md_file.read_text(encoding="utf-8")
        except Exception:
            continue
        for match in RE_WIKILINK.finditer(text):
            total += 1
            if "/images/" in match.group(1):
                with_images += 1
    return total, with_images


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
    fix_bare: bool = False,
    images_dir: Path | None = None,
    dry_run: bool = False,
) -> tuple[int, int, list[str]]:
    """修正单个 md 文件的图片路径。

    返回: (修正数量, 图片总数, 修正详情列表)

    fix_bare（v1.13.0 T2.3）：补全裸文件名图片引用（无任何路径前缀，如
    ![[x.jpg]] / ![](x.jpg)）。需 images_dir 做存在性校验——文件实际存在于
    images_dir 才补全为 ![[{to_prefix}filename]]，避免误改指向库外图片的引用。
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

    def replace_wikilink_bare(match: re.Match) -> str:
        nonlocal total_images
        total_images += 1
        filename = match.group(1)
        alias = match.group(2)
        if images_dir is None or not (images_dir / filename).exists():
            return match.group(0)  # 无 images_dir 或库内不存在，保留原样
        new_ref = f"![[{to_prefix}{filename}{alias}]]"
        changes.append(f"  ![[{filename}{alias}]] → {new_ref}")
        return new_ref

    def replace_markdown_bare(match: re.Match) -> str:
        nonlocal total_images
        total_images += 1
        alt_text = match.group(1)
        filename = match.group(2)
        if images_dir is None or not (images_dir / filename).exists():
            return match.group(0)
        # 统一转双链格式（Obsidian 推荐，与 generation.md 图片引用规范一致）
        new_ref = f"![[{to_prefix}{filename}]]"
        changes.append(f"  ![{alt_text}]({filename}) → {new_ref}")
        return new_ref

    if fix_wikilink:
        text = RE_WIKILINK.sub(replace_wikilink, text)
        text = RE_WIKILINK_RELATIVE.sub(replace_wikilink, text)

    if fix_markdown:
        text = RE_MARKDOWN.sub(replace_markdown, text)
        text = RE_MARKDOWN_RELATIVE.sub(replace_markdown, text)

    if fix_bare:
        text = RE_WIKILINK_BARE.sub(replace_wikilink_bare, text)
        text = RE_MARKDOWN_BARE.sub(replace_markdown_bare, text)

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
    fix_bare: bool = True,
    quiet: bool = False,
) -> tuple[int, int]:
    """编程接口：修正目录下所有 md 文件的图片路径。

    Args:
        directory: 要扫描的目录（通常 vault/raw/；裸文件名补全从 directory/images 读图）
        to_prefix: 目标路径前缀
        from_prefix: 源路径前缀，为 None 时自动检测
        auto_detect: 是否自动检测 vault 前缀
        fix_markdown: 是否同时修正标准 markdown 格式（带 /images/ 前缀的）
        fix_bare: 是否补全裸文件名图片引用（无路径前缀，需 directory/images 存在）
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

    # 裸文件名补全的 images_dir（directory/images，如 vault/raw/images）
    images_dir = target_dir / "images"
    if not images_dir.is_dir():
        images_dir = None  # 无 images 目录，bare replace 函数内降级为 no-op

    # 前缀替换（可选；检测不到或等于目标时跳过，但不影响裸文件名补全）
    if from_prefix is None and auto_detect:
        from_prefix = detect_vault_prefix(target_dir, exclude_prefix=to_prefix)

    do_prefix_fix = bool(from_prefix)
    if do_prefix_fix:
        from_prefix = build_from_pattern(from_prefix)
        if from_prefix == to_prefix:
            do_prefix_fix = False

    if not do_prefix_fix and not fix_bare:
        if not quiet:
            print("[跳过] 未检测到需要修正的图片路径")
        return 0, 0

    if not quiet and do_prefix_fix:
        print(f"  图片路径修正: '{from_prefix}' -> '{to_prefix}'")

    md_files = sorted(target_dir.rglob("*.md"))
    total_fixed = 0
    files_changed = 0

    for md_file in md_files:
        if "images" in md_file.parts and md_file.suffix == ".md":
            continue

        fixed, _, _ = fix_file(
            md_file,
            from_prefix if do_prefix_fix else "",
            to_prefix,
            fix_wikilink=do_prefix_fix,
            fix_markdown=fix_markdown and do_prefix_fix,
            fix_bare=fix_bare,
            images_dir=images_dir,
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
        help="源路径前缀（如 '笔记同步助手/images/'）",
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
        "--bare",
        action="store_true",
        help="补全裸文件名图片引用（无路径前缀，如 ![[x.jpg]] / ![](x.jpg) → ![[raw/images/x.jpg]]），需 directory/images 目录存在",
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
            # 诊断：区分"无任何双链图" vs "有但前缀均已是目标"（usage-log 2026-07-23 [E]②）
            total, _ = count_wikilink_images(target_dir)
            if total == 0:
                print("  未检测到任何 Obsidian 双链图片引用（![[.../images/...]]）。")
                print("  若文件用标准 markdown 语法 ![](...)，请加 --both；或用 --from 手动指定源前缀。")
            else:
                print(f"  检测到 {total} 处双链图片引用，但前缀均已是目标 '{to_prefix}'，无需前缀修正。")
            # 无前缀可修：仅当未启用 --bare 时才退出（v1.13.0 T2.3：--bare 可独立运行）
            if not args.bare:
                print("  若实际前缀不同，请用 --from 手动指定。")
                sys.exit(0)
            print("  --bare 已启用，继续扫描裸文件名图片引用...")

    if not from_prefix and not args.bare:
        print("[错误] 请用 --from 指定源前缀，或用 --auto 自动检测，或加 --bare 仅补全裸文件名")
        sys.exit(1)

    do_prefix_fix = bool(from_prefix)
    if do_prefix_fix:
        from_prefix = build_from_pattern(from_prefix)
        print(f"\n路径修正: '{from_prefix}' → '{to_prefix}'")
    else:
        print(f"\n裸文件名补全: → '{to_prefix}'（无前缀替换任务）")
    if args.dry_run:
        print("[预览模式] 不会实际修改文件")
    print("=" * 50)

    fix_wikilink = do_prefix_fix
    fix_markdown = args.both and do_prefix_fix
    images_dir = target_dir / "images"
    if not images_dir.is_dir():
        images_dir = None

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
            fix_bare=args.bare,
            images_dir=images_dir,
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
