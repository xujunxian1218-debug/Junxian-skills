#!/usr/bin/env python3
"""
Knowledge Vault 内容摄取脚本

将 PDF、Word、PPT、Excel、HTML 等文件转换为 Markdown，
输出到 vault/raw/YYYY-MM-DD/ 目录，图片输出到 vault/raw/images/。

用法:
  python ingest.py file1.pdf file2.docx --vault /path/to/vault
  python ingest.py inbox/ --vault /path/to/vault
  python ingest.py --auto --vault /path/to/vault
"""

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

# ── 脚本目录（用于定位同目录的 fix_image_paths） ──
SCRIPT_DIR = Path(__file__).resolve().parent

# ── 文件类型与工具映射 ──
MARKER_EXTS = {".pdf"}
MARKITDOWN_EXTS = {
    ".docx", ".doc",
    ".pptx", ".ppt",
    ".xlsx", ".xls",
    ".html", ".htm",
    ".csv", ".json", ".xml",
    ".txt", ".md",
    ".epub",
    ".zip",
}
VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".flv"}
AUDIO_EXTS = {".wav", ".mp3", ".m4a"}
ALL_EXTS = MARKER_EXTS | MARKITDOWN_EXTS | VIDEO_EXTS | AUDIO_EXTS

AUDIO_CACHE_DIRNAME = ".audio_cache"

# ── 不应摄取的元数据文件名关键词 ──
SKIP_KEYWORDS = ["manifest", "metadata", "index", ".git", "__pycache__"]


def ensure_dirs(vault_root: Path):
    """确保 raw/、raw/images/、raw/.audio_cache/ 目录存在"""
    raw_dir = vault_root / "raw"
    images_dir = raw_dir / "images"
    audio_cache_dir = raw_dir / AUDIO_CACHE_DIRNAME
    raw_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)
    audio_cache_dir.mkdir(parents=True, exist_ok=True)
    return raw_dir, images_dir, audio_cache_dir


def get_output_path(src_file: Path, raw_dir: Path, suffix: str = "") -> Path:
    """生成 raw/YYYY-MM-DD/原文件名-原格式[-后缀]-时间.md 输出路径"""
    today = date.today().isoformat()
    out_dir = raw_dir / today
    out_dir.mkdir(parents=True, exist_ok=True)
    ext = src_file.suffix.lstrip(".").upper()
    stem = sanitize_filename(src_file.stem)
    if suffix:
        return out_dir / f"{stem}-{ext}-{suffix}-{today}.md"
    return out_dir / f"{stem}-{ext}-{today}.md"


def sanitize_filename(name: str) -> str:
    """去掉文件名中的不安全字符，截断到合理长度"""
    # 移除 Unicode 引号（中文弯引号、排版引号），防止 Windows Bash 路径解析失败
    name = name.translate(str.maketrans({"“": "", "”": "", "‘": "", "’": ""}))
    name = re.sub(r'[\\/:*?"<>|#%^&$!`\'=~]', "", name)
    name = name.strip(". ")
    if len(name) > 80:
        name = name[:80]
    return name if name else "untitled"


def convert_with_marker(src_file: Path, out_file: Path, images_dir: Path) -> bool:
    """用 Marker 转换 PDF，保留图片"""
    try:
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict

        print(f"  [Marker] 转换 PDF: {src_file.name}")

        converter = PdfConverter(artifact_dict=create_model_dict())
        rendered = converter(str(src_file))

        # 兼容新旧版 API
        if hasattr(rendered, 'markdown'):
            text = rendered.markdown
            images = getattr(rendered, 'images', {})
        elif isinstance(rendered, str):
            text = rendered
            images = {}
        else:
            try:
                from marker.output import text_from_rendered
                text, _, images = text_from_rendered(rendered)
            except ImportError:
                text = str(rendered)
                images = {}

        # 保存图片到 raw/images/
        if images:
            for img_name, img_pil in images.items():
                img_filename = f"{img_name}"
                img_path = images_dir / img_filename
                img_pil.save(str(img_path))
                # 更新 markdown 中的图片引用
                text = text.replace(
                    f"![{img_name}]({img_name})",
                    f"![[raw/images/{img_filename}]]",
                )

        out_file.write_text(text, encoding="utf-8")
        print(f"  [Marker] 完成: {out_file.name}")
        return True

    except Exception as e:
        print(f"  [Marker] 失败: {e}")
        print(f"  [MarkItDown] 尝试回退转换 PDF...")
        return convert_with_markitdown(src_file, out_file)


