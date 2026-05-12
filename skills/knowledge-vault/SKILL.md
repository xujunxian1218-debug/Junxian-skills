---
name: knowledge-vault
version: 1.3.2
description: |
  USE WHEN: 用户提及"知识库"、"知识管理"、"初始化知识库"、"摄取文件"、"消化知识"、"知识巡检"、
  "知识问答"、"帮我整理文档"、"提取概念"、"生成主题页"、"knowledge vault"、"second brain"、
  "digest"、"ingest" 时触发
  文件驱动个人知识管理系统：Ingest → Digest → Output → Audit 四阶段循环，
  支持文档转 Markdown、结构化摘要、概念卡、主题页，兼容 Obsidian 双链
  EXAMPLES: "初始化知识库" / "把这些文件摄取到知识库" / "消化知识库的新内容" / "帮我整理这篇文档" / "知识巡检"
author: Junxian
tags: [tools, knowledge-management, obsidian, markdown]
allowed-tools: [Bash, Read, Write, Edit, Glob, Grep]
---

# Knowledge Vault

A file-first personal knowledge management system that follows a four-phase cycle:
**Ingest → Digest → Output → Audit**.

Every piece of content is a plain `.md` file. All conclusions trace back to original
sources. Works with Obsidian for visualization but doesn't depend on it.

## Phase Router

Match user intent to the correct phase before executing:

| User intent | Phase | Action |
|-------------|-------|--------|
| "初始化知识库" / first-time setup | Phase 1: Initialize | Run `init_vault.py` |
| "摄取文件" / convert documents / add to vault | Phase 2: Ingest | Run `ingest.py`, then suggest Digest |
| "消化知识" / process new content / summarize | Phase 3: Digest | Pre-checks → Digest → Self-check |
| Ask a question / explore a topic / generate content | Phase 4: Output | Layered retrieval from index |
| "知识巡检" / check health / audit | Phase 5: Audit | Run 9-point checklist |
| Multiple files given directly (no vault yet) | Phase 1 → 2 → 3 | Initialize → Ingest → Digest |

When in doubt, ask the user which operation they want.

## Directory Structure

```
<vault-root>/
├── raw/                    ← Original materials (by date YYYY-MM-DD)
│   └── images/             ← Extracted images
├── knowledge/
│   ├── summaries/          ← Structured summaries
│   ├── concepts/           ← Concept cards
│   ├── topics/             ← Topic pages
│   ├── index.md            ← Master index
│   └── dashboard.md        ← Obsidian Dataview dashboard
├── notes/                  ← Personal notes (AI must NOT touch)
├── templates/              ← Obsidian templates
└── outputs/                ← High-value output artifacts
```

## Dependencies

Requires Python 3.10+ and two packages:

```bash
pip install "markitdown[all]>=0.1.5" "marker-pdf>=1.10.0"
```

Note: `marker-pdf` downloads OCR models (~200MB) on first use. If only handling
non-PDF files, `markitdown` alone suffices.

For audio/video transcription (optional):

```bash
pip install "faster-whisper>=1.0.0"
# Also requires ffmpeg: https://ffmpeg.org/download.html
# Windows: choco install ffmpeg
```

## Phase 1: Initialize

First-time setup. Creates directories, copies templates, generates index files.
Also checks environment dependencies and reports what is installed.

```bash
# Initialize vault
python <skill-path>/scripts/init_vault.py <vault-path>

# Check environment only (no vault creation)
python <skill-path>/scripts/init_vault.py --check-env
```

This is idempotent — running it on an existing vault only fills in missing pieces.

## Phase 2: Ingest

Convert source files into Markdown stored in the vault.

### Supported formats

| Tool | Formats | Notes |
|------|---------|-------|
| Marker | `.pdf` | Preserves structure, tables, extracts images |
| MarkItDown | `.docx` `.doc` `.pptx` `.ppt` `.xlsx` `.xls` | Office documents |
| MarkItDown | `.html` `.htm` `.csv` `.json` `.xml` `.txt` `.md` | Text formats |
| MarkItDown | `.epub` `.zip` | Other formats |
| ASR | `.wav` `.mp3` `.m4a` `.mp4` `.mkv` `.avi` `.mov` `.flv` | Audio/video, requires faster-whisper + ffmpeg |

### Usage

```bash
# Ingest specific files
python <skill-path>/scripts/ingest.py file1.pdf file2.docx --vault <vault-path>

# Ingest all supported files in a directory
python <skill-path>/scripts/ingest.py inbox/ --vault <vault-path>

# Auto-scan raw/ for unconverted source files
python <skill-path>/scripts/ingest.py --auto --vault <vault-path>
```

Output lands in `raw/YYYY-MM-DD/{filename}-{EXT}-{date}.md`, images in `raw/images/`.
Audio/video transcripts use `raw/YYYY-MM-DD/{filename}-{EXT}-转写-{date}.md`.
Image paths are auto-fixed after conversion.

After ingestion, proceed to Digest.

## Phase 3: Digest

The core AI-driven phase. For each new raw file without a summary, execute
these steps. **Read `references/digestion-rules.md` before the first digestion**
for detailed rules on deduplication, image processing, and naming.

### Pre-digestion checks (mandatory, in order)

1. **Auto-convert unprocessed files**:
   ```bash
   python <skill-path>/scripts/ingest.py --auto --vault <vault-path>
   ```

2. **Fix image paths**:
   ```bash
   python <skill-path>/scripts/fix_image_paths.py <vault-path>/raw/ --auto --to "raw/images/"
   ```

3. **Deduplication**: Run the undigested-files check script to get a precise
   report of what actually needs digestion:
   ```bash
   python <skill-path>/scripts/check_undigested.py --vault <vault-path>
   ```
   The script outputs 4 categories:
   - `NEW` — genuinely undigested content (digest these)
   - `DUPE` — already covered by another format of the same content (skip)
   - `SKIP` — metadata/manifest files that aren't knowledge content (skip)
   - `MANUAL` — cannot auto-determine, needs human confirmation
   Only digest files in the `NEW` category. Report all categories to the user.

4. **Digest plan confirmation**: List all files to be digested and stop.
   Show the user: file count, filenames, and estimated scope (rough number of
   new concepts/topics that might be created). Wait for user confirmation
   before proceeding. If no new files, report and stop — do not enter digestion.

### Digestion workflow (per new raw file)

The digestion is a **two-step process**: analyze first, then generate.
**Read `references/digestion-rules.md`** for the full rules on each step.

**For files with `-转写-` in the filename (ASR transcripts):**
Before any analysis, mentally correct the transcript text. ASR output
contains homophone errors, mistranscribed proper nouns, and misaligned syllables
that rule-based correction cannot fix. Use context to identify and correct errors
such as: "前哨科技"→"科技前哨", "C dancy"→"Seedance", "Wales米斯"→"Will Smith",
"锦细量"→"信息量", etc. Do NOT modify the raw file — corrections are applied in
your understanding only, and reflected in the generated summary/concepts/topics.

#### Step 1: Analysis

Read the raw file AND the current state of the knowledge base, then produce
a structured analysis covering:

1. **Key entities** — people, organizations, products, tools mentioned
   - Name, type, role in source (central vs. peripheral)
   - Whether it likely already exists in the wiki (check `knowledge/index.md`)

2. **Key concepts** — theories, methods, techniques, phenomena
   - Name and brief definition
   - Why it matters in this source
   - Whether it likely already exists in the wiki

3. **Main arguments & findings** — core claims, supporting evidence, evidence strength

4. **Connections to existing wiki**
   - What existing concepts/topics does this source relate to?
   - Does it strengthen, challenge, or extend existing knowledge?
   - Scan `knowledge/index.md`, existing concept cards, and topic pages to find connections

5. **Contradictions & tensions**
   - Does anything in this source conflict with existing wiki content?
   - Are there internal tensions or caveats?
   - Flag these for the user's attention

6. **Recommendations** — what wiki pages should be created or updated, what to emphasize

This analysis does NOT write any files. It is an internal reasoning step
that feeds into Step 2. The analysis should be concise — focus on what's
genuinely important, not a line-by-line summary.

#### Step 2: Generation

Using the analysis from Step 1 as context, generate wiki files:

1. **Generate summary** → `knowledge/summaries/{title}-摘要-{YYYY-MM-DD}.md`
   - Use template: `templates/tpl-summary.md`
   - All required frontmatter: `source`, `title`, `date`, `author`, `tags`
   - All required body sections: one-sentence summary, key points, key concepts,
     notable quotes, key images, personal supplement, cross-references
   - **Source path verification**: before writing the `source` field, use Glob
     to search `raw/**/` for the actual filename. Use the exact filename
     returned by Glob — never rely on memory or guess the path, as special
     characters (curly quotes, em dashes) must match the real file.
   - Image handling: classify each image (A-E), convert or preserve accordingly
     (see `references/digestion-rules.md` for the classification system)
   - Image references must use Obsidian wikilinks: `![[raw/images/xxx.jpg]]`
     (never use Markdown relative paths like `../raw/images/` — they break in Obsidian)

2. **Extract/update concepts** → `knowledge/concepts/`
   - Existing concept → intelligently merge new information (see digestion-rules.md
     "Page Merge Strategy" section for merge rules). Preserve all existing content
     while adding new contributions from this source.
   - New concept → create using `templates/tpl-concept.md`.
     When creating a new concept, show the concept name and definition to
     the user before writing the file. Proceed if no objection.

3. **Update/create topic pages** → `knowledge/topics/`
   - Existing topic → intelligently merge new content into "主题脉络"
   - New topic → create using `templates/tpl-topic.md`.
     When creating a new topic, show the topic name and scope to the user
     before writing the file. Proceed if no objection.

4. **Update master index** → `knowledge/index.md`
   - Refresh statistics (count actual files)
   - Add entries to timeline index
   - New concepts: add row to concept index table
   - New topics: add row to topic navigation table
   - Updated topics: refresh their summary count

5. **Report contradictions** — if Step 1 found contradictions with existing
   wiki content, report them to the user explicitly after generation is complete.
   Do not silently resolve contradictions — the user decides.

### Post-digestion self-check (mandatory)

After digesting all files, verify every item:

1. Concept index table: every "文件" column uses `[[xxx-概念]]` wikilink format
2. Topic navigation table: every "文件" column uses `[[xxx-主题]]` wikilink format
3. Timeline index: every "摘要文件" column uses `[[xxx-摘要-xxx]]` wikilink format
4. **Summary section title precision**: for every summary generated this session,
   verify all required body sections exist AND their headings exactly match the
   template ("一句话摘要" not "一句话总结", "原文金句" not "精彩引述"). Fix any
   mismatched headings immediately. Short summaries with no notable quotes should
   use placeholder text, not omit the section.
5. Statistics match actual file counts (concepts/, summaries/, topics/)
6. Fix any non-wikilink entries immediately
7. **Cross-reference validity**: scan all concept cards' "与其他概念的关系" section, extract every `[[xxx-概念]]` wikilink, and verify the target file exists in `knowledge/concepts/`. If missing, either create the concept card or remove the broken link. Report any broken links found and actions taken.
8. **All numeric annotations in index.md**: scan every line in `index.md` that contains a number in a comment or annotation (patterns like `> ...N...` or `N 篇`/`N 张`/`N 个`). For each such number, verify it matches the actual file count in the corresponding directory. This covers header statistics, directory structure annotations, and any other inline counts. Fix any discrepancies immediately.
9. **Concept card internal wikilink format**: for every concept card created or
   updated this session, scan the "与其他概念的关系" section and verify all
   `[[...]]` links use the full slug format `[[xxx-概念]]`. Bare concept names
   (e.g. `[[Embedding 与 RAG]]` without `-概念` suffix) must be fixed immediately.

## Phase 4: Output

Consume knowledge from the vault through 6 consumption scenarios.
**Read `references/output-rules.md`** for the full retrieval strategy,
scenario workflows, and output standards.

### Retrieval Strategy

All consumption scenarios follow a layered retrieval:
`index.md → topic pages → concept cards → summaries → raw files`

Not every request needs full traversal. Quick Q&A may only need index +
concepts; deep exploration needs the full path.

### Consumption Scenarios