def convert_with_markitdown(src_file: Path, out_file: Path) -> bool:
    """用 MarkItDown 转换 Office/文本文件"""
    try:
        from markitdown import MarkItDown

        print(f"  [MarkItDown] 转换: {src_file.name}")
        md = MarkItDown()
        result = md.convert(str(src_file))
        text = result.text_content

        if not text or not text.strip():
            print(f"  [警告] 转换结果为空: {src_file.name}")
            return False

        out_file.write_text(text, encoding="utf-8")
        print(f"  [MarkItDown] 完成: {out_file.name}")
        return True

    except Exception as e:
        print(f"  [MarkItDown] 失败: {e}")
        return False


def extract_audio(video_path: Path, audio_cache_dir: Path) -> Path:
    """Extract audio from video file using ffmpeg. Returns audio file path."""
    audio_path = audio_cache_dir / f"{video_path.stem}.mp3"

    if audio_path.exists():
        print(f"  [ffmpeg] 音频缓存命中: {audio_path.name}")
        return audio_path

    cmd = [
        "ffmpeg",
        "-i", str(video_path),
        "-vn",
        "-acodec", "libmp3lame",
        "-ab", "128k",
        "-ar", "16000",
        "-ac", "1",
        "-y",
        str(audio_path),
    ]

    print(f"  [ffmpeg] 提取音轨: {video_path.name}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg 失败: {result.stderr[:500]}")

    return audio_path


def transcribe_audio(audio_path: Path) -> str:
    """Transcribe audio using faster-whisper. Returns full text."""
    from faster_whisper import WhisperModel

    print(f"  [ASR] 转写: {audio_path.name}")
    model = WhisperModel("base", device="cpu", compute_type="int8")

    segments, info = model.transcribe(
        str(audio_path),
        language="zh",
        beam_size=5,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
        initial_prompt="AI 人工智能 芯片 字节跳动 OpenAI Anthropic "
                       "Musk Altman 深度学习 量子计算 自动驾驶 生成式 "
                       "Transformer GPT Claude DeepSeek Meta Google",
    )

    full_text_parts = []
    for seg in segments:
        full_text_parts.append(seg.text.strip())

    return "\n".join(full_text_parts)


# ASR 同音错别字纠错词典（只放高置信度替换：源文本不是合法中文词）
ASR_CORRECTIONS = {
    # 常见同音错别字
    "声承": "生成", "伟造": "伪造", "换绝": "换脸",
    "营华": "引发", "鬼疑": "诡异", "荣常": "冗长",
    "早鳥架": "早鸟价", "证架": "正价", "结智": "结束",
    "字界跳动": "字节跳动", "所住": "锁住",
    "整断": "诊断", "补款": "拨款",
    "无耗破战": "毫无破绽", "讲连推验": "链接推荐",
}


def correct_asr_text(text: str) -> str:
    """规则纠错：高置信度同音错别字替换"""
    for wrong, right in ASR_CORRECTIONS.items():
        text = text.replace(wrong, right)
    return text


def convert_with_asr(src_file: Path, out_file: Path, audio_cache_dir: Path) -> bool:
    """视频/音频转写：ffmpeg 提取音轨 → faster-whisper 转写 → 写 MD"""
    ext = src_file.suffix.lower()

    try:
        # 视频文件先提取音轨，音频文件直接转写
        if ext in VIDEO_EXTS:
            audio_path = extract_audio(src_file, audio_cache_dir)
        else:
            audio_path = src_file

        full_text = transcribe_audio(audio_path)

        # 纠错
        full_text = correct_asr_text(full_text)

        if not full_text or not full_text.strip():
            print(f"  [ASR] 转写结果为空: {src_file.name}")
            return False

        out_file.write_text(full_text, encoding="utf-8")
        print(f"  [ASR] 完成: {out_file.name}")
        return True

    except FileNotFoundError:
        print(f"  [ASR] 失败: ffmpeg 未安装")
        print(f"  [提示] 视频转写需要 ffmpeg")
        print(f"    下载: https://ffmpeg.org/download.html")
        print(f"    Windows: choco install ffmpeg")
        return False

    except ImportError:
        print(f"  [ASR] 失败: faster-whisper 未安装")
        print(f"  [提示] 音视频转写需要 faster-whisper")
        print(f"    安装: pip install \"faster-whisper>=1.0.0\"")
        return False

    except Exception as e:
        print(f"  [ASR] 失败: {e}")
        return False


def is_skippable(src_file: Path) -> bool:
    """Check if file is metadata/manifest that should not be ingested."""
    stem = src_file.stem.lower()
    return any(kw in stem for kw in SKIP_KEYWORDS)


def ingest_file(src_file: Path, raw_dir: Path, images_dir: Path, audio_cache_dir: Path) -> bool:
    """摄取单个文件"""
    ext = src_file.suffix.lower()

    if ext not in ALL_EXTS:
        print(f"  [跳过] 不支持的格式: {src_file.name} ({ext})")
        return False

    if is_skippable(src_file):
        print(f"  [跳过] 元数据文件: {src_file.name}")
        return False

    if ext in VIDEO_EXTS or ext in AUDIO_EXTS:
        out_file = get_output_path(src_file, raw_dir, suffix="转写")
    else:
        out_file = get_output_path(src_file, raw_dir)

    if out_file.exists():
        print(f"  [跳过] 已存在: {out_file.name}")
        return False

    print(f"\n摄取: {src_file}")

    if ext in MARKER_EXTS:
        return convert_with_marker(src_file, out_file, images_dir)
    elif ext in VIDEO_EXTS or ext in AUDIO_EXTS:
        return convert_with_asr(src_file, out_file, audio_cache_dir)
    else:
        return convert_with_markitdown(src_file, out_file)


def collect_files(paths: list[str]) -> list[Path]:
    """从参数中收集所有待处理文件"""
    files = []
    for p in paths:
        path = Path(p).resolve()
        if path.is_file():
            if is_skippable(path):
                print(f"[跳过] 元数据文件: {path}")
            elif path.suffix.lower() in ALL_EXTS:
                files.append(path)
            else:
                print(f"[跳过] 不支持的格式: {path}")
        elif path.is_dir():
            for ext in ALL_EXTS:
                for f in path.glob(f"*{ext}"):
                    if not is_skippable(f):
                        files.append(f)
        else:
            print(f"[警告] 路径不存在: {p}")
    return sorted(set(files))


def find_unconverted_files(directory: Path) -> list[Path]:
    """扫描 raw/ 目录下未转换的源文件（PDF、DOCX 等）。

    判断逻辑：如果同目录下已有「文件名-格式-日期.md」格式的转换结果，
    则视为已转换。
    """
    unconverted = []
    for f in sorted(directory.rglob("*")):
        if not f.is_file():
            continue
        if f.suffix.lower() not in ALL_EXTS:
            continue
        if f.suffix.lower() == ".md":
            continue
        if is_skippable(f):
            continue
        stem = sanitize_filename(f.stem)
        parent = f.parent
        pattern = f"{stem}-*"
        existing = list(parent.glob(f"{pattern}.md"))
        if not existing:
            unconverted.append(f)
    return unconverted


def main():
    # Windows 控制台 UTF-8 输出
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Knowledge Vault 内容摄取工具 — 将文件转换为 Markdown 放入 vault/raw/"
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="要摄取的文件或目录路径",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="自动扫描 vault/raw/ 目录下未转换的文件并处理",
    )
    parser.add_argument(
        "--vault",
        required=True,
        help="知识库根目录路径",
    )
    args = parser.parse_args()

    vault_root = Path(args.vault).resolve()
    if not vault_root.exists():
        print(f"[错误] Vault 目录不存在: {vault_root}")
        print(f"  请先运行: python {SCRIPT_DIR / 'init_vault.py'} {args.vault}")
        sys.exit(1)

    raw_dir, images_dir, audio_cache_dir = ensure_dirs(vault_root)

    if args.auto:
        print("自动扫描 raw/ 目录下未转换的文件...")
        files = find_unconverted_files(raw_dir)
        if not files:
            print("没有发现未转换的文件。")
            return
        print(f"发现 {len(files)} 个未转换的文件:")
        for f in files:
            print(f"  - {f.relative_to(vault_root)}")
    else:
        if not args.paths:
            parser.print_help()
            sys.exit(1)
        files = collect_files(args.paths)

    if not files:
        print("没有找到可处理的文件。")
        print(f"支持的格式: {', '.join(sorted(ALL_EXTS))}")
        sys.exit(1)

    print(f"找到 {len(files)} 个文件待处理")
    print("=" * 50)

    success = 0
    failed = 0
    for f in files:
        if ingest_file(f, raw_dir, images_dir, audio_cache_dir):
            success += 1
        else:
            failed += 1

    print("\n" + "=" * 50)
    print(f"完成: 成功 {success} 个, 失败 {failed} 个")

    # 自动修正图片路径
    if success > 0:
        print("\n--- 图片路径自动修正 ---")
        try:
            if str(SCRIPT_DIR) not in sys.path:
                sys.path.insert(0, str(SCRIPT_DIR))
            from fix_image_paths import run_fix
            run_fix(raw_dir, to_prefix="raw/images/", auto_detect=True)
        except ImportError:
            print("  [跳过] fix_image_paths 模块未找到")
        print("\n下一步: 让 Claude 执行消化流程处理新增的 raw 文件")


if __name__ == "__main__":
    main()