| Scenario | Maturity | Output |
|----------|----------|--------|
| Knowledge Q&A | Stable | Direct reply, no file |
| Topic Exploration | Stable | File to `outputs/` |
| Cross-domain Analysis | Experimental | File to `outputs/` |
| Learning Path | Experimental | File to `outputs/` |
| Gap Detection | Experimental | Reply or file |
| Content Generation | Experimental | File to `outputs/` subdirectory |

### Output Standards

- Cite sources using Obsidian wikilinks: `[[概念名-概念]]`, `[[摘要名-摘要-日期]]`
- Mark knowledge boundaries: distinguish "covered by KB" vs "supplementary inference"
- File outputs use standard frontmatter: type, topic, sources, created

## Phase 5: Audit

Periodically check knowledge base health. **Read `references/audit-rules.md`**
for the full 9-point checklist:

1. Raw → summary coverage
2. Summary required fields completeness
3. Concept definition consistency
4. Topic page link validity
5. Filename compliance
6. Index statistics accuracy
7. All table columns use correct link format
8. Source optimization suggestions (optional)
9. Orphan detection — pages with no inbound references

Output: `knowledge/audit-report-YYYY-MM-DD.md` — **report only, never auto-fix**.

## Naming Conventions

| Type | Pattern | Example |
|------|---------|---------|
| Summary | `{title}-摘要-{date}.md` | `AI记忆系统-摘要-2026-04-12.md` |
| Concept | `{name}-概念.md` | `上下文工程-概念.md` |
| Topic | `{name}-主题.md` | `AI编程-主题.md` |
| Audit | `audit-report-{date}.md` | `audit-report-2026-04-12.md` |
| Note | `{title}.md` (in `notes/`) | free naming |

Title: first 40 chars of original, remove unsafe characters (`\ / : * ? " < > |` etc.).

## Error Recovery

If digestion is interrupted (session ends, script fails, user aborts):

1. **Resumable by design**: Each raw file produces independent outputs (summary,
   concepts, topics). Files already processed won't be re-digested thanks to
   deduplication (pre-check step 3).
2. **Partial completion**: If some files were digested but index wasn't updated,
   re-run digestion — deduplication skips already-processed files, then proceed
   to index update.
3. **Corrupted output**: If a summary/concept/topic file is malformed, delete it
   and re-run digestion. The deduplication check only matches on `source` field,
   so removing the broken file allows re-processing.
4. **Script failure**: If `ingest.py` or `fix_image_paths.py` fails, report the
   error and specific file that caused it. Do not skip the step — ask user whether
   to retry or skip the problematic file.

## Prohibitions

- Never delete or overwrite files in `raw/`
- Never modify concept card core definitions without user confirmation
- Never auto-merge or delete topic pages
- Never auto-execute fixes from audit reports
- **Never modify, overwrite, or delete anything in `notes/`**

## USE WHEN

- 用户提及"知识库"、"知识管理"、"初始化知识库"、"知识库初始化"
- 用户说"摄取文件"、"消化知识"、"消化新内容"、"整理文档"
- 用户说"知识巡检"、"知识库审计"、"检查知识库健康度"
- 用户说"帮我总结这篇文章"、"提取概念"、"生成主题页"
- 用户提到"knowledge vault"、"second brain"、"digest"、"ingest"
- 用户想建立 Obsidian 兼容的个人知识库

## Output Format

产出为标准 `.md` 文件，使用 Obsidian wikilink 双链：
- 摘要：结构化 Markdown，含 frontmatter 和 7 个正文板块
- 概念卡：定义 + 相关来源 + 交叉引用
- 主题页：主题脉络 + 涵盖的概念和摘要
- 巡检报告：7 项检查结果 + 统计数据
- 引用格式：`[[概念名-概念]]`、`[[摘要名-摘要-日期]]`

## Examples

- "初始化知识库" → 运行 init_vault.py 创建目录结构和模板
- "把这些 PDF 摄取到知识库" → 运行 ingest.py 转换文件为 Markdown
- "消化知识库的新内容" → 执行完整 Digest 流程（去重→摘要→概念→主题→索引）
- "知识库里关于 AI 编程的内容" → 从 index.md 检索，沿 topic → concept → summary 路径回答
- "跑一次知识巡检" → 执行 7 项检查，输出 audit-report
